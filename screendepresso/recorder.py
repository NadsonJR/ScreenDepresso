"""Lightweight screen recording on top of Qt Multimedia (FFmpeg backend).

Screens and windows are handed straight to the encoder. H.264 is preferred:
Media Foundation on Windows, VideoToolbox on macOS and NVENC/VA-API on Linux.
Qt's bundled FFmpeg has no software H.264 encoder on Linux, so recordings fall
back to MPEG-4 Part 2 (still .mp4) when H.264 is missing or fails to start. Regions are cropped
from the screen frames and fed through QVideoFrameInput. QtMultimedia is
imported only when a recording starts, so idle startup stays light.
"""
import time
from pathlib import Path
from PySide6.QtCore import QObject, QRect, QUrl, Signal
from .i18n import tr

FRAME_RATES = (15, 24, 30, 60)
QUALITIES = {'low': 'Low (smaller files)', 'normal': 'Normal', 'high': 'High', 'very_high': 'Very high'}
COUNTDOWNS = (0, 3, 5)


def default_recording():
    return {'fps': 30, 'quality': 'normal',
            'countdown': 3, 'microphone': False, 'microphone_device': ''}


def normalize_recording(data):
    """Return valid recording options, keeping each valid stored value."""
    result = default_recording()
    if not isinstance(data, dict):
        return result
    for key, allowed in (('fps', FRAME_RATES), ('countdown', COUNTDOWNS)):
        if type(data.get(key)) is int and data[key] in allowed:
            result[key] = data[key]
    if data.get('quality') in QUALITIES:
        result['quality'] = data['quality']
    if isinstance(data.get('microphone'), bool):
        result['microphone'] = data['microphone']
    if isinstance(data.get('microphone_device'), str):
        result['microphone_device'] = data['microphone_device']
    return result


def region_crop(rect, screen_geometry, frame_size):
    """Map a logical global region to even-sized pixels of a screen frame."""
    scale_x = frame_size.width()/max(1, screen_geometry.width())
    scale_y = frame_size.height()/max(1, screen_geometry.height())
    rect = rect.intersected(screen_geometry)
    x = round((rect.x()-screen_geometry.x())*scale_x)
    y = round((rect.y()-screen_geometry.y())*scale_y)
    width = min(round(rect.width()*scale_x), frame_size.width()-x)
    height = min(round(rect.height()*scale_y), frame_size.height()-y)
    # H.264 encoders require even dimensions.
    return QRect(x, y, max(2, width - width % 2), max(2, height - height % 2))


def microphones():
    from PySide6.QtMultimedia import QMediaDevices
    return [(device.description(), device_key(device)) for device in QMediaDevices.audioInputs()]


def device_key(device):
    return bytes(device.id()).decode('utf-8', errors='replace')


def remove_later(path, delay=1500):
    """Delete an unfinished recording and its empty in-progress folder."""
    from PySide6.QtCore import QTimer

    def remove():
        try:
            path.unlink(missing_ok=True)
            path.parent.rmdir()
        except OSError:
            pass
    if delay:
        QTimer.singleShot(delay, remove)
    else:
        remove()


def preferred_codec():
    from PySide6.QtMultimedia import QMediaFormat
    supported = QMediaFormat(QMediaFormat.FileFormat.MPEG4).supportedVideoCodecs(QMediaFormat.ConversionMode.Encode)
    return 'h264' if QMediaFormat.VideoCodec.H264 in supported else 'mpeg4'


def capturable_window(title):
    """Find the Qt window source for a picked window, matching its title.

    Returns None when no window or several windows share the title, so the
    caller can record the window's area instead of a wrong window."""
    from PySide6.QtMultimedia import QWindowCapture
    windows = QWindowCapture.capturableWindows()
    matches = [window for window in windows if window.isValid() and window.description() == title]
    return matches[0] if len(matches) == 1 else None


class ScreenRecorder(QObject):
    state_changed = Signal(str)
    duration_changed = Signal(int)
    saved = Signal(str)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = 'idle'
        self.path = None
        self._objects = []
        self._recorder = None
        self._audio = None
        self._discard = False
        self._error = None
        self._request = None
        self._duration = 0
        self.codec = None

    @property
    def active(self):
        return self.state in ('starting', 'recording', 'paused', 'stopping')

    def start(self, target, options, path, codec=None):
        """Record target: ('screen', QScreen), ('window', QCapturableWindow) or
        ('region', QScreen, QRect in global logical coordinates)."""
        if self.active:
            raise RuntimeError(tr('A recording is already in progress.'))
        self._begin(target, options, path, codec or preferred_codec())

    def _begin(self, target, options, path, codec):
        from PySide6.QtMultimedia import (QAudioInput, QMediaCaptureSession, QMediaDevices, QMediaFormat,
                                          QMediaRecorder, QScreenCapture, QWindowCapture)
        options = normalize_recording(options)
        fps = options['fps']
        self.path = Path(path)
        self._discard = False
        self._error = None
        self._request = (target, options, path)
        self._duration = 0
        self.codec = codec
        session = QMediaCaptureSession(self)
        recorder = QMediaRecorder(self)
        media = QMediaFormat(QMediaFormat.FileFormat.MPEG4)
        media.setVideoCodec(QMediaFormat.VideoCodec.H264 if codec == 'h264' else QMediaFormat.VideoCodec.MPEG4)
        media.setAudioCodec(QMediaFormat.AudioCodec.AAC)
        recorder.setMediaFormat(media)
        recorder.setQuality({'low': QMediaRecorder.Quality.LowQuality, 'normal': QMediaRecorder.Quality.NormalQuality,
                             'high': QMediaRecorder.Quality.HighQuality,
                             'very_high': QMediaRecorder.Quality.VeryHighQuality}[options['quality']])
        recorder.setEncodingMode(QMediaRecorder.EncodingMode.ConstantQualityEncoding)
        recorder.setVideoFrameRate(fps)
        recorder.setOutputLocation(QUrl.fromLocalFile(str(self.path)))
        recorder.recorderStateChanged.connect(self._recorder_state)
        recorder.durationChanged.connect(self._duration_changed)
        recorder.errorOccurred.connect(lambda error, message: self._fail(message))
        session.setRecorder(recorder)
        self._objects = [session, recorder]
        kind = target[0]
        if kind == 'window':
            source = QWindowCapture(self)
            source.setWindow(target[1])
            session.setWindowCapture(source)
        elif kind == 'screen':
            source = QScreenCapture(self)
            source.setScreen(target[1])
            session.setScreenCapture(source)
        elif kind == 'region':
            source = QScreenCapture(self)
            source.setScreen(target[1])
            self._setup_region(session, source, target[1], target[2], fps)
        else:
            raise ValueError(kind)
        source.setMaximumFrameRate(fps)
        source.errorOccurred.connect(lambda error, message: self._fail(message))
        self._objects.append(source)
        self._audio = None
        if options['microphone']:
            devices = QMediaDevices.audioInputs()
            device = next((d for d in devices if device_key(d) == options['microphone_device']), None)
            device = device or QMediaDevices.defaultAudioInput()
            if not device.isNull():
                self._audio = QAudioInput(device, self)
                session.setAudioInput(self._audio)
                self._objects.append(self._audio)
        self._recorder = recorder
        self._set_state('starting')
        source.start()
        recorder.record()

    def _duration_changed(self, milliseconds):
        self._duration = max(self._duration, int(milliseconds))
        self.duration_changed.emit(int(milliseconds))

    def _setup_region(self, session, source, screen, rect, fps):
        from PySide6.QtMultimedia import QMediaCaptureSession, QVideoFrame, QVideoFrameInput, QVideoSink
        preview = QMediaCaptureSession(self)
        preview.setScreenCapture(source)
        sink = QVideoSink(self)
        preview.setVideoSink(sink)
        frames = QVideoFrameInput(self)
        session.setVideoFrameInput(frames)
        self._objects.extend([preview, sink, frames])
        interval = 1/fps
        clock = {'crop': None, 'start': None, 'paused': 0.0, 'paused_at': None, 'last': None}
        self._clock = clock

        def send(frame):
            if self.state != 'recording' or not frame.isValid():
                return
            now = time.monotonic()
            if clock['last'] is not None and now-clock['last'] < interval*.9:
                return
            if clock['crop'] is None:
                clock['crop'] = region_crop(rect, screen.geometry(), frame.size())
            if clock['start'] is None:
                clock['start'] = now
            clock['last'] = now
            image = frame.toImage().copy(clock['crop'])
            output = QVideoFrame(image)
            stamp = int((now-clock['start']-clock['paused'])*1_000_000)
            output.setStartTime(stamp)
            output.setEndTime(stamp+int(interval*1_000_000))
            frames.sendVideoFrame(output)
        sink.videoFrameChanged.connect(send)

    def pause(self):
        if self.state == 'recording' and self._recorder is not None:
            clock = getattr(self, '_clock', None)
            if clock is not None:
                clock['paused_at'] = time.monotonic()
            self._recorder.pause()

    def resume(self):
        if self.state == 'paused' and self._recorder is not None:
            clock = getattr(self, '_clock', None)
            if clock is not None and clock['paused_at'] is not None:
                clock['paused'] += time.monotonic()-clock['paused_at']
                clock['paused_at'] = None
            self._recorder.record()

    def toggle_pause(self):
        self.resume() if self.state == 'paused' else self.pause()

    def set_microphone_muted(self, muted):
        if self._audio is not None:
            self._audio.setMuted(muted)

    @property
    def has_microphone(self):
        return self._audio is not None

    def stop(self, discard=False):
        if self._recorder is None or self.state in ('idle', 'stopping'):
            return
        self._discard = discard
        self._set_state('stopping')
        self._recorder.stop()

    def wait_stopped(self, timeout=5.0):
        """Finalize the file before the application quits."""
        from PySide6.QtCore import QCoreApplication, QEventLoop
        self.stop()
        deadline = time.monotonic()+timeout
        while self.active and time.monotonic() < deadline:
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)

    def _recorder_state(self, state):
        from PySide6.QtMultimedia import QMediaRecorder
        if state == QMediaRecorder.RecorderState.RecordingState:
            self._set_state('recording')
        elif state == QMediaRecorder.RecorderState.PausedState:
            self._set_state('paused')
        elif state == QMediaRecorder.RecorderState.StoppedState and self.state != 'idle':
            self._finish()

    def _fail(self, message):
        if self.state == 'idle':
            return
        if self.codec == 'h264' and self._duration == 0 and self.state in ('starting', 'recording'):
            # No H.264 encoder usable here (e.g. Linux without NVENC/VA-API):
            # restart silently with the software MPEG-4 encoder.
            partial = self.path
            self._teardown()
            target, options, path = self._request
            # The stopped encoder may still hold the partial file for a moment.
            remove_later(partial)
            try:
                self._begin(target, options, Path(path).with_name(Path(path).stem+'-mpeg4.mp4'), 'mpeg4')
            except Exception as exc:
                self._set_state('idle')
                self.failed.emit(str(exc))
            return
        self._error = message or tr('Recording failed.')
        if self._recorder is not None and self.state != 'stopping':
            self._discard = True
            self._set_state('stopping')
            self._recorder.stop()
            if self._recorder.recorderState().name == 'StoppedState':
                self._finish()

    def _teardown(self):
        for item in reversed(self._objects):
            item.blockSignals(True)
            if hasattr(item, 'stop'):
                try:
                    item.stop()
                except RuntimeError:
                    pass
            item.deleteLater()
        self._objects, self._recorder, self._audio, self._clock = [], None, None, None

    def _finish(self):
        path, discard, error = self.path, self._discard, self._error
        self._teardown()
        self._set_state('idle')
        if (discard or error) and path is not None:
            remove_later(path, 0)
        if error:
            self.failed.emit(error)
        elif not discard and path is not None and path.exists():
            self.saved.emit(str(path))
        elif not discard:
            self.failed.emit(tr('Recording failed.'))

    def _set_state(self, state):
        if state != self.state:
            self.state = state
            self.state_changed.emit(state)
