import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import subprocess
import sys
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from screendepresso.single_instance import SingleInstance

app = QApplication.instance() or QApplication([])


def pump_until(predicate, seconds=3):
    deadline = time.monotonic()+seconds
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        QTest.qWait(10)
    assert predicate()


def notify_while_servicing_events(instance):
    # Windows named pipes require the server's event loop to accept connections.
    # A real second launch runs in another process; do not block the primary UI.
    import threading
    results = []
    worker = threading.Thread(target=lambda: results.append(instance.notify_existing()))
    worker.start()
    try:
        pump_until(lambda: not worker.is_alive(), seconds=5)
    finally:
        worker.join(timeout=3)
    assert results == [True]


def test_only_one_owner_and_activation_is_delivered(tmp_path):
    owner = SingleInstance(tmp_path)
    duplicate = SingleInstance(tmp_path)
    calls = []
    try:
        assert owner.acquire()
        owner.set_activation_handler(lambda: calls.append('open'))
        assert not duplicate.acquire()
        notify_while_servicing_events(duplicate)
        pump_until(lambda: calls == ['open'])
        duplicate.release()  # A non-owner must not remove the running endpoint.
        notify_while_servicing_events(duplicate)
        pump_until(lambda: calls == ['open', 'open'])
    finally:
        owner.release()
        duplicate.release()
    assert duplicate.acquire()
    duplicate.release()


def test_activation_during_initialization_is_not_lost(tmp_path):
    owner, duplicate = SingleInstance(tmp_path), SingleInstance(tmp_path)
    calls = []
    try:
        assert owner.acquire()
        assert not duplicate.acquire()
        notify_while_servicing_events(duplicate)
        pump_until(lambda: owner.pending_activation)
        owner.set_activation_handler(lambda: calls.append('open'))
        pump_until(lambda: calls == ['open'])
    finally:
        owner.release()


def primary_script():
    return '''
import sys
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QTimer
from screendepresso.single_instance import SingleInstance
app=QCoreApplication([])
app.setApplicationName('screendepresso')
instance=SingleInstance(sys.argv[1])
assert instance.acquire()
Path(sys.argv[2]).write_text('ready')
instance.set_activation_handler(lambda: Path(sys.argv[3]).write_text('activated'))
QTimer.singleShot(20000, app.quit)
try: app.exec()
finally: instance.release()
'''


def test_cross_process_exclusion_activation_and_crash_recovery(tmp_path):
    ready, activated = tmp_path/'ready', tmp_path/'activated'
    directory = tmp_path/'profile'
    process = subprocess.Popen([sys.executable, '-c', primary_script(), str(directory), str(ready), str(activated)])
    candidate = SingleInstance(directory)
    try:
        pump_until(ready.exists, seconds=8)
        assert not candidate.acquire()
        assert candidate.notify_existing()
        pump_until(activated.exists)
        assert process.poll() is None
        process.kill()  # Simulate an unclean exit: no Python/Qt cleanup.
        process.wait(timeout=5)
        assert candidate.acquire()  # Recover the dead owner's lock and local socket.
    finally:
        candidate.release()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_second_real_launch_restores_existing_window_without_loading_a_new_one(tmp_path, monkeypatch):
    from screendepresso.app import MainWindow
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    owner = SingleInstance()
    window = MainWindow()
    try:
        assert owner.acquire()
        owner.set_activation_handler(window.activate_existing_instance)
        window.hide()
        env = os.environ.copy()
        env['QT_QPA_PLATFORM'] = 'offscreen'
        # The existing endpoint is live before the event loop is serviced.
        process = subprocess.Popen([sys.executable, '-m', 'screendepresso.app', '--smoke-test'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            pump_until(lambda: process.poll() is not None, seconds=8)
            stdout, stderr = process.communicate(timeout=2)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=3)
        assert process.returncode == 0, stderr
        assert 'OK (offscreen)' not in stdout  # It did not construct a second editor.
        pump_until(window.isVisible)
    finally:
        owner.release()
        window.request_quit()


def test_simultaneous_startup_has_exactly_one_primary(tmp_path):
    script = '''
import sys, time
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QTimer
from screendepresso.single_instance import SingleInstance
app=QCoreApplication([])
app.setApplicationName('screendepresso')
while not Path(sys.argv[2]).exists(): time.sleep(0.01)
instance=SingleInstance(sys.argv[1])
if instance.acquire():
 Path(sys.argv[3]).write_text('primary')
 QTimer.singleShot(20000, app.quit)
 try: app.exec()
 finally: instance.release()
else:
 assert instance.notify_existing()
 Path(sys.argv[3]).write_text('secondary')
'''
    gate = tmp_path/'start'
    outputs = [tmp_path/'a', tmp_path/'b']
    processes = [subprocess.Popen([sys.executable, '-c', script, str(tmp_path/'profile'), str(gate), str(output)]) for output in outputs]
    try:
        gate.touch()
        pump_until(lambda: all(p.exists() for p in outputs), seconds=8)
        assert sorted(p.read_text() for p in outputs) == ['primary', 'secondary']
        secondary = next(process for process, output in zip(processes, outputs) if output.read_text() == 'secondary')
        assert secondary.wait(timeout=5) == 0
        primary = next(process for process, output in zip(processes, outputs) if output.read_text() == 'primary')
        assert primary.poll() is None
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)


def test_update_restart_waits_for_old_instance_then_opens_new_editor(tmp_path, monkeypatch):
    import queue
    import threading
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    owner = SingleInstance()
    assert owner.acquire()
    script = '''
import sys
from screendepresso.single_instance import SingleInstance
original = SingleInstance.acquire
def acquire(self):
 result = original(self)
 if not result: print('waiting', flush=True)
 return result
SingleInstance.acquire = acquire
sys.argv = ['screendepresso', '--smoke-test', '--restart-after-update']
from screendepresso.app import main
main()
'''
    process = subprocess.Popen([sys.executable,'-c',script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = queue.Queue()
    worker = threading.Thread(target=lambda: output.put(process.stdout.readline()))
    worker.start()
    try:
        assert output.get(timeout=10).strip() == 'waiting'
        worker.join(timeout=1)
        assert process.poll() is None and owner.owns_lock
        owner.release()
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr
        assert 'OK (offscreen)' in stdout
    finally:
        owner.release()
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        worker.join(timeout=2)
