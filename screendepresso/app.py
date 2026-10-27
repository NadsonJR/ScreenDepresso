import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal, QObject
from PySide6.QtGui import QKeySequence, QAction, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QListWidget, QFileDialog, QMessageBox,
    QInputDialog, QScrollArea, QSystemTrayIcon, QMenu, QStyle, QSpinBox)

from .editor import Canvas
from .settings import Settings, SettingsDialog
from .hotkeys import Hotkeys


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
        from . import __version__
        from .update_dialog import UpdateDialog
        self.settings = Settings()
        self.setWindowTitle('ScreenDepresso')
        self.menuBar().addAction('Configurações…', lambda: SettingsDialog(self).exec())
        self.menuBar().addAction('Atualizações…', lambda: UpdateDialog(self).exec())
        self.menuBar().addAction('Sobre', lambda: QMessageBox.information(self, 'ScreenDepresso', f'ScreenDepresso {__version__}\nUbuntu / GNOME / X11'))
        self.resize(1100, 760)
        self.history = History(self.settings.directory)
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
        for name in ['selecionar', 'seta', 'texto', 'retângulo', 'desfoque', 'recorte']:
            button = QPushButton(name.capitalize())
            button.clicked.connect(lambda checked=False, t=name: setattr(self.canvas, 'tool', t))
            tools.addWidget(button)
        for label, callback in [('Desfazer', self.canvas.undo), ('Refazer', self.canvas.redo), ('Copiar', self.copy), ('Salvar', self.save)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            tools.addWidget(button)
        layout.addLayout(tools)
        blur_row = QHBoxLayout()
        blur_row.addWidget(QLabel('Desfoque fora da seleção:'))
        self.blur_strength = QSpinBox()
        self.blur_strength.setRange(1, 100)
        self.blur_strength.setValue(14)
        self.blur_strength.valueChanged.connect(self.canvas.set_blur_radius)
        self.canvas.blur_selected.connect(self.display_blur_radius)
        blur_row.addWidget(self.blur_strength)
        blur_row.addWidget(QLabel('Selecionar: mover e arrastar alças • Texto: duplo clique para editar'))
        layout.addLayout(blur_row)
        for label, shortcut, callback in [('Desfazer', 'Ctrl+Z', self.canvas.undo), ('Refazer', 'Ctrl+Y', self.canvas.redo), ('Excluir objeto', 'Delete', self.canvas.delete_selected)]:
            action = QAction(label, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.addAction(action)
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
        self.hotkeys = Hotkeys()
        self.hotkeys.capture.connect(self.capture)
        self.hotkeys.failed.connect(lambda message: self.statusBar().showMessage(message))
        QApplication.instance().aboutToQuit.connect(self.hotkeys.stop)
        self.show_shortcuts()
        if os.environ.get('DISPLAY') and '--smoke-test' not in sys.argv:
            try:
                self.hotkeys.configure(self.settings.hotkeys)
            except Exception as exc:
                self.statusBar().showMessage(f'Atalhos indisponíveis: {exc}')
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

    def display_blur_radius(self, radius):
        self.blur_strength.blockSignals(True)
        self.blur_strength.setValue(radius)
        self.blur_strength.blockSignals(False)

    def show_shortcuts(self):
        self.statusBar().showMessage(' • '.join(f'{value}: {mode}' for mode, value in self.settings.hotkeys.items()))

    def apply_settings(self, directory, hotkeys):
        old = self.settings.hotkeys.copy()
        changed = hotkeys != old
        if changed and os.environ.get('DISPLAY'):
            self.hotkeys.configure(hotkeys)
        try:
            self.settings.save(directory, hotkeys)
        except OSError:
            if changed and os.environ.get('DISPLAY'):
                self.hotkeys.configure(old)
            raise
        self.history = History(directory)
        self.refresh()
        self.show_shortcuts()

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
        path, _ = QFileDialog.getSaveFileName(self, 'Salvar imagem', str(self.history.directory / 'captura.png'), 'PNG (*.png);;JPEG (*.jpg *.jpeg)')
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
    if '--version' in sys.argv:
        from . import __version__
        print(__version__)
        return
    if '--smoke-test' in sys.argv:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    if '--smoke-test' not in sys.argv and os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        sys.exit('Este MVP requer uma sessão X11. Selecione Ubuntu on Xorg no login.')
    app = QApplication(sys.argv)
    app.setApplicationName('ScreenDepresso')
    window = MainWindow()
    window.show()
    if '--smoke-test' in sys.argv:
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.fill(QColor('red'))
        window.finish_capture(image)
        window.copy()
        if QApplication.clipboard().image() != image or window.list.count() < 1:
            raise RuntimeError('Smoke test failed')
        print('Interface, histórico e clipboard: OK (offscreen)', flush=True)
        QTimer.singleShot(100, app.quit)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
