import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import pytest
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QToolBar
from screendepresso.app import MainWindow
from screendepresso.close_dialog import CloseDialog
from screendepresso.i18n import set_language
from test_editor import image, gesture

app = QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    monkeypatch.delenv('DISPLAY', raising=False)
    # Avoid a real tray host; separate cases exercise both supported and fallback paths.
    monkeypatch.setattr(QSystemTrayIcon, 'isSystemTrayAvailable', lambda: False)
    window = MainWindow()
    window.show()
    app.processEvents()
    yield window
    window.request_quit()
    set_language('en')


def test_simplified_controls_and_blur_menu(window):
    assert window.menuWidget() is None
    tools = window.findChild(QToolBar, 'tools')
    assert 'recorte' not in window.tool_actions
    assert not any('Delete' in action.text() for action in tools.actions())
    ribbon = window.findChild(QToolBar, 'ribbon')
    crops = [a for a in ribbon.actions() if a.text() == 'Crop']
    assert len(crops) == 1
    crops[0].trigger()
    assert window.canvas.tool == 'recorte'
    assert not any(a.isChecked() for a in window.tool_actions.values())
    button = tools.widgetForAction(window.tool_actions['desfoque'])
    assert button.menu() is window.blur_menu
    assert window.blur_menu.isAncestorOf(window.blur_strength)
    assert window.blur_menu.isAncestorOf(window.blur_slider)
    window.canvas.load(image())
    window.choose_tool('retângulo')
    gesture(window.canvas, (10, 10), (100, 80))
    from PySide6.QtTest import QTest
    QTest.keyClick(window, Qt.Key.Key_Delete)
    assert not window.canvas.objects  # Keyboard deletion is retained.


def test_close_to_tray_keeps_document_and_hotkeys(window, monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, 'isSystemTrayAvailable', lambda: True)
    monkeypatch.setattr(window, 'ask_close_action', lambda: 'minimize')
    calls = []
    monkeypatch.setattr(window.hotkeys, 'stop', lambda: calls.append('stop'))
    monkeypatch.setattr(window.tray, 'show', lambda: calls.append('tray'))
    window.canvas.load(image())
    window.choose_tool('texto')
    gesture(window.canvas, (10, 10), (150, 100))
    window.canvas.text_editor.setPlainText('Kept while minimized')
    window.close()
    assert not window.isVisible()
    assert calls == ['tray']
    assert window.canvas.objects[0]['text'] == 'Kept while minimized'
    window.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
    assert window.isVisible()
    assert window.canvas.objects[0]['text'] == 'Kept while minimized'
    window.hide()
    window.tray.contextMenu().actions()[0].trigger()
    assert window.isVisible()


def test_missing_tray_minimizes_to_accessible_taskbar(window, monkeypatch):
    monkeypatch.setattr(window, 'ask_close_action', lambda: 'minimize')
    window.close()
    assert window.isMinimized()
    assert window.isVisible()
    assert not window._quitting
    window.open_editor()
    assert not window.isMinimized()
    assert window.isVisible()


def test_cancel_close_retains_window(window, monkeypatch):
    monkeypatch.setattr(window, 'ask_close_action', lambda: 'cancel')
    window.close()
    assert window.isVisible()
    assert not window._quitting


def test_quit_choice_stops_background_services(window, monkeypatch):
    calls = []
    monkeypatch.setattr(window, 'ask_close_action', lambda: 'quit')
    monkeypatch.setattr(window.hotkeys, 'stop', lambda: calls.append('hotkeys'))
    monkeypatch.setattr(window.tray, 'hide', lambda: calls.append('tray'))
    monkeypatch.setattr(window, '_quit_application', lambda: calls.append('quit'))
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert window._quitting
    assert calls == ['hotkeys', 'tray', 'quit']
    assert not window.isVisible()


def test_close_dialog_buttons_and_translation(window):
    dialog = CloseDialog(window, True)
    assert dialog.minimize_button.text() == 'Minimize to tray'
    QTimer.singleShot(0, dialog.minimize_button.click)
    dialog.exec()
    assert dialog.choice == 'minimize'
    window.apply_settings(window.settings.directory, window.settings.hotkeys, 'pt_BR')
    translated = CloseDialog(window, False)
    assert translated.minimize_button.text() == 'Minimizar para a barra de tarefas'
    assert translated.quit_button.text() == 'Sair'
    QTimer.singleShot(0, translated.cancel_button.click)
    translated.exec()
    assert translated.choice == 'cancel'


def test_application_smoke_test_exits_without_close_prompt(tmp_path):
    import subprocess
    import sys
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['XDG_CONFIG_HOME'] = str(tmp_path/'config')
    env['XDG_DATA_HOME'] = str(tmp_path/'data')
    result = subprocess.run([sys.executable, '-m', 'screendepresso.app', '--smoke-test'], env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert 'OK (offscreen)' in result.stdout
