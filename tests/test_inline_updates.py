import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import threading
import time
from types import SimpleNamespace
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QMessageBox

from screendepresso.app import MainWindow
from screendepresso import update_panel as module
from screendepresso.i18n import set_language
from screendepresso.updater import Release

app = QApplication.instance() or QApplication([])


def pump(predicate):
    deadline = time.monotonic()+5
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert predicate()


def release():
    return Release('0.6.6','package.exe','https://github.com/package.exe','a'*64,100)


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path/'data'))
    monkeypatch.setattr(QMessageBox,'question',lambda *args: pytest.fail('Updates must stay inline'))
    window = MainWindow()
    window.show()
    app.processEvents()
    yield window
    window.update_panel.shutdown()
    window.request_quit()
    set_language('en')


def test_check_runs_in_updates_tab_and_restores_button_with_latest_message(window, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(module,'check_update',lambda version: gate.wait(4) and None)
    settings = window.open_settings(updates=True)
    panel = window.update_panel
    assert settings.tabs.currentWidget() is panel
    assert not isinstance(panel,QDialog)
    assert not settings.isModal()
    assert not settings.buttons.button(QDialogButtonBox.StandardButton.Save).isVisible()
    assert settings.buttons.button(QDialogButtonBox.StandardButton.Close).isVisible()
    app.processEvents()
    action_bounds = panel.action_stack.geometry()
    before = {w for w in app.topLevelWidgets() if isinstance(w,QDialog) and w.isVisible()}
    try:
        panel.button.click()
        app.processEvents()
        assert panel.loader.isVisible()
        assert panel.action_stack.geometry() == action_bounds
        assert not panel.button.isVisible()
        assert {w for w in app.topLevelWidgets() if isinstance(w,QDialog) and w.isVisible()} == before
    finally:
        gate.set()
    pump(lambda: not panel.busy)
    assert panel.button.isVisible() and panel.button.text() == 'Check for updates'
    assert 'latest version' in panel.label.text()
    assert settings.tabs.currentWidget() is panel


def test_download_survives_closing_and_reopening_settings(window, monkeypatch, tmp_path):
    gate = threading.Event()
    monkeypatch.setattr(module,'sys',SimpleNamespace(platform='win32'))
    package = tmp_path/'download'/'package.exe'
    package.parent.mkdir()
    package.write_bytes(b'installer')
    def download(selected, progress):
        progress(25,100)
        assert gate.wait(4)
        progress(100,100)
        return package
    monkeypatch.setattr(module,'download_release',download)
    settings = window.open_settings(updates=True)
    panel = window.update_panel
    panel.on_completed('check',release())
    try:
        panel.button.click()
        pump(lambda: panel.progress_bar.value() == 25)
        settings.reject()
        assert panel.parentWidget() is window
        assert panel.busy
        reopened = window.open_settings(updates=True)
        assert reopened is not settings
        assert reopened.tabs.currentWidget() is panel
        assert panel.progress_bar.isVisible() and panel.progress_bar.value() == 25
    finally:
        gate.set()
    pump(lambda: panel.phase == 'ready')
    assert package.exists()
    assert panel.button.text() == 'Restart application'
    assert panel.button.isVisible()


def test_keep_current_and_recheck_stay_in_same_settings_page(window, monkeypatch):
    settings = window.open_settings(updates=True)
    panel = window.update_panel
    panel.on_completed('check',release())
    assert panel.keep_button.isVisible()
    panel.keep_button.click()
    assert panel.phase == 'kept' and panel.release is None
    assert panel.button.text() == 'Check for updates'
    monkeypatch.setattr(module,'check_update',lambda version: release())
    panel.button.click()
    pump(lambda: not panel.busy)
    assert panel.phase == 'available'
    assert panel.button.text() == 'Download and install'
    assert panel.keep_button.isVisible()
    assert window._settings_dialog is settings
    assert settings.tabs.currentWidget() is panel


def test_tray_check_opens_existing_updates_tab_without_an_extra_dialog(window, monkeypatch):
    calls = []
    monkeypatch.setattr(window.update_panel,'check_for_updates',lambda: calls.append('check'))
    settings = window.open_settings()
    window.check_updates()
    assert calls == ['check']
    assert window._settings_dialog is settings
    assert settings.tabs.currentWidget() is window.update_panel


def test_update_status_translates_when_language_changes(window):
    window.open_settings(updates=True)
    panel = window.update_panel
    panel.on_completed('check',release())
    window.apply_settings(window.settings.directory,window.settings.hotkeys,'pt_BR')
    assert panel.button.text() == 'Baixar e instalar'
    assert panel.keep_button.text() == 'Manter versão atual'
    assert 'Nova versão' in panel.label.text()
    panel.keep_button.click()
    assert 'Mantendo a versão atual' in panel.label.text()
    assert panel.button.text() == 'Verificar atualizações'


def test_capture_hides_modeless_settings_and_keeps_update_state(window, monkeypatch):
    from screendepresso import app as app_module
    settings = window.open_settings(updates=True)
    window.update_panel.on_completed('check',release())
    monkeypatch.setattr(app_module.QTimer,'singleShot',lambda *args: None)
    window.capture('tela')
    assert not settings.isVisible()
    assert window.update_panel.phase == 'available'
