"""Offline, translated notes shipped with the installed application."""
from . import __version__
from .i18n import tr


def installed_release_notes():
    return tr('What’s new in version {version}').format(version=__version__) + '\n\n' + '\n\n'.join(
        '• ' + text for text in (
            tr('Updated dark interface following the ScreenDepresso visual identity guide, with consistent colors, typography and icons.'),
            tr('Labeled tools and a contextual properties bar preserve existing annotation controls, shortcuts and continuous drawing.'),
            tr('The empty editor offers capture, open, paste and image dropping. Compact windows use smaller toolbars and scrollable properties.'),
            tr('Version 0.7.0 remains available as a separate download if you prefer the previous design. Reinstall it manually to roll back.'),
        )
    )
