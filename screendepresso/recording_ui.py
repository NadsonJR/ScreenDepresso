"""Floating recording controls, countdown and region frame.

These windows are excluded from the recording where the platform allows it
(Windows 10 2004+ and macOS); elsewhere they are kept outside the region.
"""
import sys
from PySide6.QtCore import QPoint, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget
from .i18n import tr
from .theme import TOKENS

OVERLAY_FLAGS = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint


def exclude_from_capture(widget):
    """Keep a helper window out of screen captures when the OS supports it."""
    try:
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            user = ctypes.WinDLL('user32', use_last_error=True)
            user.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
            user.SetWindowDisplayAffinity.restype = wintypes.BOOL
            # WDA_EXCLUDEFROMCAPTURE; older Windows versions just ignore it.
            user.SetWindowDisplayAffinity(int(widget.winId()), 0x11)
        elif sys.platform == 'darwin':
            import objc
            view = objc.objc_object(c_void_p=int(widget.winId()))
            view.window().setSharingType_(0)  # NSWindowSharingNone
    except Exception:
        pass


def format_duration(milliseconds):
    seconds = max(0, int(milliseconds))//1000
    hours, rest = divmod(seconds, 3600)
    return (f'{hours}:' if hours else '')+f'{rest//60:02d}:{rest % 60:02d}'


class RecordingBar(QWidget):
    stop_requested = Signal()
    pause_requested = Signal()
    discard_requested = Signal()
    mute_toggled = Signal(bool)

    def __init__(self):
        super().__init__(None, OVERLAY_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle(tr('Recording'))
        self._drag = None
        self._blink = True
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 8, 6)
        layout.setSpacing(4)
        self.dot = QLabel('●')
        self.dot.setStyleSheet(f"color: {TOKENS['danger']}; font-size: 15px;")
        layout.addWidget(self.dot)
        self.time = QLabel('00:00')
        font = QFont(self.font())
        font.setPixelSize(14)
        font.setBold(True)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.time.setFont(font)
        self.time.setMinimumWidth(56)
        self.time.setStyleSheet(f"color: {TOKENS['text']};")
        layout.addWidget(self.time)

        def button(text, tip, callback, checkable=False):
            widget = QToolButton()
            widget.setText(text)
            widget.setToolTip(tip)
            widget.setCheckable(checkable)
            widget.setAutoRaise(True)
            widget.setCursor(Qt.CursorShape.PointingHandCursor)
            widget.setFixedSize(30, 28)
            widget.setStyleSheet(
                f"QToolButton {{ color: {TOKENS['text']}; border: none; border-radius: 6px; font-size: 14px; }}"
                f"QToolButton:hover {{ background: rgba(255,255,255,28); }}"
                f"QToolButton:checked {{ color: {TOKENS['danger']}; }}")
            widget.clicked.connect(callback)
            layout.addWidget(widget)
            return widget
        self.pause = button('❚❚', tr('Pause recording'), self.pause_requested.emit)
        self.mute = button('🎙', tr('Mute microphone'), lambda: self.toggle_mute(), checkable=True)
        self.stop = button('■', tr('Stop and save'), self.stop_requested.emit)
        self.stop.setStyleSheet(self.stop.styleSheet()+f"QToolButton {{ color: {TOKENS['danger']}; font-size: 17px; }}")
        self.discard = button('✕', tr('Discard recording'), self.discard_requested.emit)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._blink_dot)
        self.adjustSize()

    def toggle_mute(self):
        muted = self.mute.isChecked()
        self.mute.setToolTip(tr('Unmute microphone') if muted else tr('Mute microphone'))
        self.mute_toggled.emit(muted)

    def set_microphone(self, available):
        self.mute.setVisible(available)
        self.mute.setChecked(False)
        self.mute.setToolTip(tr('Mute microphone'))
        self.adjustSize()

    def set_state(self, state):
        paused = state == 'paused'
        self.pause.setText('▶' if paused else '❚❚')
        self.pause.setToolTip(tr('Resume recording') if paused else tr('Pause recording'))
        if state == 'recording':
            self.timer.start(600)
        else:
            self.timer.stop()
            self.dot.setVisible(True)
        self.dot.setStyleSheet(f"color: {TOKENS['warning'] if paused else TOKENS['danger']}; font-size: 15px;")

    def set_duration(self, milliseconds):
        self.time.setText(format_duration(milliseconds))

    def _blink_dot(self):
        self._blink = not self._blink
        self.dot.setVisible(self._blink)

    def place(self, screen_geometry, region=None):
        """Bottom-center of the screen, or just below/above the region."""
        self.adjustSize()
        size = self.size()
        x = screen_geometry.center().x()-size.width()//2
        y = screen_geometry.bottom()-size.height()-48
        if region is not None:
            x = region.center().x()-size.width()//2
            below = region.bottom()+12
            above = region.top()-size.height()-12
            if below+size.height() <= screen_geometry.bottom():
                y = below
            elif above >= screen_geometry.top():
                y = above
            else:
                y = region.bottom()-size.height()-12
        x = max(screen_geometry.left()+8, min(x, screen_geometry.right()-size.width()-8))
        self.move(x, y)

    def show_bar(self):
        self.show()
        exclude_from_capture(self)
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QColor(TOKENS['surface']))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint()-self.pos()

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            self.move(event.globalPosition().toPoint()-self._drag)

    def mouseReleaseEvent(self, event):
        self._drag = None


class RegionFrame(QWidget):
    """Click-through dashed border drawn just outside the recorded region."""
    MARGIN = 4

    def __init__(self, region):
        flags = OVERLAY_FLAGS | Qt.WindowType.WindowTransparentForInput
        if sys.platform.startswith('linux'):
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(region.adjusted(-self.MARGIN, -self.MARGIN, self.MARGIN, self.MARGIN))

    def show_frame(self):
        self.show()
        exclude_from_capture(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor(TOKENS['danger']), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))


class Countdown(QWidget):
    """A small 3-2-1 badge; click or Esc cancels."""
    finished = Signal()
    cancelled = Signal()

    def __init__(self, seconds, screen_geometry):
        super().__init__(None, OVERLAY_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.remaining = seconds
        self.setFixedSize(180, 180)
        self.move(screen_geometry.center()-QPoint(90, 90))
        self.setToolTip(tr('Click or press Esc to cancel'))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self):
        self.show()
        exclude_from_capture(self)
        self.raise_()
        self.activateWindow()
        self.timer.start(1000)

    def _tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.timer.stop()
            self.hide()
            # Let the compositor remove the badge before the first frame.
            QTimer.singleShot(120, self.finished.emit)
        else:
            self.update()

    def cancel(self):
        self.timer.stop()
        self.hide()
        self.cancelled.emit()

    def mousePressEvent(self, event):
        self.cancel()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 170))
        painter.drawEllipse(self.rect().adjusted(4, 4, -4, -4))
        font = QFont(self.font())
        font.setPixelSize(84)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor('white'))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self.remaining))
        font.setPixelSize(12)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 190))
        painter.drawText(QRect(0, 128, 180, 20), Qt.AlignmentFlag.AlignCenter, tr('Esc cancels'))
