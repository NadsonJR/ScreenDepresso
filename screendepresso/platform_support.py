import os
import sys
from pathlib import Path
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap


def global_hotkeys_available():
    return sys.platform == 'win32' or bool(os.environ.get('DISPLAY'))


def config_path():
    if os.environ.get('XDG_CONFIG_HOME'):
        return Path(os.environ['XDG_CONFIG_HOME'])/'screendepresso/settings.json'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData/Local'))/'ScreenDepresso/settings.json'
    return Path.home()/'.config/screendepresso/settings.json'


def data_directory():
    if os.environ.get('XDG_DATA_HOME'):
        return Path(os.environ['XDG_DATA_HOME'])/'screendepresso'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData/Local'))/'ScreenDepresso/captures'
    return Path.home()/'.local/share/screendepresso'


def capture_desktop():
    screens = QGuiApplication.screens()
    if sys.platform != 'win32':
        pixmap = QGuiApplication.primaryScreen().grabWindow(0)
        return pixmap, QRect(QPoint(0, 0), pixmap.deviceIndependentSize().toSize())
    geometry = QRect()
    for screen in screens:
        geometry = geometry.united(screen.geometry())
    image = QImage(geometry.size(), QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    try:
        for screen in screens:
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                raise RuntimeError('Windows screen capture is unavailable.')
            painter.drawImage(screen.geometry().translated(-geometry.topLeft()), pixmap.toImage())
    finally:
        painter.end()
    return QPixmap.fromImage(image), geometry
