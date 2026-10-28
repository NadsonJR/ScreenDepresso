"""Offline, translated notes shipped with the installed application."""
from . import __version__
from .i18n import tr


def installed_release_notes():
    return tr('What’s new in version {version}').format(version=__version__) + '\n\n' + '\n\n'.join(
        '• ' + text for text in (
            tr('Update controls appear side by side, with the installed version centered above them.'),
            tr('Arrow, rectangle, text, balloon and blur tools stay active for repeated annotations. Choose Select/Move to edit existing objects.'),
            tr('macOS 15 or later is supported on Apple Silicon and Intel, with native global hotkeys, screen permissions, window previews and DMG installers.'),
            tr('On macOS, updates are verified before opening the disk image. Quit the old app and replace it in Applications.'),
        )
    )
