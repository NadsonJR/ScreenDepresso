from .i18n import tr, mode_label, set_language, translate_tree
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal, QObject, QSize, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QIcon, QKeySequence, QActionGroup, QAction, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QFileDialog, QMessageBox, QInputDialog, QScrollArea, QSystemTrayIcon, QMenu, QSpinBox, QSlider, QToolBar, QDockWidget, QColorDialog, QSizePolicy, QToolButton, QWidgetAction
from .appearance import STYLE, dark_palette, icon as toolbar_icon
from .editor import Canvas
from .settings import Settings, SettingsDialog
from .hotkeys import Hotkeys
from .platform_support import capture_desktop, data_directory, global_hotkeys_available

class History:

    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._last_saved_time = None

    def save(self, image):
        payload = QByteArray()
        buffer = QBuffer(payload)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, 'PNG'):
            raise OSError(tr('Could not save the capture.'))
        buffer.close()
        stamp = datetime.now()
        if self._last_saved_time is not None:
            stamp = max(stamp, self._last_saved_time+timedelta(microseconds=1))
        while True:
            path = self.directory/(stamp.strftime('%Y%m%d-%H%M%S-%f')+'.png')
            try:
                stream = path.open('xb')
            except FileExistsError:
                stamp += timedelta(microseconds=1)
                continue
            try:
                with stream:
                    stream.write(bytes(payload))
            except OSError:
                path.unlink(missing_ok=True)
                raise
            self._last_saved_time = stamp
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
    if sys.platform == 'win32':
        from .windows_backend import windows as list_windows
        return list_windows()
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
        self.settings = Settings()
        set_language(self.settings.language)
        self.setWindowTitle('ScreenDepresso')
        self._quitting = False
        self.setPalette(dark_palette())
        self.setStyleSheet(STYLE)
        self.resize(1280, 840)
        self.history = History(self.settings.directory)
        self.canvas = Canvas()
        self.tool_actions = {}
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        ribbon = QToolBar(tr('Actions'), self)
        ribbon.setObjectName('ribbon')
        ribbon.setMovable(False)
        ribbon.setIconSize(QSize(42, 42))
        ribbon.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, ribbon)

        def add_action(bar, title, symbol, callback, color='#3878a8', shortcut=None):
            action = QAction(toolbar_icon(symbol, color), title, self)
            action.triggered.connect(callback)
            action.setProperty('hoverShortcut', shortcut or '')
            action.setToolTip(title + (f' ({shortcut})' if shortcut else ''))
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            bar.addAction(action)
            return action
        add_action(ribbon, tr('Save'), 'save', self.save, '#54894d', 'Ctrl+S')
        add_action(ribbon, tr('Copy image'), 'copy', self.copy, '#54894d', 'Ctrl+C')
        add_action(ribbon, tr('Paste image'), '+', self.paste, '#54894d', 'Ctrl+V')
        ribbon.addSeparator()
        add_action(ribbon, tr('Undo'), '↶', self.canvas.undo, '#b87b2d', 'Ctrl+Z')
        add_action(ribbon, tr('Redo'), '↷', self.canvas.redo, '#b87b2d', 'Ctrl+Y')
        add_action(ribbon, tr('Crop'), 'crop', lambda: self.choose_tool('recorte'))
        ribbon.addSeparator()
        add_action(ribbon, tr('Full screen'), '▣', lambda: self.capture('tela'))
        add_action(ribbon, tr('Window'), '▢', lambda: self.capture('janela'))
        add_action(ribbon, tr('Region'), '⌗', lambda: self.capture('região'))
        ribbon.addSeparator()
        add_action(ribbon, tr('Settings'), '⚙', lambda: SettingsDialog(self).exec())
        tools = QToolBar(tr('Tools'), self)
        tools.setObjectName('tools')
        tools.setMovable(False)
        tools.setIconSize(QSize(40, 40))
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tools)
        for name, label, symbol in [('selecionar', tr('Select / move'), 'hand'), ('seta', tr('Arrow'), 'arrow'), ('retângulo', tr('Rectangle'), 'rectangle'), ('texto', tr('Text — drag and type'), 'A'), ('numero', tr('Numbered markers'), '1'), ('desfoque', tr('Blur outside selection'), 'blur')]:
            action = add_action(tools, label, symbol, lambda checked=False, t=name: self.choose_tool(t))
            action.setCheckable(True)
            self.tool_group.addAction(action)
            self.tool_actions[name] = action
        self.color_actions = {}
        for name, label, callback in [('numero', 'Marker color…', self.choose_marker_color), ('retângulo', 'Rectangle color…', self.choose_rectangle_color), ('seta', 'Arrow color…', self.choose_arrow_color)]:
            button = tools.widgetForAction(self.tool_actions[name])
            menu = QMenu(button)
            menu.setToolTipsVisible(True)
            color_action = menu.addAction(tr(label), callback)
            color_action.setToolTip(tr(label))
            self.color_actions[name] = color_action
            button.setMenu(menu)
            button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.canvas.marker_color_changed.connect(self.display_marker_color)
        self.canvas.rectangle_color_changed.connect(self.display_rectangle_color)
        self.canvas.arrow_color_changed.connect(self.display_arrow_color)
        self.display_marker_color(self.canvas.marker_color)
        self.display_rectangle_color(self.canvas.rectangle_color)
        self.display_arrow_color(self.canvas.arrow_color)
        self.tool_actions[self.canvas.tool].setChecked(True)
        self.canvas.tool_changed.connect(self.sync_tool)
        delete_action = QAction(tr('Delete object (Delete)'), self)
        delete_action.setShortcut(QKeySequence('Delete'))
        delete_action.triggered.connect(self.canvas.delete_selected)
        self.addAction(delete_action)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        options = QWidget()
        options.setObjectName('toolOptions')
        options.setStyleSheet('QWidget#toolOptions { background: #292e38; }')
        options_row = QHBoxLayout(options)
        self.tool_hint = QLabel(tr('Arrow • Drag on the image to draw'))
        self.tool_hint.setWordWrap(True)
        self.tool_hint.setMinimumWidth(0)
        self.tool_hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        options_row.addWidget(self.tool_hint, 1)
        self.blur_menu = QMenu(tools)
        self.blur_menu.setObjectName('blurMenu')
        blur_panel = QWidget()
        blur_layout = QVBoxLayout(blur_panel)
        blur_label = QLabel(tr('Blur strength:'))
        blur_label.setToolTip(tr('Select a blur effect to change its strength.'))
        blur_layout.addWidget(blur_label)
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(1, 100)
        self.blur_slider.setValue(14)
        self.blur_slider.setFixedWidth(150)
        self.blur_slider.setToolTip(tr('Select a blur effect to change its strength.'))
        blur_layout.addWidget(self.blur_slider)
        self.blur_strength = QSpinBox()
        self.blur_strength.setToolTip(tr('Blur strength (1–100)'))
        self.blur_strength.setRange(1, 100)
        self.blur_strength.setValue(14)
        self.blur_strength.valueChanged.connect(self.canvas.set_blur_radius)
        self.blur_slider.valueChanged.connect(self.blur_strength.setValue)
        self.blur_strength.valueChanged.connect(self.blur_slider.setValue)
        self.canvas.blur_selected.connect(self.display_blur_radius)
        blur_layout.addWidget(self.blur_strength)
        blur_action = QWidgetAction(self.blur_menu)
        blur_action.setDefaultWidget(blur_panel)
        self.blur_menu.addAction(blur_action)
        blur_button = tools.widgetForAction(self.tool_actions['desfoque'])
        blur_button.setMenu(self.blur_menu)
        blur_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        layout.addWidget(options)
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll, 1)
        self.setCentralWidget(container)
        self.list = QListWidget()
        self.list.setToolTip(tr('Click a capture to open it in the editor.'))
        self.list.itemClicked.connect(self.open_history)
        self.history_dock = QDockWidget(tr('Capture history'), self)
        self.history_dock.setObjectName('history')
        self.history_dock.setWidget(self.list)
        self.history_dock.setMinimumWidth(230)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        self.history_dock.hide()
        history_action = self.history_dock.toggleViewAction()
        history_action.setIcon(toolbar_icon('☷'))
        history_action.setText(tr('History'))
        history_action.setToolTip(tr('History'))
        ribbon.addAction(history_action)
        self.dimensions = QLabel(tr('No image • Capture a screen to get started'))
        self.statusBar().addPermanentWidget(self.dimensions)
        from . import __version__
        self.version_label = QLabel(f'v{__version__}')
        self.version_label.setToolTip(tr('Application version'))
        self.statusBar().addPermanentWidget(self.version_label)
        self.canvas.changed.connect(self.update_dimensions)
        self.refresh()
        self.hotkeys = Hotkeys()
        self.hotkeys.capture.connect(self.capture)
        self.hotkeys.failed.connect(lambda message: self.statusBar().showMessage(message))
        QApplication.instance().aboutToQuit.connect(self.hotkeys.stop)
        self.show_shortcuts()
        if global_hotkeys_available() and '--smoke-test' not in sys.argv:
            try:
                self.hotkeys.configure(self.settings.hotkeys)
            except Exception as exc:
                self.statusBar().showMessage(f"{tr('Hotkeys unavailable: ')}{exc}")
        icon = QIcon.fromTheme('screendepresso', toolbar_icon('copy', '#c6384c'))
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)
        menu.addAction(tr('Open'), self.open_editor)
        for mode in ['tela', 'janela', 'região']:
            menu.addAction(tr({'tela': 'Capture full screen', 'janela': 'Capture window', 'região': 'Capture region'}[mode]), lambda m=mode: self.capture(m))
        menu.addSeparator()
        menu.addAction(tr('Settings'), lambda: SettingsDialog(self).exec())
        menu.addAction(tr('Check for updates'), self.check_updates)
        menu.addAction(tr('About'), self.show_about)
        menu.addSeparator()
        menu.addAction(tr('Quit'), self.request_quit)
        menu.setToolTipsVisible(True)
        for action in menu.actions():
            action.setToolTip(action.text())
        self.tray.setToolTip('ScreenDepresso')
        self.tray.activated.connect(self.tray_activated)
        self.tray.setContextMenu(menu)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def open_editor(self):
        if self._quitting:
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_editor()

    def check_updates(self):
        from .update_dialog import UpdateDialog
        dialog = UpdateDialog(self)
        dialog.quit_requested.connect(self.request_quit)
        dialog.perform()
        dialog.exec()

    def show_about(self):
        from . import __version__
        QMessageBox.information(self, 'ScreenDepresso', f'ScreenDepresso {__version__}\nWindows / Linux X11')

    def ask_close_action(self):
        from .close_dialog import CloseDialog
        dialog = CloseDialog(self, QSystemTrayIcon.isSystemTrayAvailable())
        dialog.exec()
        return dialog.choice

    def minimize_to_background(self):
        self.canvas.finish_text()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
            self.hide()
        else:
            self.showMinimized()

    def stop_background_services(self):
        self.hotkeys.stop()
        self.tray.hide()
        if hasattr(self, 'selector'):
            self.selector.close()

    def _quit_application(self):
        QApplication.instance().quit()

    def request_quit(self):
        self._quitting = True
        self.canvas.finish_text()
        self.stop_background_services()
        self.hide()
        self._quit_application()

    def closeEvent(self, event):
        if self._quitting:
            event.accept()
            return
        choice = self.ask_close_action()
        if choice == 'minimize':
            event.ignore()
            self.minimize_to_background()
        elif choice == 'quit':
            self.request_quit()
            event.accept()
        else:
            event.ignore()

    def choose_tool(self, name):
        self.canvas.tool = name

    def sync_tool(self, name):
        if name in self.tool_actions:
            self.tool_actions[name].setChecked(True)
        else:
            self.tool_group.setExclusive(False)
            for action in self.tool_actions.values():
                action.setChecked(False)
            self.tool_group.setExclusive(True)
        hints = {'selecionar': tr('Select • Drag to move; use handles to resize'), 'texto': tr('Text • Drag a box and type; Ctrl+Enter confirms; Esc cancels'), 'seta': tr('Arrow • Drag on the image to draw'), 'retângulo': tr('Rectangle • Drag on the image to draw'), 'recorte': tr('Crop • Drag the area you want to keep'), 'desfoque': tr('Blur • Drag the area you want to keep sharp'), 'numero': tr('Numbers • Click for the next number; drag from the circle to its target')}
        self.tool_hint.setText(hints[name])
        self.tool_hint.setToolTip(hints[name])

    def choose_arrow_color(self):
        obj = self.canvas.objects[self.canvas.selected] if self.canvas.selected is not None else None
        current = obj.get('color', '#ef233c') if obj is not None and obj['kind'] == 'seta' else self.canvas.arrow_color
        color = QColorDialog.getColor(QColor(current), self, tr('Arrow color'), QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_arrow_color(color)

    def display_arrow_color(self, color):
        icon = toolbar_icon('arrow', color)
        self.tool_actions['seta'].setIcon(icon)
        self.color_actions['seta'].setIcon(icon)

    def choose_rectangle_color(self):
        obj = self.canvas.objects[self.canvas.selected] if self.canvas.selected is not None else None
        current = obj.get('color', '#ef233c') if obj is not None and obj['kind'] == 'retângulo' else self.canvas.rectangle_color
        color = QColorDialog.getColor(QColor(current), self, tr('Rectangle color'), QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_rectangle_color(color)

    def display_rectangle_color(self, color):
        icon = toolbar_icon('rectangle', color)
        self.tool_actions['retângulo'].setIcon(icon)
        self.color_actions['retângulo'].setIcon(icon)

    def choose_marker_color(self):
        color = QColorDialog.getColor(QColor(self.canvas.marker_color), self, tr('Marker color'), QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_marker_color(color)

    def display_marker_color(self, color):
        icon = toolbar_icon('1', color)
        self.tool_actions['numero'].setIcon(icon)
        self.color_actions['numero'].setIcon(icon)

    def update_dimensions(self):
        self.dimensions.setText(f'{self.canvas.base.width()} × {self.canvas.base.height()} px • 100%')

    def display_blur_radius(self, radius):
        self.blur_strength.blockSignals(True)
        self.blur_strength.setValue(radius)
        self.blur_strength.blockSignals(False)
        self.blur_slider.blockSignals(True)
        self.blur_slider.setValue(radius)
        self.blur_slider.blockSignals(False)

    def show_shortcuts(self):
        self.statusBar().showMessage(' • '.join((f'{value}: {mode_label(mode)}' for mode, value in self.settings.hotkeys.items())))

    def apply_settings(self, directory, hotkeys, language=None):
        old = self.settings.hotkeys.copy()
        changed = hotkeys != old
        if changed and global_hotkeys_available():
            self.hotkeys.configure(hotkeys)
        try:
            self.settings.save(directory, hotkeys, language)
        except OSError:
            if changed and global_hotkeys_available():
                self.hotkeys.configure(old)
            raise
        set_language(self.settings.language)
        self.sync_tool(self.canvas.tool)
        self.history = History(directory)
        self.refresh()
        self.show_shortcuts()

    def refresh(self):
        self.list.clear()
        for path in self.history.entries():
            self.list.addItem(path.name)

    def open_history(self, item):
        self.canvas.load(QImage(str(self.history.directory / item.text())))
        self.update_dimensions()

    def capture(self, mode):
        target = None
        if mode == 'janela':
            try:
                choices = windows()
                if not choices:
                    raise RuntimeError(tr('No windows available.'))
                labels = [f'{i + 1}. {title}' for i, (title, _) in enumerate(choices)]
                chosen, ok = QInputDialog.getItem(self, tr('Capture window'), tr('Visible window (unobstructed):'), labels, 0, False)
                if not ok:
                    return
                target = choices[labels.index(chosen)][1]
            except Exception as exc:
                QMessageBox.warning(self, tr('Window capture'), str(exc))
                return
        self.hide()
        QTimer.singleShot(350, lambda: self.take_capture(mode, target))

    def take_capture(self, mode, target):
        try:
            pixmap, geometry = capture_desktop()
            if pixmap.isNull():
                raise RuntimeError(tr('Capture unavailable. Run in an X11 session.'))
            if mode == 'região':
                self.selector = Selector(pixmap, geometry)
                self.selector.selected.connect(lambda rect: self.finish_capture(pixmap.copy(QRect(round(rect.x() * pixmap.devicePixelRatio()), round(rect.y() * pixmap.devicePixelRatio()), round(rect.width() * pixmap.devicePixelRatio()), round(rect.height() * pixmap.devicePixelRatio()))).toImage()))
                self.selector.cancelled.connect(self.open_editor)
                self.selector.show()
                self.selector.activateWindow()
                return
            if target is not None:
                ratio = pixmap.devicePixelRatio()
                target = QRect(round((target.x()-geometry.x()) * ratio), round((target.y()-geometry.y()) * ratio), round(target.width() * ratio), round(target.height() * ratio))
                pixmap = pixmap.copy(target.intersected(pixmap.rect()))
            self.finish_capture(pixmap.toImage())
        except Exception as exc:
            self.open_editor()
            QMessageBox.warning(self, tr('Capture error'), str(exc))

    def finish_capture(self, image):
        self.open_editor()
        try:
            self.history.save(image)
            self.canvas.load(image)
            self.update_dimensions()
            self.refresh()
        except OSError as exc:
            QMessageBox.warning(self, tr('History'), str(exc))

    def paste(self):
        if not self.canvas.paste_image():
            self.statusBar().showMessage(tr('Clipboard does not contain an image.'))
        self.update_dimensions()

    def copy(self):
        self.canvas.finish_text()
        if not self.canvas.image.isNull():
            QApplication.clipboard().setImage(self.canvas.image)
            self.statusBar().showMessage(tr('Image copied. Keep the application open to provide clipboard data.'))

    def save(self):
        self.canvas.finish_text()
        if self.canvas.image.isNull():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr('Save image'), str(self.history.directory / 'captura.png'), 'PNG (*.png);;JPEG (*.jpg *.jpeg)')
        if path:
            if not Path(path).suffix:
                path += '.png'
            if not self.canvas.image.save(path):
                QMessageBox.warning(self, tr('Save'), tr('Could not save to this path or format.'))
            else:
                try:
                    self.history.save(self.canvas.image)
                    self.refresh()
                except OSError as exc:
                    QMessageBox.warning(self, tr('History'), str(exc))

def main():
    if '--version' in sys.argv:
        from . import __version__
        print(__version__)
        return
    if '--smoke-test' in sys.argv:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    if sys.platform != 'win32' and '--smoke-test' not in sys.argv and os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        sys.exit(tr('This MVP requires an X11 session. Select Ubuntu on Xorg at login.'))
    app = QApplication(sys.argv)
    app.setApplicationName('screendepresso')
    app.setApplicationDisplayName('ScreenDepresso')
    app.setDesktopFileName('screendepresso')
    app.setQuitOnLastWindowClosed(False)
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
        QTimer.singleShot(100, window.request_quit)
    sys.exit(app.exec())
if __name__ == '__main__':
    main()
