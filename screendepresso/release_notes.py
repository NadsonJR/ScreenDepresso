"""Offline, translated notes shipped with the installed application."""
from . import __version__
from .i18n import tr


def installed_release_notes():
    return tr('What’s new in version {version}').format(version=__version__) + '\n\n' + '\n\n'.join(
        '• ' + text for text in (
            tr('Large-image blur is prepared in the background and reused while moving clear regions. A lightweight preview is shown until the full-resolution layer is ready.'),
            tr('Copy and save always use the original resolution and Gaussian filter, never the temporary preview. They may wait for the full layer to finish.'),
            tr('The blur cache is shared across tabs and limited in memory. Transparency, overlapping clear areas, undo/redo and legacy compositing are preserved.'),
            tr('Version 0.7.1 replaces the old 0.7.0 installers. The old source tag remains in the repository history.'),
        )
    )
