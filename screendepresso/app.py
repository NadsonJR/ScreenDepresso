import json
import os
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageFilter
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal, QObject
from PySide6.QtGui import QAction, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QListWidget, QFileDialog, QMessageBox,
    QInputDialog, QScrollArea, QSystemTrayIcon, QMenu, QStyle)


class History:
    def __init__(self, directory=None):
        self.directory = Path(directory or Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'screendepresso')
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, image):
        path = self.directory / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.png')
        if not image.save(str(path), 'PNG'):
            raise OSError('Não foi possível salvar a captura.')
        return path

    def entries(self):
        return sorted(self.directory.glob('*.png'), reverse=True)


class Canvas(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.tool = 'seta'
        self.begin = None
        self.end = None
        self.undo_stack = []
        self.setMouseTracking(True)

    def load(self, image):
        self.image = image.convertToFormat(QImage.Format.Format_ARGB32)
        self.undo_stack.clear()
        self.resize(self.image.size())
        self.setFixedSize(self.image.size())
        self.update()

    def undo(self):
        if self.undo_stack:
            self.image = self.undo_stack.pop()
            self.setFixedSize(self.image.size())
            self.update()
            self.changed.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.image)
        if self.begin is not None and self.end is not None:
            painter.setPen(QPen(QColor('#f43f5e'), 2, Qt.PenStyle.DashLine))
            painter.drawRect(QRect(self.begin, self.end).normalized())

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.image.isNull():
            return
        self.begin = event.position().toPoint()
        self.end = self.begin
        if self.tool == 'texto':
            text, ok = QInputDialog.getText(self, 'Texto', 'Texto da anotação:')
            if ok and text:
                self.undo_stack.append(self.image.copy())
                painter = QPainter(self.image)
                painter.setPen(QColor('#ef233c'))
                font = painter.font()
                font.setPixelSize(24)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(self.begin, text)
                painter.end()
                self.changed.emit()
            self.begin = self.end = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.begin is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.begin is None or event.button() != Qt.MouseButton.LeftButton:
            return
        end = event.position().toPoint()
        rect = QRect(self.begin, end).normalized().intersected(self.image.rect())
        if rect.width() > 2 and rect.height() > 2:
            self.undo_stack.append(self.image.copy())
            if self.tool == 'recorte':
                self.image = self.image.copy(rect)
                self.setFixedSize(self.image.size())
            elif self.tool == 'desfoque':
                part = self.image.copy(rect).convertToFormat(QImage.Format.Format_RGBA8888)
                pil = Image.frombytes('RGBA', (part.width(), part.height()), bytes(part.bits()), 'raw', 'RGBA', part.bytesPerLine())
                data = pil.filter(ImageFilter.GaussianBlur(14)).tobytes()
                blurred = QImage(data, part.width(), part.height(), part.width() * 4, QImage.Format.Format_RGBA8888).copy()
                painter = QPainter(self.image)
                painter.drawImage(rect.topLeft(), blurred)
                painter.end()
            else:
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(QPen(QColor('#ef233c'), 4))
                if self.tool == 'retângulo':
                    painter.drawRect(rect.adjusted(2, 2, -2, -2))
                else:
                    import math
                    painter.drawLine(self.begin, end)
                    angle = math.atan2(end.y() - self.begin.y(), end.x() - self.begin.x())
                    for offset in (-0.5, 0.5):
                        tip = QPoint(round(end.x() - 20 * math.cos(angle + offset)), round(end.y() - 20 * math.sin(angle + offset)))
                        painter.drawLine(end, tip)
                painter.end()
            self.changed.emit()
        self.begin = self.end = None
        self.update()


class Selector(QWidget):
    selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self, pixmap, geometry):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.pixmap = pixmap
        self.begin = self.end = None
        self.setGeometry(geometry)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if self.begin is not None:
            rect = QRect(self.begin, self.end).normalized()
            painter.drawPixmap(rect, self.pixmap, rect)
            painter.setPen(QPen(QColor('#fb7185'), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin = self.end = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.begin is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.begin is not None and event.button() == Qt.MouseButton.LeftButton:
            rect = QRect(self.begin, event.position().toPoint()).normalized().intersected(self.rect())
            self.close()
            if rect.width() > 2 and rect.height() > 2:
                self.selected.emit(rect)
            else:
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.cancelled.emit()


class Hotkeys(QObject):
    capture = Signal(str)
    failed = Signal(str)

    def run(self):
        try:
            from Xlib import X, XK, display, error
            connection = display.Display()
            root = connection.screen().root
            bindings = {}
            errors = []
            def on_error(err, request):
                errors.append(str(err))
            connection.set_error_handler(on_error)
            for key, mode in [('1', 'tela'), ('2', 'janela'), ('3', 'região')]:
                code = connection.keysym_to_keycode(XK.string_to_keysym(key))
                bindings[code] = mode
                for locks in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                    root.grab_key(code, X.ControlMask | X.ShiftMask | locks, False, X.GrabModeAsync, X.GrabModeAsync)
            connection.sync()
            if errors:
                root.ungrab_key(X.AnyKey, X.AnyModifier)
                connection.sync()
                self.failed.emit('Atalhos ocupados por outro aplicativo. Use os botões de captura.')
                connection.close()
                return
            while True:
                event = connection.next_event()
                if event.type == X.KeyPress and event.detail in bindings:
                    self.capture.emit(bindings[event.detail])
        except Exception as exc:
            self.failed.emit(f'Atalhos indisponíveis: {exc}')


def windows():
    from Xlib import X, display
    connection = display.Display()
    try:
        root = connection.screen().root
        prop = root.get_full_property(connection.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType)
        result = []
        for wid in prop.value if prop is not None else []:
            try:
                window = connection.create_resource_object('window', int(wid))
                title = window.get_wm_name() or ''
                if title and title != 'ScreenDepresso':
                    geometry = window.get_geometry()
                    position = root.translate_coords(window, 0, 0)
                    result.append((title, QRect(position.x, position.y, geometry.width, geometry.height)))
            except Exception:
                continue
        return result
    finally:
        connection.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ScreenDepresso')
        self.resize(1100, 760)
        self.history = History()
        self.canvas = Canvas()
        container = QWidget()
        layout = QVBoxLayout(container)
        capture_row = QHBoxLayout()
        for mode, label in [('tela', 'Tela inteira'), ('janela', 'Janela'), ('região', 'Região')]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, m=mode: self.capture(m))
            capture_row.addWidget(button)
        layout.addLayout(capture_row)
        tools = QHBoxLayout()
        for name in ['seta', 'texto', 'retângulo', 'desfoque', 'recorte']:
            button = QPushButton(name.capitalize())
            button.clicked.connect(lambda checked=False, t=name: setattr(self.canvas, 'tool', t))
            tools.addWidget(button)
        for label, callback in [('Desfazer', self.canvas.undo), ('Copiar', self.copy), ('Salvar', self.save)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            tools.addWidget(button)
        layout.addLayout(tools)
        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setMaximumWidth(240)
        self.list.itemClicked.connect(self.open_history)
        body.addWidget(self.list)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        body.addWidget(scroll, 1)
        layout.addLayout(body)
        self.setCentralWidget(container)
        self.refresh()
        self.statusBar().showMessage('Ctrl+Shift+1: tela • Ctrl+Shift+2: janela • Ctrl+Shift+3: região')
        self.hotkeys = Hotkeys()
        self.hotkeys.capture.connect(self.capture)
        self.hotkeys.failed.connect(lambda message: self.statusBar().showMessage(message))
        if os.environ.get('DISPLAY'):
            threading.Thread(target=self.hotkeys.run, daemon=True).start()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)
        menu.addAction('Abrir', self.showNormal)
        for mode in ['tela', 'janela', 'região']:
            menu.addAction('Capturar ' + mode, lambda m=mode: self.capture(m))
        menu.addAction('Sair', QApplication.quit)
        self.tray.setContextMenu(menu)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def refresh(self):
        self.list.clear()
        for path in self.history.entries():
            self.list.addItem(path.name)

    def open_history(self, item):
        self.canvas.load(QImage(str(self.history.directory / item.text())))

    def capture(self, mode):
        target = None
        if mode == 'janela':
            try:
                choices = windows()
                if not choices:
                    raise RuntimeError('Nenhuma janela disponível.')
                labels = [f'{i + 1}. {title}' for i, (title, _) in enumerate(choices)]
                chosen, ok = QInputDialog.getItem(self, 'Capturar janela', 'Janela visível (sem obstruções):', labels, 0, False)
                if not ok:
                    return
                target = choices[labels.index(chosen)][1]
            except Exception as exc:
                QMessageBox.warning(self, 'Captura de janela', str(exc))
                return
        self.hide()
        QTimer.singleShot(350, lambda: self.take_capture(mode, target))

    def take_capture(self, mode, target):
        try:
            screen = QApplication.primaryScreen()
            # X11 root captures the entire virtual desktop, including other monitors.
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                raise RuntimeError('Captura indisponível. Execute numa sessão X11.')
            if mode == 'região':
                geometry = QRect(QPoint(0, 0), pixmap.deviceIndependentSize().toSize())
                self.selector = Selector(pixmap, geometry)
                self.selector.selected.connect(lambda rect: self.finish_capture(pixmap.copy(QRect(round(rect.x() * pixmap.devicePixelRatio()), round(rect.y() * pixmap.devicePixelRatio()), round(rect.width() * pixmap.devicePixelRatio()), round(rect.height() * pixmap.devicePixelRatio()))).toImage()))
                self.selector.cancelled.connect(self.showNormal)
                self.selector.show()
                self.selector.activateWindow()
                return
            if target is not None:
                ratio = pixmap.devicePixelRatio()
                target = QRect(round(target.x() * ratio), round(target.y() * ratio), round(target.width() * ratio), round(target.height() * ratio))
                pixmap = pixmap.copy(target.intersected(pixmap.rect()))
            self.finish_capture(pixmap.toImage())
        except Exception as exc:
            self.showNormal()
            QMessageBox.warning(self, 'Erro de captura', str(exc))

    def finish_capture(self, image):
        self.showNormal()
        try:
            self.history.save(image)
            self.canvas.load(image)
            self.refresh()
        except OSError as exc:
            QMessageBox.warning(self, 'Histórico', str(exc))

    def copy(self):
        if not self.canvas.image.isNull():
            QApplication.clipboard().setImage(self.canvas.image)
            self.statusBar().showMessage('Imagem copiada. Mantenha o aplicativo aberto para disponibilizar a área de transferência.')

    def save(self):
        if self.canvas.image.isNull():
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Salvar imagem', 'captura.png', 'PNG (*.png);;JPEG (*.jpg *.jpeg)')
        if path:
            if not Path(path).suffix:
                path += '.png'
            if not self.canvas.image.save(path):
                QMessageBox.warning(self, 'Salvar', 'Não foi possível salvar nesse caminho ou formato.')
            else:
                try:
                    self.history.save(self.canvas.image)
                    self.refresh()
                except OSError as exc:
                    QMessageBox.warning(self, 'Histórico', str(exc))


def main():
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        sys.exit('Este MVP requer uma sessão X11. Selecione Ubuntu on Xorg no login.')
    app = QApplication(sys.argv)
    app.setApplicationName('ScreenDepresso')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
