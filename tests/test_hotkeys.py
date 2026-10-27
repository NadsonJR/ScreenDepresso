"""Real X11 key grabs in an isolated virtual display (no user desktop)."""
import os
import select
import shutil
import subprocess
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from screendepresso.hotkeys import Hotkeys
from screendepresso.settings import DEFAULT_HOTKEYS


@pytest.fixture
def x11(monkeypatch):
    executable = shutil.which('Xvfb')
    if not executable:
        pytest.skip('Xvfb is required for global hotkey integration tests')
    process = subprocess.Popen([executable, '-displayfd', '1', '-screen', '0', '320x240x24', '-nolisten', 'tcp', '-ac'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert select.select([process.stdout], [], [], 5)[0], 'Xvfb did not start'
        number = process.stdout.readline().decode().strip()
        assert number.isdigit()
        monkeypatch.setenv('DISPLAY', ':'+number)
        from Xlib import display
        connection = display.Display()
        yield connection
        connection.close()
    finally:
        process.terminate()
        process.wait(timeout=5)


def press(connection, key):
    from Xlib import X, XK
    from Xlib.ext import xtest
    codes = [connection.keysym_to_keycode(XK.string_to_keysym(k)) for k in ('Control_L', 'Shift_L', key)]
    for code in codes:
        xtest.fake_input(connection, X.KeyPress, code)
    for code in reversed(codes):
        xtest.fake_input(connection, X.KeyRelease, code)
    connection.sync()
    for _ in range(20):
        QApplication.processEvents()
        QTest.qWait(10)


def test_rebind_and_conflict_rollback(x11):
    app = QApplication.instance() or QApplication([])
    hotkeys = Hotkeys()
    captured = []
    hotkeys.capture.connect(captured.append)
    try:
        hotkeys.configure(DEFAULT_HOTKEYS)
        press(x11, '1')
        assert captured == ['tela']
        changed = dict(DEFAULT_HOTKEYS, tela='Ctrl+Shift+4')
        hotkeys.configure(changed)
        captured.clear()
        press(x11, '1')
        assert captured == []
        press(x11, '4')
        assert captured == ['tela']
        from Xlib import X, XK
        code = x11.keysym_to_keycode(XK.string_to_keysym('5'))
        x11.screen().root.grab_key(code, X.ControlMask | X.ShiftMask, False, X.GrabModeAsync, X.GrabModeAsync)
        x11.sync()
        with pytest.raises(ValueError, match='in use'):
            hotkeys.configure(dict(DEFAULT_HOTKEYS, tela='Ctrl+Shift+5'))
        captured.clear()
        press(x11, '4')
        assert captured == ['tela']
        assert hotkeys.shortcuts == changed
    finally:
        hotkeys.stop()
