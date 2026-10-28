import hashlib
import json
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from screendepresso.windows_backend import virtual_key, WindowsHotkeys, WinAPI, WM_HOTKEY
from screendepresso.updater import Release
from screendepresso.platform_support import config_path, data_directory


def test_windows_virtual_keys():
    assert virtual_key('Ctrl+Shift+1') == (0x4006, 0x31)
    assert virtual_key('Alt+Print') == (0x4001, 0x2C)
    assert virtual_key('Meta+F24') == (0x4008, 0x87)
    assert virtual_key('Ctrl+A')[1] == 0x41
    with pytest.raises(ValueError):
        virtual_key('F25')


def test_windows_update_manifest_selection_and_url_validation():
    filename = 'screendepresso_0.5.0_windows_amd64_setup.exe'
    manifest = {'version':'0.5.0', 'windows-amd64': {
        'url':f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v0.5.0/{filename}',
        'sha256':hashlib.sha256(b'installer').hexdigest(), 'size':9}}
    release = Release.parse(manifest, '0.4.2', machine='AMD64', system='Windows')
    assert release.filename == filename
    manifest['windows-amd64']['url'] = 'https://example.com/installer.exe'
    with pytest.raises(ValueError):
        Release.parse(manifest, '0.4.2', machine='AMD64', system='Windows')


def test_windows_default_paths(monkeypatch, tmp_path):
    from screendepresso import platform_support
    monkeypatch.setattr(platform_support.sys, 'platform', 'win32')
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert config_path() == tmp_path/'ScreenDepresso/settings.json'
    assert data_directory() == tmp_path/'ScreenDepresso/captures'


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows API integration')
def test_native_windows_hotkey_registration_dispatch_and_rollback():
    app = QApplication.instance() or QApplication([])
    first, second = WindowsHotkeys(), WindowsHotkeys()
    captures = []
    first.capture.connect(captures.append)
    try:
        first.configure({'tela':'Ctrl+Alt+F10'})
        api = WinAPI()
        assert api.user.PostThreadMessageW(first.thread_id, WM_HOTKEY, 100, 0)
        for _ in range(30):
            QApplication.processEvents()
            QTest.qWait(10)
            if captures:
                break
        assert captures == ['tela']
        second.configure({'janela':'Ctrl+Alt+F11'})
        with pytest.raises(ValueError):
            first.configure({'tela':'Ctrl+Alt+F11'})
        assert first.shortcuts == {'tela':'Ctrl+Alt+F10'}
        captures.clear()
        assert api.user.PostThreadMessageW(first.thread_id, WM_HOTKEY, 100, 0)
        for _ in range(30):
            QApplication.processEvents()
            QTest.qWait(10)
            if captures:
                break
        assert captures == ['tela']
    finally:
        first.stop()
        second.stop()
    assert first.thread is None
    assert second.thread is None


def test_release_merging_rejects_corrupt_installers(tmp_path):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location('merge_release', Path(__file__).parents[1]/'packaging/merge_release.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    linux, windows = tmp_path/'linux', tmp_path/'windows'
    for directory, key, filename, manifest_name in (
        (linux,'linux-amd64','screendepresso_0.5.0_amd64.deb','update.json'),
        (windows,'windows-amd64','screendepresso_0.5.0_windows_amd64_setup.exe','windows-update.json'),
    ):
        directory.mkdir()
        package = directory/filename
        package.write_bytes(b'package')
        data={'version':'0.5.0', key:{'url':f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v0.5.0/{filename}', 'sha256':hashlib.sha256(b'package').hexdigest(), 'size':7}}
        (directory/manifest_name).write_text(json.dumps(data), encoding='utf-8')
    merged = module.merge(linux, windows, tmp_path/'merged')
    assert set(merged) == {'version','linux-amd64','windows-amd64'}
    (windows/'screendepresso_0.5.0_windows_amd64_setup.exe').write_bytes(b'corrupted')
    with pytest.raises(ValueError):
        module.merge(linux, windows, tmp_path/'bad')


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows desktop capture')
def test_native_windows_capture_and_window_enumeration(tmp_path):
    import os
    import subprocess
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'windows'
    script = '''
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from screendepresso.platform_support import capture_desktop
from screendepresso.windows_backend import windows
app = QApplication([])
window = QWidget(None, Qt.WindowType.FramelessWindowHint)
window.setWindowTitle('ScreenDepresso native capture test')
window.setStyleSheet('background: #e63946;')
window.setGeometry(70, 70, 220, 140)
window.show()
window.raise_()
window.activateWindow()
assert QTest.qWaitForWindowExposed(window, 5000)
QTest.qWait(500)
pixmap, geometry = capture_desktop()
assert not pixmap.isNull()
point = window.geometry().center() - geometry.topLeft()
color = pixmap.toImage().pixelColor(point)
assert color.red() > 200 and color.green() < 100, color.name()
assert any(title == window.windowTitle() for title, rect in windows())
from screendepresso.capture_ui import Selector
selector = Selector(pixmap, geometry)
selector.show()
QTest.qWait(100)
assert selector.overlays
for overlay in selector.overlays:
 assert overlay.geometry() == overlay.capture_screen.geometry().intersected(geometry)
 assert overlay.image.height() == round(overlay.bounds.height()*pixmap.devicePixelRatio())
selector.cancel()
assert not selector.overlays
window.close()
'''
    result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_windows_installer_launches_with_verified_path(monkeypatch, tmp_path):
    import subprocess
    from screendepresso.updater import start_windows_installer
    installer = tmp_path/'setup.exe'
    calls = []
    monkeypatch.setattr(subprocess, 'Popen', lambda args, **kwargs: calls.append((args,kwargs)) or object())
    start_windows_installer(installer)
    assert calls[0][0] == [str(installer), '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS']
    assert calls[0][1]['env']['PYINSTALLER_RESET_ENVIRONMENT'] == '1'
