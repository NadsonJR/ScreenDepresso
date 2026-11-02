"""Offline, translated notes shipped with the installed application."""
from . import __version__
from .i18n import tr


def installed_release_notes():
    return tr('What’s new in version {version}').format(version=__version__) + '\n\n' + '\n\n'.join(
        '• ' + text for text in (
            tr('Screen recording: capture a monitor, window or region as MP4. Start or stop with the Record button, tray menu or recording hotkey.'),
            tr('Pause, resume, mute the microphone, save or discard with the floating recording controls. Configure frame rate, quality, countdown and microphone in Settings.'),
            tr('Recordings appear in the workspace with thumbnails and open in your video player. The workspace image limit does not delete videos.'),
            tr('Existing capture shortcuts and preferences are preserved. Discarding restores the editor, and microphone permission is requested when needed on macOS.'),
            tr('Inside/outside blur and the large-image blur cache remain available.'),
        )
    )
