"""macOS window discovery, permission checks and Carbon global hotkeys.

Quartz/AppKit are imported lazily so other platforms can test the key mapping.
Carbon registration integrates with Qt's native main-thread event loop and does
not require Accessibility or Input Monitoring permissions.
"""
import ctypes as C
from itertools import count
import os
from pathlib import Path
import subprocess
import tempfile
from PySide6.QtCore import QObject, QRect, Signal
from .i18n import tr
from .settings import parse_hotkey
from .workspace import read_image


def ensure_screen_permission():
    import Quartz
    if not Quartz.CGPreflightScreenCaptureAccess():
        Quartz.CGRequestScreenCaptureAccess()
        if not Quartz.CGPreflightScreenCaptureAccess():
            raise RuntimeError(tr('Allow ScreenDepresso in System Settings → Privacy & Security → Screen & System Audio Recording, then reopen the app.'))


def windows():
    import Quartz as Q
    result = []
    for info in Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionOnScreenOnly | Q.kCGWindowListExcludeDesktopElements, Q.kCGNullWindowID) or []:
        bounds = info.get(Q.kCGWindowBounds, {})
        title = info.get(Q.kCGWindowName, '')
        if (info.get(Q.kCGWindowOwnerPID) == os.getpid() or info.get(Q.kCGWindowLayer, 0) != 0
                or not title or bounds.get('Width', 0) < 2 or bounds.get('Height', 0) < 2):
            continue
        rect = QRect(round(bounds['X']), round(bounds['Y']), round(bounds['Width']), round(bounds['Height']))
        result.append((f"{info.get(Q.kCGWindowOwnerName, '')} — {title}", rect, int(info[Q.kCGWindowNumber])))
    return result


def activate_window(wid):
    import Quartz as Q
    from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
    for info in Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionIncludingWindow, wid) or []:
        if int(info.get(Q.kCGWindowNumber, -1)) == wid:
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(info[Q.kCGWindowOwnerPID])
            if app:
                app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            return


def capture_window(wid):
    # screencapture supports other apps' windows on modern macOS; Qt's
    # grabWindow(windowID) only supports this application's windows on Cocoa.
    try:
        with tempfile.TemporaryDirectory(prefix='screendepresso-window-') as directory:
            path = Path(directory)/'window.png'
            subprocess.run(['/usr/sbin/screencapture', '-x', '-o', '-l', str(int(wid)), str(path)],
                           check=True, capture_output=True, timeout=10)
            image = read_image(path)
            if not image.isNull():
                return image
    except (OSError, subprocess.SubprocessError):
        pass
    raise RuntimeError(tr('Could not capture this window. Check Screen Recording permission and try again.'))


KEY_CODES = dict(zip('asdfhgzxcvbqwerty123465=97-80]ou[ip\nlj\'k;\\,/nm.',
                     (0,1,2,3,4,5,6,7,8,9,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47)))
KEY_CODES.update({'space':49, 'Tab':48, 'Return':36, 'Escape':53, 'BackSpace':51,
                  'Delete':117, 'Home':115, 'End':119, 'Prior':116, 'Next':121,
                  'Left':123, 'Right':124, 'Down':125, 'Up':126, 'Insert':114})
KEY_CODES.update(dict(zip((f'F{i}' for i in range(1,21)),
                         (122,120,99,118,96,97,98,100,101,109,103,111,105,107,113,106,64,79,80,90))))


def carbon_key(value):
    modifiers, key = parse_hotkey(value)
    if key not in KEY_CODES:
        raise ValueError(tr('Key unavailable on this keyboard: ')+value)
    # Qt PortableText Ctrl means Command on macOS; Meta means physical Control.
    masks = {'Ctrl':256, 'Shift':512, 'Alt':2048, 'Meta':4096}
    return KEY_CODES[key], sum(masks[m] for m in modifiers)


def fourcc(value):
    return int.from_bytes(value.encode('ascii'), 'big')


_signatures = count(fourcc('ScDp'))


class EventType(C.Structure):
    _fields_ = [('eventClass', C.c_uint32), ('eventKind', C.c_uint32)]


class HotKeyID(C.Structure):
    _fields_ = [('signature', C.c_uint32), ('id', C.c_uint32)]


class MacHotkeys(QObject):
    capture = Signal(str)
    failed = Signal(str)

    def __init__(self, library=None):
        super().__init__()
        self.api = library
        self.handler = C.c_void_p()
        self.references = []
        self.shortcuts = {}
        self.bindings = {}
        self.signature = next(_signatures)
        self.callback = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_void_p, C.c_void_p)(self.dispatch)

    def load(self):
        if self.api is not None:
            return
        self.api = C.CDLL('/System/Library/Frameworks/Carbon.framework/Carbon')
        signatures = {
            'GetApplicationEventTarget': (C.c_void_p, []),
            'InstallEventHandler': (C.c_int32, [C.c_void_p, C.c_void_p, C.c_uint32, C.POINTER(EventType), C.c_void_p, C.POINTER(C.c_void_p)]),
            'RegisterEventHotKey': (C.c_int32, [C.c_uint32, C.c_uint32, HotKeyID, C.c_void_p, C.c_uint32, C.POINTER(C.c_void_p)]),
            'UnregisterEventHotKey': (C.c_int32, [C.c_void_p]),
            'RemoveEventHandler': (C.c_int32, [C.c_void_p]),
            'GetEventParameter': (C.c_int32, [C.c_void_p, C.c_uint32, C.c_uint32, C.c_void_p, C.c_uint32, C.c_void_p, C.c_void_p]),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(self.api, name)
            function.restype, function.argtypes = result, arguments

    def dispatch(self, handler, event, data):
        identifier = HotKeyID()
        status = self.api.GetEventParameter(event, fourcc('----'), fourcc('hkid'), None,
                                           C.sizeof(identifier), None, C.byref(identifier))
        if status == 0 and identifier.signature == self.signature and identifier.id in self.bindings:
            self.capture.emit(self.bindings[identifier.id])
            return 0
        return -9874

    def stop(self):
        for reference in self.references:
            self.api.UnregisterEventHotKey(reference)
        self.references.clear()
        self.bindings.clear()
        if self.handler.value:
            self.api.RemoveEventHandler(self.handler)
            self.handler = C.c_void_p()

    def start(self, shortcuts):
        self.load()
        keys = [carbon_key(value) for value in shortcuts.values()]
        if len(set(keys)) != len(keys):
            raise ValueError(tr('Duplicate hotkeys.'))
        target = self.api.GetApplicationEventTarget()
        event = EventType(fourcc('keyb'), 6)  # kEventHotKeyPressed
        try:
            if self.api.InstallEventHandler(target, self.callback, 1, C.byref(event), None, C.byref(self.handler)):
                raise RuntimeError(tr('Could not register macOS global hotkeys.'))
            for identifier, (mode, key) in enumerate(zip(shortcuts, keys), 1):
                reference = C.c_void_p()
                if self.api.RegisterEventHotKey(*key, HotKeyID(self.signature, identifier), target, 0, C.byref(reference)):
                    raise ValueError(tr('Hotkey is in use by another application. Choose another combination.'))
                self.references.append(reference)
                self.bindings[identifier] = mode
        except Exception:
            self.stop()
            raise
        self.shortcuts = shortcuts.copy()

    def configure(self, shortcuts):
        old = self.shortcuts.copy()
        self.stop()
        try:
            self.start(shortcuts)
        except Exception:
            if old:
                self.start(old)
            raise
