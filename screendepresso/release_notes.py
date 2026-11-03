"""Offline, translated notes shipped with the installed application."""
from . import __version__
from .i18n import tr


def installed_release_notes():
    return tr('What’s new in version {version}').format(version=__version__) + '\n\n' + '\n\n'.join(
        '• ' + text for text in (
            tr('Top toolbar menus now open from the lower strip, with more space between icons, labels and menu arrows.'),
            tr('The menu strip follows each button’s actual width in compact and expanded layouts, English and Brazilian Portuguese.'),
            tr('Click the icon to run the main action, or the lower arrow to open its options. Capture, recording and editing commands are unchanged.'),
        )
    )
