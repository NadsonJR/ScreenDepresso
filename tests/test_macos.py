import ctypes as C
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication
from screendepresso import macos_backend as mac
from screendepresso import platform_support, updater, update_panel

app = QApplication.instance() or QApplication([])


def test_mac_key_mapping_matches_qt_portable_shortcuts():
    assert mac.carbon_key('Ctrl+Shift+1') == (18, 768)
    assert mac.carbon_key('Meta+Alt+A') == (0, 6144)
    assert mac.carbon_key('Ctrl+F20') == (90, 256)
    for key in ('Print', 'F21'):
        with pytest.raises(ValueError):
            mac.carbon_key(key)
    for letter in 'abcdefghijklmnopqrstuvwxyz0123456789':
        assert letter in mac.KEY_CODES
    assert len({mac.KEY_CODES[k] for k in 'abcdefghijklmnopqrstuvwxyz0123456789'}) == 36


def test_mac_default_paths_and_dispatch(monkeypatch):
    monkeypatch.setattr(platform_support.sys, 'platform', 'darwin')
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    assert platform_support.config_path() == Path.home()/'Library/Application Support/ScreenDepresso/settings.json'
    assert platform_support.data_directory() == Path.home()/'Library/Application Support/ScreenDepresso/captures'
    assert platform_support.global_hotkeys_available()
    from screendepresso.hotkeys import Hotkeys
    assert isinstance(Hotkeys(), mac.MacHotkeys)


def test_screen_recording_denial_is_actionable(monkeypatch):
    requests = []
    quartz = SimpleNamespace(CGPreflightScreenCaptureAccess=lambda: False,
                             CGRequestScreenCaptureAccess=lambda: requests.append(True))
    monkeypatch.setitem(sys.modules, 'Quartz', quartz)
    with pytest.raises(RuntimeError, match='Privacy'):
        mac.ensure_screen_permission()
    assert requests == [True]
    quartz.CGPreflightScreenCaptureAccess = lambda: True
    mac.ensure_screen_permission()
    assert requests == [True]


def test_mac_window_discovery_excludes_own_and_non_application_windows(monkeypatch):
    template = {'pid':123, 'layer':0, 'title':'Document', 'owner':'Editor', 'number':42,
                'bounds':{'X':-800,'Y':20,'Width':600,'Height':400}}
    quartz = SimpleNamespace(kCGWindowListOptionOnScreenOnly=1, kCGWindowListExcludeDesktopElements=16,
        kCGNullWindowID=0, kCGWindowBounds='bounds', kCGWindowName='title', kCGWindowOwnerPID='pid',
        kCGWindowLayer='layer', kCGWindowOwnerName='owner', kCGWindowNumber='number',
        CGWindowListCopyWindowInfo=lambda *args: [template, {**template,'pid':mac.os.getpid()},
                                                   {**template,'layer':24}, {**template,'title':''}])
    monkeypatch.setitem(sys.modules, 'Quartz', quartz)
    assert mac.windows() == [('Editor — Document', QRect(-800,20,600,400),42)]


@pytest.mark.parametrize('arch', ['arm64', 'x86_64'])
def test_mac_updates_select_native_architecture_and_reject_other_sources(arch):
    key_arch = 'arm64' if arch == 'arm64' else 'amd64'
    filename = f'screendepresso_0.7.0_macos_{key_arch}.dmg'
    data = {'version':'0.7.0', 'macos-'+key_arch:{'url':f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v0.7.0/{filename}',
             'sha256':hashlib.sha256(b'dmg').hexdigest(), 'size':3}}
    result = updater.Release.parse(data, '0.6.7', machine=arch, system='Darwin')
    assert result.filename == filename
    data['macos-'+key_arch]['url'] = 'https://evil.example/file.dmg'
    with pytest.raises(ValueError):
        updater.Release.parse(data, '0.6.7', machine=arch, system='Darwin')


def test_mac_update_opens_verified_dmg_without_quitting_or_running_linux_installer(monkeypatch, tmp_path):
    panel = update_panel.UpdatePanel()
    panel.show()
    monkeypatch.setattr(update_panel, 'sys', SimpleNamespace(platform='darwin'))
    opened, quit_requests = [], []
    panel.quit_requested.connect(lambda: quit_requests.append(True))
    monkeypatch.setattr(update_panel, 'start_macos_installer', lambda path: opened.append(path))
    package = tmp_path/'download'/'update.dmg'
    package.parent.mkdir()
    package.write_bytes(b'verified dmg')
    panel.on_completed('download', package)
    assert panel.phase == 'mac_ready'
    assert panel.button.text() == 'Open installer'
    assert panel.progress_bar.value() == 100
    panel.button.click()
    assert opened == [package] and not quit_requests
    assert panel.phase == 'mac_manual'
    panel.shutdown()
    assert package.exists()  # Finder still needs the disk image.
    panel.close()


def test_mac_installer_opener_uses_argument_list_and_clean_environment(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv('DYLD_LIBRARY_PATH', '/old/app')
    monkeypatch.setattr(mac.subprocess, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))
    path = tmp_path/'with spaces.dmg'
    updater.start_macos_installer(path)
    assert calls[0][0][0] == ['/usr/bin/open', str(path)]
    assert 'DYLD_LIBRARY_PATH' not in calls[0][1]['env']


@pytest.mark.skipif(sys.platform != 'darwin', reason='Native Carbon event integration')
def test_native_carbon_registration_event_dispatch_conflict_and_rollback():
    first, second = mac.MacHotkeys(), mac.MacHotkeys()
    captured = []
    first.capture.connect(captured.append)
    try:
        first.configure({'tela':'Ctrl+Alt+F10'})
        second.configure({'janela':'Ctrl+Alt+F11'})
        with pytest.raises(ValueError):
            first.configure({'tela':'Ctrl+Alt+F11'})
        assert first.shortcuts == {'tela':'Ctrl+Alt+F10'}
        api = first.api
        api.CreateEvent.restype = C.c_int32
        api.CreateEvent.argtypes = [C.c_void_p, C.c_uint32, C.c_uint32, C.c_double, C.c_uint32, C.POINTER(C.c_void_p)]
        api.SetEventParameter.restype = C.c_int32
        api.SetEventParameter.argtypes = [C.c_void_p, C.c_uint32, C.c_uint32, C.c_uint32, C.c_void_p]
        api.SendEventToEventTarget.restype = C.c_int32
        api.SendEventToEventTarget.argtypes = [C.c_void_p, C.c_void_p]
        api.ReleaseEvent.argtypes = [C.c_void_p]
        event = C.c_void_p()
        assert api.CreateEvent(None, mac.fourcc('keyb'), 6, 0, 0, C.byref(event)) == 0
        try:
            identifier = mac.HotKeyID(first.signature, 1)
            assert api.SetEventParameter(event, mac.fourcc('----'), mac.fourcc('hkid'), C.sizeof(identifier), C.byref(identifier)) == 0
            assert api.SendEventToEventTarget(event, api.GetApplicationEventTarget()) == 0
            assert captured == ['tela']
        finally:
            api.ReleaseEvent(event)
    finally:
        first.stop()
        second.stop()
    assert not first.references and not first.handler.value


def test_combined_manifest_verifies_both_mac_architectures(tmp_path):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location('merge_release', Path(__file__).parents[1]/'packaging/merge_release.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    directories = []
    for key, suffix, metadata in [('linux-amd64','amd64.deb','update.json'),
                                  ('windows-amd64','windows_amd64_setup.exe','windows-update.json'),
                                  ('macos-arm64','macos_arm64.dmg','macos-update.json'),
                                  ('macos-amd64','macos_amd64.dmg','macos-update.json')]:
        directory = tmp_path/key
        directory.mkdir()
        directories.append(directory)
        filename = f'screendepresso_0.7.0_{suffix}'
        (directory/filename).write_bytes(b'package')
        data = {'version':'0.7.0',key:{'url':f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v0.7.0/{filename}',
                'sha256':hashlib.sha256(b'package').hexdigest(),'size':7}}
        (directory/metadata).write_text(json.dumps(data),encoding='utf-8')
    result = module.merge(*directories[:2], tmp_path/'combined', *directories[2:])
    assert set(result) == {'version','linux-amd64','windows-amd64','macos-arm64','macos-amd64'}
    (directories[2]/'screendepresso_0.7.0_macos_arm64.dmg').write_bytes(b'corrupt')
    with pytest.raises(ValueError):
        module.merge(*directories[:2], tmp_path/'bad', *directories[2:])
