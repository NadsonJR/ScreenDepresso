"""System audio (loopback) capture, mixed with an optional microphone.

Qt Multimedia only records input devices, so what the speakers play is read
with `soundcard`: WASAPI loopback on Windows and the PulseAudio/PipeWire
monitor source on Linux. The microphone, when enabled, comes from Qt's
QAudioSource. Each device feeds its own FIFO; a mixer thread
paces the output by the wall clock, so silent loopback devices (WASAPI sends
nothing while no sound plays) become silence instead of gaps, and emits
interleaved 16-bit stereo PCM for QAudioBufferInput. `soundcard` and numpy are
imported on the capture thread only, keeping startup light and COM
initialization off the Qt main thread.
"""
import importlib.util
import sys
import threading
import time
from PySide6.QtCore import QObject, Signal

RATE = 48000
CHANNELS = 2
TICK = 0.02        # mixer period in seconds
LATENCY = 0.1      # jitter buffer: output lags the wall clock by this much
MAX_BACKLOG = 0.4  # drop older audio past this, so device clock drift cannot pile up
STOP_TIMEOUT = 3.0  # how long stop() waits for the mixer and its readers


def system_audio_supported():
    if not (sys.platform == 'win32' or sys.platform.startswith('linux')):
        return False
    try:
        return importlib.util.find_spec('soundcard') is not None
    except (ImportError, ValueError):
        return False


def _com_init():
    if sys.platform == 'win32':
        import ctypes
        # COINIT_MULTITHREADED; S_OK or S_FALSE mean this thread must uninitialize.
        return ctypes.windll.ole32.CoInitializeEx(None, 0) in (0, 1)
    return False


def _com_uninit(initialized):
    if initialized:
        import ctypes
        ctypes.windll.ole32.CoUninitialize()


def to_float_frames(data, audio_format):
    """Raw QAudioSource bytes -> float32 (frames, channels) at RATE Hz."""
    import numpy as np
    from PySide6.QtMultimedia import QAudioFormat
    kind = audio_format.sampleFormat()
    if kind == QAudioFormat.SampleFormat.Float:
        samples = np.frombuffer(data, '<f4')
    elif kind == QAudioFormat.SampleFormat.Int16:
        samples = np.frombuffer(data, '<i2')/32768.0
    elif kind == QAudioFormat.SampleFormat.Int32:
        samples = np.frombuffer(data, '<i4')/2147483648.0
    else:  # UInt8
        samples = (np.frombuffer(data, 'u1')-128.0)/128.0
    channels = max(1, audio_format.channelCount())
    frames = len(samples)//channels
    samples = np.asarray(samples[:frames*channels], np.float32).reshape(frames, channels)
    rate = audio_format.sampleRate()
    if rate and rate != RATE and frames > 1:
        count = max(1, round(frames*RATE/rate))
        positions = np.arange(count)*(rate/RATE)
        index = np.arange(frames)
        samples = np.column_stack([np.interp(positions, index, samples[:, c]) for c in range(channels)]).astype(np.float32)
    return samples


class _Source:
    """Thread-safe FIFO of float32 (frames, 2) blocks read from one device."""

    def __init__(self, name, recorder):
        self.name = name
        self.recorder = recorder
        self.lock = threading.Lock()
        self.blocks = []
        self.frames = 0
        self.dropping = False

    def set_dropping(self, dropping):
        """While dropping, pushed audio is discarded. Entering or leaving the
        state also empties the FIFO, so audio captured during a muted or paused
        interval (it waits in the jitter buffer) can never reach the video."""
        with self.lock:
            if dropping == self.dropping:
                return
            self.dropping = dropping
            self.blocks, self.frames = [], 0

    def push(self, data):
        import numpy as np
        if data is None or len(data) == 0:
            return
        data = np.asarray(data, dtype=np.float32)
        if data.ndim == 1:
            data = data[:, None]
        if data.shape[1] == 1:
            data = np.repeat(data, CHANNELS, axis=1)
        elif data.shape[1] > CHANNELS:
            data = data[:, :CHANNELS]
        with self.lock:
            if self.dropping:
                return
            self.blocks.append(data)
            self.frames += len(data)

    def take(self, count):
        import numpy as np
        with self.lock:
            blocks, self.blocks, available, self.frames = self.blocks, [], self.frames, 0
        data = np.concatenate(blocks) if blocks else np.zeros((0, CHANNELS), np.float32)
        excess = available-count-int(MAX_BACKLOG*RATE)
        if excess > 0:
            data = data[excess:]
        result, rest = data[:count], data[count:]
        if len(rest):
            with self.lock:
                self.blocks.insert(0, rest)
                self.frames += len(rest)
        if len(result) < count:
            result = np.concatenate([result, np.zeros((count-len(result), CHANNELS), np.float32)])
        return result


class AudioMixer(QObject):
    """Captures system audio (and optionally a microphone) as one stereo stream.

    chunk carries little-endian int16 interleaved PCM at RATE Hz."""
    chunk = Signal(bytes)
    problem = Signal(str)

    def __init__(self, system=True, microphone=False, microphone_id='', parent=None):
        super().__init__(parent)
        self.system = system
        self.microphone = microphone
        self.microphone_id = microphone_id
        self._muted = False
        self._paused = False
        self._sources = []
        self._stop = threading.Event()
        self._thread = None
        self._mic = None
        self._mic_io = None
        self._mic_source = None

    @property
    def has_microphone(self):
        return self._mic_source is not None

    @property
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, value):
        self._muted = bool(value)
        self._apply_gates()

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, value):
        self._paused = bool(value)
        self._apply_gates()

    def _warn(self, message):
        try:
            self.problem.emit(message)
        except RuntimeError:  # the object is already being deleted
            pass

    def _apply_gates(self):
        """Discard, at the source, whatever a mute or pause must not record."""
        for source in list(self._sources):
            source.set_dropping(self._paused or (self._muted and source.name == 'microphone'))

    def start(self):
        """Call from the Qt thread: the microphone is read with QAudioSource,
        which accepts every device format (soundcard rejects mix formats that
        are not WAVE_FORMAT_EXTENSIBLE) and shares the settings' device ids."""
        if self._thread is None:
            if self.microphone:
                try:
                    self._start_microphone()
                except Exception as exc:
                    self.problem.emit(f'microphone: {exc}')
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name='screendepresso-audio', daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._mic is not None:
            self._mic.stop()
            self._mic = self._mic_io = None
        if self._thread is not None:
            self._thread.join(timeout=STOP_TIMEOUT)
            if self._thread.is_alive():
                self._warn('audio thread did not stop in time')
            else:
                self._thread = None

    def _start_microphone(self):
        from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices
        device = next((d for d in QMediaDevices.audioInputs()
                       if bytes(d.id()).decode('utf-8', errors='replace') == self.microphone_id), None)
        device = device or QMediaDevices.defaultAudioInput()
        if device.isNull():
            raise RuntimeError('no input device')
        wanted = QAudioFormat()
        wanted.setSampleRate(RATE)
        wanted.setChannelCount(CHANNELS)
        wanted.setSampleFormat(QAudioFormat.SampleFormat.Float)
        audio_format = wanted if device.isFormatSupported(wanted) else device.preferredFormat()
        self._mic_format = audio_format
        self._mic = QAudioSource(device, audio_format, self)
        self._mic_io = self._mic.start()
        if self._mic_io is None:
            self._mic = None
            raise RuntimeError('could not open the input device')
        self._mic_source = _Source('microphone', None)
        self._mic_io.readyRead.connect(self._read_microphone)

    def _read_microphone(self):
        if self._mic_io is None:
            return
        data = bytes(self._mic_io.readAll())
        if data:
            self._mic_source.push(to_float_frames(data, self._mic_format))

    def _open_sources(self, sc):
        sources = []
        if self.system:
            try:
                speaker = sc.default_speaker()
                loopback = sc.get_microphone(speaker.id, include_loopback=True)
                sources.append(_Source('system', self._open(loopback)))
            except Exception as exc:
                self.problem.emit(f'system audio: {exc}')
        return sources

    @staticmethod
    def _open(device):
        blocksize = RATE//100
        try:
            recorder = device.recorder(samplerate=RATE, channels=CHANNELS, blocksize=blocksize)
            recorder.__enter__()
        except Exception:
            recorder = device.recorder(samplerate=RATE, channels=1, blocksize=blocksize)
            recorder.__enter__()
        return recorder

    def _read(self, source):
        import warnings
        # WASAPI loopback reports gaps while nothing plays; the mixer fills them.
        warnings.filterwarnings('ignore', message='data discontinuity')
        com = _com_init()
        try:
            while not self._stop.is_set():
                try:
                    data = source.recorder.record(numframes=None)
                except Exception as exc:
                    self.problem.emit(f'{source.name}: {exc}')
                    return
                if len(data):
                    source.push(data)
                else:
                    time.sleep(0.005)
        finally:
            # The device is released by the thread that reads it, only once
            # the read has returned: closing it under a pending read would
            # free resources that read is still using.
            try:
                if source.recorder is not None:
                    source.recorder.__exit__(None, None, None)
            except Exception:
                pass
            _com_uninit(com)

    def _run(self):
        # soundcard calls CoInitializeEx when first imported and treats
        # S_FALSE (already initialized) as an error, so the first import
        # initializes COM on this thread itself; later threads do it here.
        com = _com_init() if 'soundcard' in sys.modules else False
        sources, readers = [], []
        try:
            import numpy as np
            try:
                import soundcard as sc
                sources = self._open_sources(sc)
            except Exception as exc:
                self.problem.emit(str(exc))
            for source in sources:
                reader = threading.Thread(target=self._read, args=(source,), daemon=True)
                reader.start()
                readers.append(reader)
            if self._mic_source is not None:
                sources.append(self._mic_source)
            self._sources = sources
            self._apply_gates()
            # Silence is still sent when no device opened, keeping A/V in step
            # and the file's audio track present.
            start = time.monotonic()+LATENCY
            produced = 0
            while not self._stop.wait(TICK):
                target = int((time.monotonic()-start)*RATE)
                count = target-produced
                if count <= 0:
                    continue
                produced = target
                mixed = np.zeros((count, CHANNELS), np.float32)
                for source in sources:
                    data = source.take(count)
                    if source.name == 'microphone' and self.muted:
                        continue
                    mixed += data
                if self.paused:
                    continue
                pcm = (np.clip(mixed, -1.0, 1.0)*32767).astype('<i2')
                self.chunk.emit(pcm.tobytes())
        except Exception as exc:
            self.problem.emit(str(exc))
        finally:
            self._stop.set()
            deadline = time.monotonic()+STOP_TIMEOUT-0.5
            for reader in readers:
                reader.join(timeout=max(0.0, deadline-time.monotonic()))
                if reader.is_alive():
                    # Still inside a device read: it closes the device itself
                    # when that read returns; nothing is freed from here.
                    self._warn('audio device is still busy and will be released when it responds')
            _com_uninit(com)
