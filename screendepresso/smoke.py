"""Installed-bundle checks that do not require a desktop or microphone consent."""
from pathlib import Path
import time


def verify_video_bundle(directory):
    """Encode synthetic frames and decode the resulting MP4 with bundled Qt.

    This validates FFmpeg, its software fallback encoder and playback plugins.
    Real screen capture and OS permission dialogs still need a desktop session.
    """
    from PySide6.QtCore import QCoreApplication, QSize, QUrl
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtMultimedia import (QMediaCaptureSession, QMediaFormat, QMediaPlayer,
                                      QMediaRecorder, QVideoFrame, QVideoFrameInput, QVideoSink)

    path = Path(directory)/'recording-smoke.mp4'
    errors = []
    session = QMediaCaptureSession()
    recorder = QMediaRecorder()
    frames = QVideoFrameInput()
    session.setVideoFrameInput(frames)
    session.setRecorder(recorder)
    media = QMediaFormat(QMediaFormat.FileFormat.MPEG4)
    media.setVideoCodec(QMediaFormat.VideoCodec.MPEG4)
    recorder.setMediaFormat(media)
    recorder.setVideoResolution(QSize(320, 240))
    recorder.setVideoFrameRate(15)
    recorder.setAutoStop(True)
    recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))
    recorder.errorOccurred.connect(lambda error, message: errors.append(message))

    def wait_for(predicate, description, timeout=5):
        deadline = time.monotonic()+timeout
        while not predicate():
            if errors:
                raise RuntimeError('Video bundle smoke test: '+errors[0])
            if time.monotonic() >= deadline:
                raise RuntimeError('Video bundle smoke test timed out: '+description)
            QCoreApplication.processEvents()
            time.sleep(.005)
        if errors:
            raise RuntimeError('Video bundle smoke test: '+errors[0])

    player = QMediaPlayer()
    sink = QVideoSink()
    player.setVideoSink(sink)
    player.errorOccurred.connect(lambda error, message: errors.append(message))
    decoded = []
    sink.videoFrameChanged.connect(lambda frame: decoded.append(frame.size()) if frame.isValid() else None)
    try:
        recorder.record()
        wait_for(lambda: recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState, 'start encoder')
        for index in range(12):
            image = QImage(320, 240, QImage.Format.Format_RGB32)
            image.fill(QColor('red' if index % 2 else 'blue'))
            frame = QVideoFrame(image)
            frame.setStartTime(index*1_000_000//15)
            frame.setEndTime((index+1)*1_000_000//15)
            wait_for(lambda: frames.sendVideoFrame(frame), 'send video frame')
        wait_for(lambda: frames.sendVideoFrame(QVideoFrame()), 'send end of stream')
        wait_for(lambda: recorder.recorderState() == QMediaRecorder.RecorderState.StoppedState, 'finalize MP4')
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError('Video bundle smoke test did not create an MP4')
        player.setSource(QUrl.fromLocalFile(str(path)))
        player.play()
        wait_for(lambda: bool(decoded), 'decode recorded MP4')
        if decoded[0] != QSize(320, 240):
            raise RuntimeError('Video bundle smoke test decoded an unexpected frame size')
    finally:
        player.stop()
        player.setSource(QUrl())
        recorder.stop()
        session.setRecorder(None)
        session.setVideoFrameInput(None)
    return 'Recording encode/decode: OK (MPEG-4, 320x240)'
