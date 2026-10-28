"""Full-monitor region overlays and a thumbnail grid for choosing a window."""
import sys
from PySide6.QtCore import QObject, Qt, QRect, QSize, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QPainter, QColor, QPen
from PySide6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QListView, QAbstractItemView, QDialogButtonBox)
from .appearance import STYLE, dark_palette
from .i18n import tr
from .platform_support import crop_desktop


class RegionOverlay(QWidget):
    def __init__(self, owner, screen):
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        if sys.platform != 'win32':
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        super().__init__(None, flags)
        self.owner = owner
        self.capture_screen = screen
        self.bounds = screen.geometry().intersected(owner.geometry)
        self.image = crop_desktop(owner.pixmap, owner.geometry, self.bounds).toImage()
        self.image.setDevicePixelRatio(1)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setWindowTitle('ScreenDepresso region selection')
        self.winId()
        self.windowHandle().setScreen(screen)
        self.setGeometry(self.bounds)

    def show_on_screen(self):
        self.show()
        # Keep exact screen geometry; a normal managed window can be moved into
        # the work area by GNOME, clipping the dock or the top panel.
        self.setGeometry(self.bounds)
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(self.rect(), self.image)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if self.owner.begin is not None:
            rect = self.owner.selection().translated(-self.bounds.topLeft())
            painter.save()
            painter.setClipRect(rect)
            painter.drawImage(self.rect(), self.image)
            painter.restore()
            painter.setPen(QPen(QColor('#fb7185'), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.begin = self.owner.end = event.globalPosition().toPoint()
            self.owner.repaint_overlays()

    def mouseMoveEvent(self, event):
        if self.owner.begin is not None:
            self.owner.end = event.globalPosition().toPoint()
            self.owner.repaint_overlays()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.owner.begin is not None:
            self.owner.end = event.globalPosition().toPoint()
            self.owner.complete()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.owner.cancel()

    def closeEvent(self, event):
        if not self.owner.closing:
            self.owner.cancel()
        event.accept()


class Selector(QObject):
    selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self, pixmap, geometry, parent=None, screens=None):
        super().__init__(parent)
        self.pixmap, self.geometry = pixmap, geometry
        self.begin = self.end = None
        self.closing = self.done = False
        self.overlays = [RegionOverlay(self, screen) for screen in
                         (QGuiApplication.screens() if screens is None else screens)
                         if screen.geometry().intersects(geometry)]

    def selection(self):
        return QRect(self.begin, self.end).normalized().intersected(self.geometry)

    def repaint_overlays(self):
        for overlay in self.overlays:
            overlay.update()

    def show(self):
        if not self.overlays:
            self.cancel()
            return
        for overlay in self.overlays:
            overlay.show_on_screen()
        active = next((overlay for overlay in self.overlays if overlay.bounds.contains(QCursor.pos())), self.overlays[0])
        active.activateWindow()
        active.setFocus()
        active.grabMouse()
        active.grabKeyboard()

    def close(self):
        self.closing = True
        for overlay in self.overlays:
            if QWidget.mouseGrabber() is overlay:
                overlay.releaseMouse()
            if QWidget.keyboardGrabber() is overlay:
                overlay.releaseKeyboard()
            overlay.close()
            overlay.deleteLater()
        self.overlays.clear()

    def complete(self):
        if self.done:
            return
        rect = self.selection()
        self.done = True
        self.close()
        if rect.width() > 2 and rect.height() > 2:
            self.selected.emit(rect)
        else:
            self.cancelled.emit()

    def cancel(self):
        if not self.done:
            self.done = True
            self.close()
            self.cancelled.emit()


def window_preview(wid, rect, desktop, geometry):
    screen = QGuiApplication.screenAt(rect.center()) or QGuiApplication.primaryScreen()
    try:
        preview = screen.grabWindow(wid) if screen is not None else None
    except RuntimeError:
        preview = None
    if preview is None or preview.isNull():
        preview = crop_desktop(desktop, geometry, rect)
    thumbnail = preview.scaled(QSize(440, 280), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    thumbnail.setDevicePixelRatio(2)
    return thumbnail


class WindowPicker(QDialog):
    def __init__(self, choices, desktop, geometry, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Capture window'))
        self.setPalette(dark_palette())
        self.setStyleSheet(STYLE)
        self.resize(820, 540)
        self.choices = choices
        layout = QVBoxLayout(self)
        label = QLabel(tr('Choose a window preview to capture.'))
        layout.addWidget(label)
        self.grid = QListWidget()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.grid.setIconSize(QSize(220, 140))
        self.grid.setGridSize(QSize(250, 205))
        self.grid.setSpacing(8)
        self.grid.setWordWrap(True)
        self.grid.setToolTip(tr('Double-click a preview to capture that window.'))
        for title, rect, wid in choices:
            preview = window_preview(wid, rect, desktop, geometry)
            item = QListWidgetItem(QIcon(preview), title)
            item.setToolTip(title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
            self.grid.addItem(item)
        layout.addWidget(self.grid)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr('Capture selected window'))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        for button in self.buttons.buttons():
            button.setToolTip(button.text().replace('&', ''))
        layout.addWidget(self.buttons)
        self.grid.itemDoubleClicked.connect(lambda item: self.accept())
        if choices:
            self.grid.setCurrentRow(0)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(choices))

    def selected_window(self):
        row = self.grid.currentRow()
        return self.choices[row] if row >= 0 else None
