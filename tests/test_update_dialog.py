import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import hashlib
import io
import threading
import time
from types import SimpleNamespace
import pytest
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
from screendepresso import updater
from screendepresso import update_dialog as module
from screendepresso.i18n import set_language

app = QApplication.instance() or QApplication([])


def pump(predicate, seconds=4):
    deadline = time.monotonic()+seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert predicate()


def release():
    return updater.Release('0.6.3', 'package.exe', 'https://github.com/NadsonJR/ScreenDepresso/releases/download/v0.6.3/package.exe', 'a'*64, 10)


@pytest.fixture
def dialog():
    set_language('en')
    dialog = module.UpdateDialog()
    dialog.show()
    yield dialog
    dialog.busy = False
    dialog.close()
    set_language('en')


def test_automatic_check_has_no_buttons_and_latest_result_stays_buttonless(dialog, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(module, 'check_update', lambda version: gate.wait(3) and None)
    try:
        dialog.perform()
        assert dialog.phase == 'checking' and dialog.busy
        assert not any(b.isVisible() for b in dialog.findChildren(QPushButton))
    finally:
        gate.set()
    pump(lambda: not dialog.busy)
    assert dialog.phase == 'latest'
    assert not dialog.button.isVisible()


def test_download_progress_and_windows_explicit_restart(dialog, monkeypatch, tmp_path):
    gate = threading.Event()
    package = tmp_path/'download'/'package.exe'
    package.parent.mkdir()
    package.write_bytes(b'installer')
    monkeypatch.setattr(module, 'sys', SimpleNamespace(platform='win32'))
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    calls = []
    monkeypatch.setattr(module, 'start_windows_installer', lambda path, **kwargs: calls.append((path,kwargs)))
    dialog.quit_requested.connect(lambda: calls.append('quit'))
    def download(selected, progress):
        progress(0,10)
        progress(3,10)
        assert gate.wait(3)
        progress(10,10)
        return package
    monkeypatch.setattr(module, 'download_release', download)
    dialog.on_completed('check',release())
    assert dialog.button.isVisible()
    try:
        dialog.button.click()
        pump(lambda: dialog.progress_bar.value() == 30)
        assert dialog.phase == 'downloading'
        assert dialog.progress_bar.isVisible()
        assert not dialog.button.isVisible()
    finally:
        gate.set()
    pump(lambda: dialog.phase == 'ready')
    assert dialog.progress_bar.value() == 100
    assert dialog.button.text() == 'Restart application'
    assert not calls  # Finishing the download never closes the app automatically.
    dialog.button.click()
    assert calls == [(package, {'restart':True}), 'quit']
    assert package.exists()  # The detached installer still needs the verified bytes.
    dialog.phase = 'finished'


def test_linux_install_completion_shows_restart_and_launches_before_quitting(dialog, monkeypatch, tmp_path):
    monkeypatch.setattr(module, 'sys', SimpleNamespace(platform='linux'))
    directory = tmp_path/'download'
    directory.mkdir()
    dialog.package = directory/'app.deb'
    dialog.package.write_bytes(b'package')
    dialog.phase = 'installing'
    dialog.busy = True
    dialog.installed(0,QProcess.ExitStatus.NormalExit)
    assert dialog.phase == 'installed'
    assert dialog.button.text() == 'Restart application'
    assert not directory.exists()
    calls = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(module, 'start_restarted_application', lambda: calls.append('start'))
    dialog.quit_requested.connect(lambda: calls.append('quit'))
    dialog.button.click()
    assert calls == ['start','quit']


def test_restart_cancel_or_launch_error_keeps_the_app_open(dialog, monkeypatch):
    dialog.show_restart('installed')
    calls = []
    dialog.quit_requested.connect(lambda: calls.append('quit'))
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.No)
    dialog.button.click()
    assert not calls and not dialog.busy
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    def failure():
        raise OSError('Cannot start process')
    monkeypatch.setattr(module, 'sys', SimpleNamespace(platform='linux'))
    monkeypatch.setattr(module, 'start_restarted_application', failure)
    dialog.button.click()
    assert not calls
    assert dialog.button.isVisible() and not dialog.busy
    assert 'Could not restart' in dialog.label.text()


def test_check_error_is_inline_without_check_button(dialog):
    dialog.on_failed('Network unavailable')
    assert not dialog.button.isVisible()
    assert 'Network unavailable' in dialog.label.text()
    assert not dialog.progress_bar.isVisible()


def test_download_failure_cannot_offer_restart(dialog, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    def corrupt(*args):
        raise ValueError('SHA-256 verification failed')
    monkeypatch.setattr(module, 'download_release', corrupt)
    dialog.on_completed('check',release())
    dialog.button.click()
    pump(lambda: not dialog.busy)
    assert dialog.phase == 'error'
    assert dialog.package is None
    assert dialog.button.text() == 'Download and install'
    assert not dialog.progress_bar.isVisible()


def test_download_reports_actual_byte_progress_without_weakening_verification(monkeypatch, tmp_path):
    data = b'x'*(1024*1024+17)
    path = tmp_path/'download'
    path.mkdir()
    monkeypatch.setattr(updater.tempfile,'mkdtemp',lambda **kwargs: str(path))
    monkeypatch.setattr(updater,'open_url',lambda url: io.BytesIO(data))
    selected = updater.Release('0.6.3','app.deb','https://github.com/file',hashlib.sha256(data).hexdigest(),len(data))
    counts = []
    output = updater.download_release(selected,lambda count,total: counts.append((count,total)))
    assert output.read_bytes() == data
    assert counts == [(0,len(data)),(1024*1024,len(data)),(len(data),len(data))]


def test_windows_installer_restart_arguments(monkeypatch, tmp_path):
    import subprocess
    calls = []
    monkeypatch.setattr(subprocess,'Popen', lambda command,**kwargs: calls.append((command,kwargs)))
    installer = tmp_path/'setup.exe'
    updater.start_windows_installer(installer,restart=True)
    assert calls[0][0][0] == str(installer)
    assert '/SCREENDEPRESSO_RESTART=1' in calls[0][0]
    assert '/NORESTARTAPPLICATIONS' in calls[0][0]
    assert calls[0][1]['env']['PYINSTALLER_RESET_ENVIRONMENT'] == '1'


def test_restarted_application_uses_fresh_bundle_and_waits_for_lock(monkeypatch):
    import subprocess,sys
    calls = []
    monkeypatch.setattr(subprocess,'Popen',lambda command,**kwargs: calls.append((command,kwargs)))
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    updater.start_restarted_application()
    assert calls[0][0] == [sys.executable,'--restart-after-update']
    assert calls[0][1]['env']['PYINSTALLER_RESET_ENVIRONMENT'] == '1'
