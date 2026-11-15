"""Offline, translated notes shipped with the installed application."""
from . import __version__
from .i18n import tr


def installed_release_notes():
    return tr('What’s new in version {version}').format(version=__version__) + '\n\n' + '\n\n'.join(
        '• ' + text for text in (
            tr('Every screenshot is now copied to the clipboard automatically, ready to paste into a chat or another application.'),
            tr('Full screen, individual monitor, window and region captures still save to the workspace and open in the editor.'),
            tr('Use Copy image to copy your edits. On X11, keep ScreenDepresso open while pasting into other applications.'),
        )
    )
