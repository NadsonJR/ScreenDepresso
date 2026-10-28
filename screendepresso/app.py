from .i18n import tr, mode_label, set_language, translate_tree
import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QRect, QTimer, QSize
from PySide6.QtGui import QIcon, QKeySequence, QActionGroup, QAction, QColor, QImage, QPixmap, QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QSpinBox, QSlider, QToolBar, QDockWidget, QColorDialog, QSizePolicy, QToolButton, QWidgetAction, QFontComboBox, QFormLayout, QCheckBox
from .appearance import STYLE, dark_palette, icon as toolbar_icon
from .editor import Canvas
from .documents import CaptureTabs
from .annotations import ARROW_STYLES, BUBBLE_STYLES
from .markers import MARKER_STYLES
from .settings import Settings, SettingsDialog
from .hotkeys import Hotkeys
from .platform_support import capture_desktop, crop_desktop, global_hotkeys_available
from .capture_ui import Selector, WindowPicker
from .update_panel import UpdatePanel
from .workspace import WorkspaceStore as History, WorkspaceView, read_image

def windows():
    if sys.platform == 'darwin':
        from .macos_backend import windows as list_windows
        return list_windows()
    if sys.platform == 'win32':
        from .windows_backend import windows as list_windows
        return list_windows(with_ids=True)
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
                pid = window.get_full_property(connection.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
                if pid is not None and len(pid.value) and int(pid.value[0]) == os.getpid():
                    continue
                if window.get_attributes().map_state != X.IsViewable:
                    continue
                utf8 = window.get_full_property(connection.intern_atom('_NET_WM_NAME'), X.AnyPropertyType)
                if utf8 is not None:
                    title = bytes(utf8.value).decode('utf-8', errors='replace')
                elif isinstance(title, bytes):
                    title = title.decode(errors='replace')
                if title and title != 'ScreenDepresso':
                    geometry = window.get_geometry()
                    position = root.translate_coords(window, 0, 0)
                    result.append((title, QRect(position.x, position.y, geometry.width, geometry.height), int(wid)))
            except Exception:
                continue
        return result
    finally:
        connection.close()

def activate_window(wid):
    if sys.platform == 'darwin':
        from .macos_backend import activate_window as activate
        return activate(wid)
    if sys.platform == 'win32':
        from .windows_backend import activate_window as activate
        return activate(wid)
    from Xlib import X, display, protocol
    connection = display.Display()
    try:
        root = connection.screen().root
        window = connection.create_resource_object('window', wid)
        event = protocol.event.ClientMessage(window=window, client_type=connection.intern_atom('_NET_ACTIVE_WINDOW'),
                                             data=(32, [2, X.CurrentTime, 0, 0, 0]))
        root.send_event(event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        window.configure(stack_mode=X.Above)
        connection.sync()
    finally:
        connection.close()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        set_language(self.settings.language)
        self.setWindowTitle('ScreenDepresso')
        self._quitting = False
        self._capture_pending = False
        self.setPalette(dark_palette())
        self.setStyleSheet(STYLE)
        self.resize(1280, 840)
        self.history = History(self.settings.directory, self.settings.workspace_limit)
        self.tabs = CaptureTabs(self)
        self._active_canvas = None
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
        add_action(ribbon, tr('Paste image'), 'paste', self.paste, '#54894d', 'Ctrl+V')
        ribbon.addSeparator()
        add_action(ribbon, tr('Undo'), '↶', lambda: self.canvas.undo(), '#b87b2d', 'Ctrl+Z')
        add_action(ribbon, tr('Redo'), '↷', lambda: self.canvas.redo(), '#b87b2d', 'Ctrl+Y')
        add_action(ribbon, tr('Crop'), 'crop', lambda: self.choose_tool('recorte'))
        ribbon.addSeparator()
        full_screen_action = add_action(ribbon, tr('Full screen'), '▣', lambda: self.capture('tela'))
        self.monitor_menu = QMenu(ribbon)
        self.monitor_menu.aboutToShow.connect(self.refresh_monitor_menu)
        full_screen_button = ribbon.widgetForAction(full_screen_action)
        full_screen_button.setMenu(self.monitor_menu)
        full_screen_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        add_action(ribbon, tr('Window'), '▢', lambda: self.capture('janela'))
        add_action(ribbon, tr('Region'), '⌗', lambda: self.capture('região'))
        ribbon.addSeparator()
        add_action(ribbon, tr('Settings'), '⚙', self.open_settings)
        tools = QToolBar(tr('Tools'), self)
        tools.setObjectName('tools')
        tools.setMovable(False)
        tools.setIconSize(QSize(40, 40))
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tools)
        for name, label, symbol in [('selecionar', tr('Select / move'), 'hand'), ('seta', tr('Arrow'), 'arrow'), ('retângulo', tr('Rectangle'), 'rectangle'), ('texto', tr('Text — drag and type'), 'A'), ('balao', tr('Speech balloon'), 'bubble:oval'), ('numero', tr('Numbered markers'), '1'), ('desfoque', tr('Blur outside selection'), 'blur')]:
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
        self.setup_bubble_menu(tools)
        self.setup_text_menu(tools)
        self.setup_arrow_menu(tools)
        self.setup_rectangle_menu(tools)
        self.setup_marker_menu(tools)
        self.display_marker_color(self.canvas.marker_color)
        self.display_rectangle_color(self.canvas.rectangle_color)
        self.display_arrow_color(self.canvas.arrow_color)
        self.tool_actions[self.canvas.tool].setChecked(True)
        delete_action = QAction(tr('Delete object (Delete)'), self)
        delete_action.setShortcut(QKeySequence('Delete'))
        delete_action.triggered.connect(lambda: self.canvas.delete_selected())
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
        self.blur_strength.valueChanged.connect(lambda value: self.canvas.set_blur_radius(value))
        self.blur_slider.valueChanged.connect(self.blur_strength.setValue)
        self.blur_strength.valueChanged.connect(self.blur_slider.setValue)
        blur_layout.addWidget(self.blur_strength)
        blur_action = QWidgetAction(self.blur_menu)
        blur_action.setDefaultWidget(blur_panel)
        self.blur_menu.addAction(blur_action)
        self.blur_menu.addSeparator()
        self.blur_modes = {}
        blur_modes_group = QActionGroup(self.blur_menu)
        blur_modes_group.setExclusive(True)
        for mode, label in [('shared', 'Shared blur layer'), ('sequential', 'Sequential blur (legacy)')]:
            action = self.blur_menu.addAction(tr(label))
            action.setCheckable(True)
            action.setToolTip(tr(label))
            action.triggered.connect(lambda checked=False, m=mode: self.canvas.set_blur_mode(m))
            blur_modes_group.addAction(action)
            self.blur_modes[mode] = action
        blur_button = tools.widgetForAction(self.tool_actions['desfoque'])
        blur_button.setMenu(self.blur_menu)
        blur_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        layout.addWidget(options)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(container)
        self.workspace = WorkspaceView(self.history, self)
        self.list = self.workspace.grid
        self.list.itemDoubleClicked.connect(self.open_history)
        self.history_dock = QDockWidget(tr('Workspace'), self)
        self.history_dock.setObjectName('workspace')
        self.history_dock.setWidget(self.workspace)
        self.history_dock.setMinimumWidth(320)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        history_action = self.history_dock.toggleViewAction()
        history_action.setIcon(toolbar_icon('☷'))
        history_action.setText(tr('Workspace'))
        history_action.setToolTip(tr('Workspace'))
        ribbon.addAction(history_action)
        self.dimensions = QLabel(tr('No image • Capture a screen to get started'))
        zoom_panel = QWidget()
        zoom_layout = QHBoxLayout(zoom_panel)
        zoom_layout.setContentsMargins(0, 0, 8, 0)
        zoom_layout.addWidget(QLabel(tr('Zoom')))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.setToolTip(tr('Zoom the active capture (10–400%)'))
        self.zoom_slider.valueChanged.connect(self.change_zoom)
        zoom_layout.addWidget(self.zoom_slider)
        self.zoom_label = QLabel('100%')
        self.zoom_label.setMinimumWidth(45)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addStretch()
        self.statusBar().addPermanentWidget(zoom_panel, 1)
        self.statusBar().addPermanentWidget(self.dimensions)
        from . import __version__
        self.version_label = QLabel(f'v{__version__}')
        self.version_label.setToolTip(tr('Application version'))
        self.statusBar().addPermanentWidget(self.version_label)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.close_requested.connect(self.close_tabs)
        for label, shortcut, callback in [
            ('Close tab', 'Ctrl+W', lambda: self.close_tab(self.tabs.currentIndex())),
            ('Next tab', 'Ctrl+Tab', lambda: self.tabs.cycle(1)),
            ('Previous tab', 'Ctrl+Shift+Tab', lambda: self.tabs.cycle(-1)),
        ]:
            action = QAction(tr(label), self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.addAction(action)
        self.tab_changed(self.tabs.currentIndex())
        self.refresh()
        self._settings_dialog = None
        self.update_panel = UpdatePanel(self)
        self.update_panel.hide()
        self.update_panel.quit_requested.connect(self.request_quit)
        QApplication.instance().aboutToQuit.connect(self.update_panel.shutdown)
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
        menu.addAction(tr('Settings'), self.open_settings)
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

    @property
    def canvas(self):
        return self.tabs.canvas

    @property
    def scroll(self):
        return self.tabs.currentWidget()

    def tab_changed(self, index):
        if index < 0:
            return
        if self._active_canvas is not None and self._active_canvas is not self.canvas:
            self._active_canvas.finish_text()
        canvas = self.canvas
        if not canvas.property('windowSignalsConnected'):
            for signal, callback in [
                (canvas.changed, self.update_dimensions),
                (canvas.tool_changed, self.sync_tool),
                (canvas.marker_color_changed, self.display_marker_color),
                (canvas.rectangle_color_changed, self.display_rectangle_color),
                (canvas.arrow_color_changed, self.display_arrow_color),
                (canvas.blur_selected, self.display_blur_radius),
                (canvas.bubble_changed, self.display_bubble_format),
                (canvas.text_format_changed, self.display_text_format),
                (canvas.zoom_changed, self.display_zoom),
                (canvas.arrow_style_changed, self.display_arrow_style),
                (canvas.blur_settings_changed, self.display_blur_options),
                (canvas.rectangle_format_changed, self.display_rectangle_format),
                (canvas.marker_style_changed, self.display_marker_style),
                (canvas.drop_failed, lambda message: self.statusBar().showMessage(message, 4000)),
            ]:
                signal.connect(lambda *args, c=canvas, f=callback: f(*args) if self.tabs.currentIndex() >= 0 and self.canvas is c else None)
            canvas.setProperty('windowSignalsConnected', True)
        self._active_canvas = canvas
        self.sync_tool(canvas.tool)
        self.display_marker_color(canvas.marker_color)
        self.display_rectangle_color(canvas.rectangle_color)
        self.display_arrow_color(canvas.arrow_color)
        selected = canvas.objects[canvas.selected] if canvas.selected is not None else None
        self.display_blur_radius(selected['radius'] if selected is not None and selected['kind'] == 'desfoque' else canvas.blur_radius)
        self.display_bubble_format()
        self.display_text_format()
        self.display_zoom(round(canvas.zoom*100))
        self.display_arrow_style()
        self.display_blur_options()
        self.display_rectangle_format()
        self.display_marker_style()
        self.update_dimensions()
        self.tabs.retranslate()

    def close_tab(self, index):
        if index < 0 or index >= self.tabs.count():
            return False
        self.tabs.setCurrentIndex(index)
        self.canvas.finish_text()
        if self.tabs.is_dirty(self.tabs.currentWidget()):
            answer = QMessageBox.question(
                self, tr('Close tab'), tr('Save changes before closing this tab?'),
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save)
            if answer == QMessageBox.StandardButton.Cancel:
                return False
            if answer == QMessageBox.StandardButton.Save and not self.save():
                return False
        # Clear the reference before Qt destroys the closed canvas.
        self._active_canvas = None
        self.tabs.remove_document(index)
        return True

    def close_tabs(self, operation, page):
        if self.tabs.indexOf(page) < 0 or operation not in ('all', 'this', 'others'):
            return
        pages = [self.tabs.widget(i) for i in range(self.tabs.count())]
        if operation == 'this':
            pages = [page]
        elif operation == 'others':
            pages.remove(page)
        for target in pages:
            if not self.close_tab(self.tabs.indexOf(target)):
                break
        else:
            if operation == 'others':
                self.tabs.setCurrentWidget(page)

    def activate_existing_instance(self):
        self.open_editor()
        dialog = QApplication.activeModalWidget()
        if dialog is not None:
            dialog.showNormal()
            dialog.raise_()
            dialog.activateWindow()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_editor()

    def open_settings(self, updates=False):
        dialog = self._settings_dialog
        if dialog is None:
            dialog = SettingsDialog(self)
            self._settings_dialog = dialog
            dialog.finished.connect(lambda result, d=dialog: self.settings_closed(d))
        if updates:
            dialog.show_updates()
        dialog.showNormal()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def settings_closed(self, dialog):
        if self._settings_dialog is dialog:
            self._settings_dialog = None
        dialog.deleteLater()

    def check_updates(self):
        self.open_settings(updates=True)
        self.update_panel.check_for_updates()

    def show_about(self):
        from . import __version__
        QMessageBox.information(self, 'ScreenDepresso', f'ScreenDepresso {__version__}\nWindows / Linux X11 / macOS')

    def ask_close_action(self):
        from .close_dialog import CloseDialog
        dialog = CloseDialog(self, QSystemTrayIcon.isSystemTrayAvailable())
        dialog.exec()
        return dialog.choice

    def minimize_to_background(self):
        self.canvas.finish_text()
        if self._settings_dialog is not None:
            self._settings_dialog.hide()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
            self.hide()
        else:
            self.showMinimized()

    def stop_background_services(self):
        self.hotkeys.stop()
        self.workspace.stop()
        self.tray.hide()
        if hasattr(self, 'selector'):
            self.selector.close()

    def _quit_application(self):
        QApplication.instance().quit()

    def request_quit(self):
        self._quitting = True
        self.canvas.finish_text()
        if self._settings_dialog is not None:
            self._settings_dialog.reject()
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

    def setup_bubble_menu(self, tools):
        button = tools.widgetForAction(self.tool_actions['balao'])
        self.bubble_menu = QMenu(button)
        self.bubble_menu.setToolTipsVisible(True)
        self.bubble_styles = {}
        group = QActionGroup(self.bubble_menu)
        group.setExclusive(True)
        for style, label in BUBBLE_STYLES.items():
            action = self.bubble_menu.addAction(toolbar_icon('bubble:'+style), tr(label))
            action.setCheckable(True)
            action.setToolTip(tr(label))
            action.triggered.connect(lambda checked=False, s=style: self.choose_bubble_style(s))
            group.addAction(action)
            self.bubble_styles[style] = action
        self.bubble_menu.addSeparator()
        for key, label in [('fill', 'Balloon fill color…'), ('outline', 'Balloon outline color…')]:
            action = self.bubble_menu.addAction(tr(label), lambda k=key: self.choose_bubble_color(k))
            action.setToolTip(tr(label))
        button.setMenu(self.bubble_menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

    def setup_rectangle_menu(self, tools):
        menu = tools.widgetForAction(self.tool_actions['retângulo']).menu()
        menu.addSeparator()
        panel = QWidget()
        form = QFormLayout(panel)
        self.rectangle_width = QSpinBox()
        self.rectangle_width.setRange(1, 40)
        self.rectangle_width.setSuffix(' px')
        self.rectangle_width.setMinimumWidth(110)
        self.rectangle_width.setKeyboardTracking(False)
        self.rectangle_width.setToolTip(tr('Border thickness'))
        self.rectangle_width.valueChanged.connect(lambda width: self.canvas.set_rectangle_format(width=width))
        form.addRow(tr('Border thickness'), self.rectangle_width)
        self.rectangle_rounded = QCheckBox(tr('Rounded corners'))
        self.rectangle_rounded.setToolTip(tr('Rounded corners'))
        self.rectangle_rounded.toggled.connect(lambda rounded: self.canvas.set_rectangle_format(rounded=rounded))
        form.addRow(self.rectangle_rounded)
        self.rectangle_radius = QSpinBox()
        self.rectangle_radius.setRange(1, 100)
        self.rectangle_radius.setSuffix(' px')
        self.rectangle_radius.setKeyboardTracking(False)
        self.rectangle_radius.setToolTip(tr('Corner radius'))
        self.rectangle_radius.valueChanged.connect(lambda radius: self.canvas.set_rectangle_format(radius=radius))
        form.addRow(tr('Corner radius'), self.rectangle_radius)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)

    def display_rectangle_format(self):
        canvas = self.canvas
        obj = canvas.objects[canvas.selected] if canvas.selected is not None else None
        values = obj if obj is not None and obj['kind'] == 'retângulo' else canvas.rectangle_format
        for widget, value in [(self.rectangle_width, values.get('width', 4)),
                              (self.rectangle_rounded, values.get('rounded', False)),
                              (self.rectangle_radius, values.get('radius', 12))]:
            widget.blockSignals(True)
            if widget is self.rectangle_rounded:
                widget.setChecked(value)
            else:
                widget.setValue(value)
            widget.blockSignals(False)
        self.rectangle_radius.setEnabled(values.get('rounded', False))
        self.display_rectangle_color(values.get('color', canvas.rectangle_color))

    def setup_marker_menu(self, tools):
        menu = tools.widgetForAction(self.tool_actions['numero']).menu()
        menu.addSeparator()
        self.marker_styles = {}
        group = QActionGroup(menu)
        group.setExclusive(True)
        for style, label in MARKER_STYLES.items():
            action = menu.addAction(toolbar_icon('marker:'+style), tr(label))
            action.setCheckable(True)
            action.setToolTip(tr(label))
            action.triggered.connect(lambda checked=False, s=style: self.choose_marker_style(s))
            group.addAction(action)
            self.marker_styles[style] = action

    def choose_marker_style(self, style):
        self.canvas.set_marker_style(style)
        if self.canvas.selected is None or self.canvas.objects[self.canvas.selected]['kind'] != 'numero':
            self.choose_tool('numero')

    def current_marker_style(self):
        canvas = self.canvas
        obj = canvas.objects[canvas.selected] if canvas.selected is not None else None
        return obj.get('style', 'circle') if obj is not None and obj['kind'] == 'numero' else canvas.marker_style

    def display_marker_style(self):
        self.marker_styles[self.current_marker_style()].setChecked(True)
        self.display_marker_color(self.canvas.marker_color)

    def current_bubble_format(self):
        canvas = self.canvas
        if canvas.selected is not None and canvas.objects[canvas.selected]['kind'] == 'balao':
            return canvas.objects[canvas.selected]
        return canvas.bubble_format

    def choose_bubble_style(self, style):
        self.canvas.set_bubble_format(style=style)
        if self.canvas.selected is None or self.canvas.objects[self.canvas.selected]['kind'] != 'balao':
            self.choose_tool('balao')

    def choose_bubble_color(self, key):
        color = QColorDialog.getColor(QColor(self.current_bubble_format()[key]), self,
                                      tr('Balloon fill color…' if key == 'fill' else 'Balloon outline color…'),
                                      QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_bubble_format(**{key: color})

    def display_bubble_format(self):
        values = self.current_bubble_format()
        self.bubble_styles[values['style']].setChecked(True)
        self.tool_actions['balao'].setIcon(toolbar_icon('bubble:'+values['style']))

    def setup_text_menu(self, tools):
        button = tools.widgetForAction(self.tool_actions['texto'])
        self.text_menu = QMenu(button)
        self.text_menu.setToolTipsVisible(True)
        panel = QWidget()
        form = QFormLayout(panel)
        self.text_font = QFontComboBox()
        self.text_font.setToolTip(tr('Font family'))
        self.text_font.setCurrentFont(QFont(self.canvas.text_format['font_family']))
        self.text_font.currentFontChanged.connect(lambda font: self.canvas.set_text_format(font_family=font.family()))
        form.addRow(tr('Font family'), self.text_font)
        self.text_size = QSpinBox()
        self.text_size.setRange(6, 200)
        self.text_size.setValue(24)
        self.text_size.setSuffix(' px')
        self.text_size.setMinimumWidth(115)
        self.text_size.setToolTip(tr('Font size'))
        self.text_size.valueChanged.connect(lambda size: self.canvas.set_text_format(font_size=size))
        form.addRow(tr('Font size'), self.text_size)
        action = QWidgetAction(self.text_menu)
        action.setDefaultWidget(panel)
        self.text_menu.addAction(action)
        self.text_color_action = self.text_menu.addAction(tr('Text color…'), self.choose_text_color)
        self.text_color_action.setToolTip(tr('Text color…'))
        button.setMenu(self.text_menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

    def choose_text_color(self):
        color = QColorDialog.getColor(QColor(self.canvas.current_text_format().get('color', '#ef233c')), self,
                                      tr('Text color…'), QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_text_format(color=color)

    def display_text_format(self):
        values = self.canvas.current_text_format()
        self.text_font.blockSignals(True)
        self.text_font.setCurrentFont(QFont(values.get('font_family', QFont().family())))
        self.text_font.blockSignals(False)
        self.text_size.blockSignals(True)
        self.text_size.setValue(values.get('font_size', 24))
        self.text_size.blockSignals(False)
        self.tool_actions['texto'].setIcon(toolbar_icon('A', values.get('color', '#ef233c')))
        self.text_color_action.setIcon(toolbar_icon('A', values.get('color', '#ef233c')))

    def change_zoom(self, percent):
        self.scroll.set_zoom(percent)

    def setup_arrow_menu(self, tools):
        menu = tools.widgetForAction(self.tool_actions['seta']).menu()
        menu.addSeparator()
        self.arrow_styles = {}
        group = QActionGroup(menu)
        group.setExclusive(True)
        for style, label in ARROW_STYLES.items():
            action = menu.addAction(toolbar_icon('arrow:'+style), tr(label))
            action.setCheckable(True)
            action.setToolTip(tr(label))
            action.triggered.connect(lambda checked=False, s=style: self.choose_arrow_style(s))
            group.addAction(action)
            self.arrow_styles[style] = action

    def choose_arrow_style(self, style):
        self.canvas.set_arrow_style(style)
        if self.canvas.selected is None or self.canvas.objects[self.canvas.selected]['kind'] != 'seta':
            self.choose_tool('seta')

    def display_arrow_style(self):
        obj = self.canvas.objects[self.canvas.selected] if self.canvas.selected is not None else None
        style = obj.get('style', 'classic') if obj is not None and obj['kind'] == 'seta' else self.canvas.arrow_style
        self.arrow_styles[style].setChecked(True)
        self.display_arrow_color(obj.get('color', '#ef233c') if obj is not None and obj['kind'] == 'seta' else self.canvas.arrow_color)

    def display_blur_options(self):
        self.blur_modes[self.canvas.blur_mode].setChecked(True)
        selected = self.canvas.objects[self.canvas.selected] if self.canvas.selected is not None else None
        self.display_blur_radius(selected['radius'] if selected is not None and selected['kind'] == 'desfoque' else self.canvas.blur_radius)

    def display_zoom(self, percent):
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(percent)
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f'{percent}%')

    def sync_tool(self, name):
        if name in self.tool_actions:
            self.tool_actions[name].setChecked(True)
        else:
            self.tool_group.setExclusive(False)
            for action in self.tool_actions.values():
                action.setChecked(False)
            self.tool_group.setExclusive(True)
        hints = {'selecionar': tr('Select • Drag to move; use handles to resize'), 'texto': tr('Text • Drag a box and type; Ctrl+Enter confirms; Esc cancels'), 'seta': tr('Arrow • Drag on the image to draw'), 'retângulo': tr('Rectangle • Drag on the image to draw'), 'recorte': tr('Crop • Drag the area you want to keep'), 'desfoque': tr('Blur • Drag the area you want to keep sharp'), 'numero': tr('Numbers • Click for the next number; drag from the marker to its target'), 'balao': tr('Balloon • Drag to draw; move the tail handle to point at an object')}
        self.tool_hint.setText(hints[name])
        self.tool_hint.setToolTip(hints[name])

    def choose_arrow_color(self):
        obj = self.canvas.objects[self.canvas.selected] if self.canvas.selected is not None else None
        current = obj.get('color', '#ef233c') if obj is not None and obj['kind'] == 'seta' else self.canvas.arrow_color
        color = QColorDialog.getColor(QColor(current), self, tr('Arrow color'), QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_arrow_color(color)

    def display_arrow_color(self, color):
        obj = self.canvas.objects[self.canvas.selected] if self.canvas.selected is not None else None
        style = obj.get('style', 'classic') if obj is not None and obj['kind'] == 'seta' else self.canvas.arrow_style
        icon = toolbar_icon('arrow:'+style, color)
        self.tool_actions['seta'].setIcon(icon)
        self.color_actions['seta'].setIcon(icon)

    def choose_rectangle_color(self):
        obj = self.canvas.objects[self.canvas.selected] if self.canvas.selected is not None else None
        current = obj.get('color', '#ef233c') if obj is not None and obj['kind'] == 'retângulo' else self.canvas.rectangle_color
        color = QColorDialog.getColor(QColor(current), self, tr('Rectangle color'), QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_rectangle_color(color)

    def display_rectangle_color(self, color):
        canvas = self.canvas
        obj = canvas.objects[canvas.selected] if canvas.selected is not None else None
        values = obj if obj is not None and obj['kind'] == 'retângulo' else canvas.rectangle_format
        icon = toolbar_icon('rectangle:rounded' if values.get('rounded', False) else 'rectangle', color)
        self.tool_actions['retângulo'].setIcon(icon)
        self.color_actions['retângulo'].setIcon(icon)

    def choose_marker_color(self):
        color = QColorDialog.getColor(QColor(self.canvas.marker_color), self, tr('Marker color'), QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.canvas.set_marker_color(color)

    def display_marker_color(self, color):
        icon = toolbar_icon('marker:'+self.current_marker_style(), color)
        self.tool_actions['numero'].setIcon(icon)
        self.color_actions['numero'].setIcon(icon)

    def update_dimensions(self):
        if self.canvas.base.isNull():
            self.dimensions.setText(tr('No image • Capture a screen to get started'))
        else:
            self.dimensions.setText(f'{self.canvas.base.width()} × {self.canvas.base.height()} px')
        self.zoom_slider.setEnabled(not self.canvas.base.isNull())

    def display_blur_radius(self, radius):
        self.blur_strength.blockSignals(True)
        self.blur_strength.setValue(radius)
        self.blur_strength.blockSignals(False)
        self.blur_slider.blockSignals(True)
        self.blur_slider.setValue(radius)
        self.blur_slider.blockSignals(False)

    def show_shortcuts(self):
        self.statusBar().setToolTip(' • '.join((f'{value}: {mode_label(mode)}' for mode, value in self.settings.hotkeys.items())))

    def apply_settings(self, directory, hotkeys, language=None, workspace_limit=None):
        workspace_limit = self.settings.workspace_limit if workspace_limit is None else workspace_limit
        apply_limit = directory != self.settings.directory or workspace_limit != self.settings.workspace_limit
        old = self.settings.hotkeys.copy()
        changed = hotkeys != old
        if changed and global_hotkeys_available():
            self.hotkeys.configure(hotkeys)
        try:
            self.settings.save(directory, hotkeys, language, workspace_limit)
        except OSError:
            if changed and global_hotkeys_available():
                self.hotkeys.configure(old)
            raise
        set_language(self.settings.language)
        self.update_panel.render()
        self.workspace.retranslate()
        self.sync_tool(self.canvas.tool)
        self.tabs.retranslate()
        self.history = History(directory, self.settings.workspace_limit)
        if apply_limit:
            self.history.enforce_limit()
        self.workspace.set_store(self.history)
        self.show_shortcuts()

    def refresh(self):
        self.workspace.refresh()

    def open_history(self, item):
        path = self.history.directory / item.text()
        image = read_image(path)
        if image.isNull():
            QMessageBox.warning(self, tr('Workspace'), tr('Could not open this image.'))
            return
        self.tabs.open_image(image, path)
        self.update_dimensions()

    def refresh_monitor_menu(self):
        self.monitor_menu.clear()
        action = self.monitor_menu.addAction(tr('All monitors'), lambda: self.capture('tela'))
        action.setToolTip(tr('Capture the complete virtual desktop.'))
        self.monitor_menu.addSeparator()
        for index, screen in enumerate(QApplication.screens()):
            rect, ratio = screen.geometry(), screen.devicePixelRatio()
            label = tr('Monitor {number}').format(number=index+1)+' • '+screen.name()+f' • {round(rect.width()*ratio)} × {round(rect.height()*ratio)}'
            if screen is QApplication.primaryScreen():
                label += ' • '+tr('Primary')
            action = self.monitor_menu.addAction(label, lambda checked=False, name=screen.name(): self.capture('tela', name))
            action.setToolTip(label)
        self.monitor_menu.setToolTipsVisible(True)

    def cancel_capture(self):
        if hasattr(self, 'selector'):
            self.selector.close()
        self._capture_pending = False
        self.open_editor()

    def capture(self, mode, screen_name=None):
        if self._quitting or self._capture_pending:
            return
        if sys.platform == 'darwin':
            from .macos_backend import ensure_screen_permission
            try:
                ensure_screen_permission()
            except RuntimeError as exc:
                QMessageBox.warning(self, tr('Capture error'), str(exc))
                return
        self.canvas.finish_text()
        self._capture_pending = True
        if self._settings_dialog is not None:
            self._settings_dialog.hide()
        self.hide()
        QTimer.singleShot(350, lambda: self.prepare_capture(mode, screen_name))

    def prepare_capture(self, mode, screen_name=None):
        if self._quitting:
            return
        if mode != 'janela':
            self.take_capture(mode, None, screen_name)
            return
        try:
            desktop, geometry = capture_desktop()
            choices = [choice for choice in windows() if choice[1].intersects(geometry)]
            if not choices:
                raise RuntimeError(tr('No windows available.'))
            picker = WindowPicker(choices, desktop, geometry, self)
            try:
                target = picker.selected_window() if picker.exec() == picker.DialogCode.Accepted else None
            finally:
                picker.deleteLater()
            if target is None:
                self.cancel_capture()
                return
            self.hide()
            activate_window(target[2])
            QTimer.singleShot(450, lambda: self.take_capture(mode, target))
        except Exception as exc:
            self.cancel_capture()
            QMessageBox.warning(self, tr('Window capture'), str(exc))

    def take_capture(self, mode, target, screen_name=None):
        if self._quitting:
            return
        try:
            if target is not None:
                target = next((choice for choice in windows() if choice[2] == target[2]), None)
                if target is None:
                    raise RuntimeError(tr('The selected window is no longer available.'))
            pixmap, geometry = capture_desktop(screen_name)
            if pixmap.isNull():
                raise RuntimeError(tr('Capture unavailable. Run in an X11 session.'))
            if mode == 'região':
                self.selector = Selector(pixmap, geometry, self)
                self.selector.selected.connect(lambda rect: self.finish_capture(crop_desktop(pixmap, geometry, rect).toImage()))
                self.selector.cancelled.connect(self.cancel_capture)
                self.selector.show()
                return
            if target is not None:
                if sys.platform == 'darwin':
                    from .macos_backend import capture_window
                    self.finish_capture(capture_window(target[2]))
                    return
                pixmap = crop_desktop(pixmap, geometry, target[1])
            self.finish_capture(pixmap.toImage())
        except Exception as exc:
            self.cancel_capture()
            QMessageBox.warning(self, tr('Capture error'), str(exc))

    def finish_capture(self, image):
        self._capture_pending = False
        self.open_editor()
        try:
            path = self.history.save(image)
            self.tabs.open_image(image, path, capture=True)
            self.update_dimensions()
            self.refresh()
        except OSError as exc:
            QMessageBox.warning(self, tr('Workspace'), str(exc))

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
            return False
        path, _ = QFileDialog.getSaveFileName(self, tr('Save image'), str(self.history.directory / tr('capture.png')), 'PNG (*.png);;JPEG (*.jpg *.jpeg)', '', QFileDialog.Option.DontUseNativeDialog)
        if path:
            if not Path(path).suffix:
                path += '.png'
            if not self.canvas.image.save(path):
                QMessageBox.warning(self, tr('Save'), tr('Could not save to this path or format.'))
                return False
            else:
                self.tabs.mark_saved(path)
                try:
                    self.history.save(self.canvas.image)
                    self.refresh()
                except OSError as exc:
                    QMessageBox.warning(self, tr('Workspace'), str(exc))
                return True
        return False

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
    set_language(Settings().language)
    from .single_instance import SingleInstance
    try:
        instance = SingleInstance(parent=app)
        primary = instance.acquire()
        if not primary and '--restart-after-update' in sys.argv:
            import time
            deadline = time.monotonic()+15
            while not primary and time.monotonic() < deadline:
                time.sleep(.05)
                primary = instance.acquire()
    except (OSError, RuntimeError) as exc:
        QMessageBox.critical(None, 'ScreenDepresso', str(exc))
        sys.exit(1)
    if not primary:
        if not instance.notify_existing():
            QMessageBox.information(None, 'ScreenDepresso', tr('ScreenDepresso is already running. Open it from the tray or taskbar.'))
        return
    try:
        run_application(app, instance)
    finally:
        instance.release()


def run_application(app, instance):
    window = MainWindow()
    instance.set_activation_handler(window.activate_existing_instance)
    app.aboutToQuit.connect(instance.release)
    window.show()
    if '--smoke-test' in sys.argv:
        settings = window.open_settings(updates=True)
        window.update_panel.on_completed('check', None)
        QApplication.processEvents()
        if settings.tabs.currentWidget() is not window.update_panel or not window.update_panel.button.isVisible():
            raise RuntimeError('Inline updates panel smoke test failed')
        window.update_panel.notes_button.click()
        from . import __version__
        if not window.update_panel.notes_view.isVisible() or __version__ not in window.update_panel.notes_view.toPlainText():
            raise RuntimeError('Installed release notes smoke test failed')
        window.update_panel.notes_button.click()
        from . import i18n
        set_language('pt_BR')
        if i18n._translator.native.isEmpty() or settings.workspace_limit.itemText(4) != 'Sem limite':
            raise RuntimeError('Portuguese Qt translation catalog smoke test failed')
        set_language('en')
        settings.reject()
        if window.update_panel.parentWidget() is not window:
            raise RuntimeError('Updates panel was not preserved after closing Settings')
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.fill(QColor('red'))
        window.finish_capture(image)
        window.copy()
        if QApplication.clipboard().image() != image or window.list.count() < 1:
            raise RuntimeError('Smoke test failed')
        second = QImage(120, 80, QImage.Format.Format_ARGB32)
        second.fill(QColor('blue'))
        window.finish_capture(second)
        window.copy()
        if window.tabs.count() != 2 or QApplication.clipboard().image() != second:
            raise RuntimeError('Capture tabs smoke test failed')
        canvas = window.canvas
        canvas.objects.append({'kind': 'balao', 'a': [5, 5], 'b': [110, 55], 'tail': [15, 75], **canvas.bubble_format})
        canvas.objects.extend([{'kind': 'desfoque', 'a': [x, 1], 'b': [x+20, 20], 'radius': 14} for x in (1, 80)])
        canvas.objects.append({'kind': 'seta', 'a': [20, 70], 'b': [110, 70], 'color': '#ef233c', 'style': 'line'})
        canvas.objects.append({'kind': 'retângulo', 'a': [2, 2], 'b': [118, 78], 'color': '#2563eb', 'width': 6, 'rounded': True, 'radius': 12})
        canvas.objects.append({'kind': 'numero', 'a': [95, 65], 'b': [110, 75], 'number': 1, 'style': 'hexagon'})
        canvas.start_text({'kind': 'texto', 'a': [15, 10], 'b': [105, 50], 'text': 'Smoke', **canvas.text_format})
        canvas.finish_text()
        rendered = canvas.image
        if rendered == second or len(canvas.objects) != 7 or rendered.pixelColor(60, 70) != QColor('#ef233c'):
            raise RuntimeError('Balloon and text smoke test failed')
        window.zoom_slider.setValue(150)
        if canvas.zoom != 1.5 or canvas.image != rendered:
            raise RuntimeError('Zoom changed the exported image')
        window.tabs.setCurrentIndex(0)
        if window.canvas.image != image:
            raise RuntimeError('First capture was lost after opening another tab')
        import tempfile
        with tempfile.TemporaryDirectory(prefix='.workspace-smoke-', dir=window.history.directory) as temporary:
            store = History(temporary, 0)
            original = store.save(image)
            duplicate = store.duplicate(original)
            if duplicate.read_bytes() != original.read_bytes():
                raise RuntimeError('Workspace duplicate smoke test failed')
            store.trash(duplicate)
            if duplicate.exists() or not original.exists():
                raise RuntimeError('Workspace trash smoke test failed')
        print('Interface, tabs, balloons, text, zoom, workspace and clipboard: OK (offscreen)', flush=True)
        QTimer.singleShot(100, window.request_quit)
    sys.exit(app.exec())
if __name__ == '__main__':
    main()
