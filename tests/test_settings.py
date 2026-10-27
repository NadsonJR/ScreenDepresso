import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from screendepresso.settings import Settings, SettingsDialog, DEFAULT_HOTKEYS, parse_hotkey
from screendepresso.app import MainWindow
from test_editor import image

app = QApplication.instance() or QApplication([])


def test_settings_roundtrip_and_corrupt_file(tmp_path):
    path = tmp_path/'settings.json'
    settings = Settings(path)
    assert settings.hotkeys == DEFAULT_HOTKEYS
    custom = dict(DEFAULT_HOTKEYS, tela='Alt+Print')
    settings.save(str(tmp_path/'captures'), custom)
    restored = Settings(path)
    assert restored.directory == str(tmp_path/'captures')
    assert restored.hotkeys == custom
    path.write_text('invalid')
    assert Settings(path).hotkeys == DEFAULT_HOTKEYS


@pytest.mark.parametrize('value', ['', 'Ctrl', 'Ctrl+Ctrl+A', 'Ctrl+Bogus', 'Ctrl+A, Ctrl+B'])
def test_invalid_shortcuts(value):
    with pytest.raises(ValueError):
        parse_hotkey(value)


def test_portable_hotkeys():
    assert parse_hotkey('Shift+Ctrl+A') == parse_hotkey('Ctrl+Shift+A')
    assert parse_hotkey('Print') == ((), 'Print')
    assert parse_hotkey('Alt+F12') == (('Alt',), 'F12')


def test_settings_directory_and_window_shortcuts(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    monkeypatch.delenv('DISPLAY', raising=False)
    window = MainWindow()
    window.canvas.load(image())
    window.canvas.tool = 'retângulo'
    from test_editor import gesture
    gesture(window.canvas, (20, 20), (100, 80))
    edited = window.canvas.image
    window.show()
    window.activateWindow()
    app.processEvents()
    QTest.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert window.canvas.image == image()
    QTest.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert window.canvas.image == edited
    folder = tmp_path/'new'
    folder.mkdir()
    window.apply_settings(str(folder), dict(DEFAULT_HOTKEYS, tela='Alt+Print'))
    window.finish_capture(image())
    assert list(folder.glob('*.png'))
    dialog = SettingsDialog(window)
    assert dialog.shortcuts['tela'].keySequence().toString() == 'Alt+Print'
    assert dialog.directory.text() == str(folder)
    window.close()
    other = MainWindow()
    assert other.history.directory == folder
    assert other.settings.hotkeys['tela'] == 'Alt+Print'
    other.close()
