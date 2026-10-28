import os
import sys
from pathlib import Path
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap
from .i18n import tr


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


def desktop_pixel_rect(geometry, rect, scale):
    """Map logical global edges once, avoiding seams with fractional scaling."""
    x = round((rect.x()-geometry.x())*scale)
    y = round((rect.y()-geometry.y())*scale)
    right = round((rect.x()+rect.width()-geometry.x())*scale)
    bottom = round((rect.y()+rect.height()-geometry.y())*scale)
    return QRect(x, y, right-x, bottom-y)


def crop_desktop(pixmap, geometry, rect):
    rect = rect.intersected(geometry)
    if rect.isEmpty():
        raise RuntimeError(tr('The selected area is outside the available monitors.'))
    return pixmap.copy(desktop_pixel_rect(geometry, rect, pixmap.devicePixelRatio()))


def capture_desktop(screen_name=None):
    screens = QGuiApplication.screens()
    if screen_name is not None:
        screens = [screen for screen in screens if screen.name() == screen_name]
    if not screens:
        raise RuntimeError(tr('The selected monitor is no longer available.'))
    geometry = QRect()
    for screen in screens:
        geometry = geometry.united(screen.geometry())
    scale = max(screen.devicePixelRatio() for screen in screens)
    image = QImage(round(geometry.width()*scale), round(geometry.height()*scale), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    if image.isNull():
        raise RuntimeError(tr('The desktop image is too large to capture.'))
    painter = QPainter(image)
    try:
        for screen in sorted(screens, key=lambda screen: screen.devicePixelRatio()):
            rect = screen.geometry()
            pixmap = screen.grabWindow(0, 0, 0, rect.width(), rect.height())
            if pixmap.isNull():
                raise RuntimeError(tr('Screen capture is unavailable for monitor: ')+screen.name())
            painter.drawImage(desktop_pixel_rect(geometry, rect, scale), pixmap.toImage())
    finally:
        painter.end()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(scale)
    return pixmap, geometry
