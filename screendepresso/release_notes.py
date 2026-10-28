"""Offline, translated notes shipped with the installed application."""
from . import __version__
from .i18n import tr


def installed_release_notes():
    return tr('What’s new in version {version}').format(version=__version__) + '\n\n' + '\n\n'.join(
        '• ' + text for text in (
            tr('Right-click an image tab to close all tabs, only that tab, or all other tabs.'),
            tr('Tabs with unsaved edits still offer Save, Discard and Cancel. Cancel stops closing the remaining tabs.'),
            tr('Right-click a workspace thumbnail to duplicate it or move it to the system trash. Keyboard shortcuts and dragging images into the editor are preserved.'),
            tr('Refresh workspace thumbnails using the icon in the upper-right corner.'),
            tr('Read the installed version’s release notes in Settings → Updates, even without an internet connection.'),
        )
    )
