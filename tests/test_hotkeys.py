"""Real X11 key grabs in an isolated virtual display (no user desktop)."""
import os
import select
import shutil
import subprocess
import tempfile
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
    # XKB warnings can fill an unread stderr pipe before Xvfb reports its
    # display number. A file keeps diagnostics without blocking server startup.
    errors = tempfile.TemporaryFile()
    process = subprocess.Popen([executable, '-displayfd', '1', '-screen', '0', '320x240x24', '-nolisten', 'tcp', '-ac'], stdout=subprocess.PIPE, stderr=errors)
    try:
        if not select.select([process.stdout], [], [], 20)[0]:
            process.terminate()
            process.wait(timeout=5)
            errors.seek(0)
            pytest.fail('Xvfb did not start within 20 seconds:\n'+errors.read().decode(errors='replace')[-4000:])
        number = process.stdout.readline().decode().strip()
        assert number.isdigit()
        monkeypatch.setenv('DISPLAY', ':'+number)
        from Xlib import display
        connection = display.Display()
        yield connection
        connection.close()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        errors.close()


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


def test_native_x11_capture_and_full_screen_region_overlay(x11):
    import sys
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'xcb'
    script = '''
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from screendepresso.platform_support import capture_desktop, crop_desktop
from screendepresso.capture_ui import Selector
app = QApplication([])
window = QWidget(None, Qt.WindowType.FramelessWindowHint)
window.setStyleSheet('background: #e63946;')
window.setGeometry(10,10,80,50)
window.show()
assert QTest.qWaitForWindowExposed(window,5000)
QTest.qWait(200)
pixmap, geometry = capture_desktop()
assert geometry == app.primaryScreen().geometry()
point = window.geometry().center()-geometry.topLeft()
color = pixmap.toImage().pixelColor(round(point.x()*pixmap.devicePixelRatio()), round(point.y()*pixmap.devicePixelRatio()))
assert color.red() > 200 and color.green() < 100, color.name()
selector = Selector(pixmap,geometry)
selected = []
selector.selected.connect(selected.append)
selector.show()
QTest.qWait(100)
assert selector.overlays[0].geometry() == geometry
assert selector.overlays[0].windowFlags() & Qt.WindowType.X11BypassWindowManagerHint
overlay = selector.overlays[0]
QTest.mousePress(overlay,Qt.MouseButton.LeftButton,pos=QPoint(1,1))
QTest.mouseMove(overlay,overlay.rect().bottomRight())
QTest.mouseRelease(overlay,Qt.MouseButton.LeftButton,pos=overlay.rect().bottomRight())
assert selected == [geometry.adjusted(1,1,0,0)], selected
assert not selector.overlays
assert crop_desktop(pixmap,geometry,selected[0]).height() == round((geometry.height()-1)*pixmap.devicePixelRatio())
window.close()
'''
    result = subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr
