"""Windows desktop integration. Native libraries are loaded only on Windows."""
import ctypes
from ctypes import wintypes
import threading
from PySide6.QtCore import QObject, Signal, QRect
from .settings import parse_hotkey
from .i18n import tr

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012


def virtual_key(sequence):
    modifiers, key = parse_hotkey(sequence)
    masks = {'Alt': 1, 'Ctrl': 2, 'Shift': 4, 'Meta': 8}
    mask = 0x4000 | sum(masks[m] for m in modifiers)  # MOD_NOREPEAT
    names = {'Escape': 0x1B, 'space': 0x20, 'Delete': 0x2E, 'Insert': 0x2D,
             'Prior': 0x21, 'Next': 0x22, 'Left': 0x25, 'Up': 0x26,
             'Right': 0x27, 'Down': 0x28, 'BackSpace': 8, 'Print': 0x2C,
             'Tab': 9, 'Home': 0x24, 'End': 0x23, 'Return': 0x0D}
    if len(key) == 1 and key.isascii() and key.isalnum():
        code = ord(key.upper())
    elif key.startswith('F') and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        code = 0x70 + int(key[1:]) - 1
    elif key in names:
        code = names[key]
    else:
        raise ValueError(tr('This key is not supported on Windows.'))
    return mask, code


class WinAPI:
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        # Explicit pointer-sized HWND/LPARAM declarations also work in frozen x64 builds.
        signatures = {
            'RegisterHotKey': ([wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT], wintypes.BOOL),
            'UnregisterHotKey': ([wintypes.HWND, ctypes.c_int], wintypes.BOOL),
            'GetMessageW': ([ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT], ctypes.c_int),
            'PeekMessageW': ([ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT], wintypes.BOOL),
            'PostThreadMessageW': ([wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
            'IsWindowVisible': ([wintypes.HWND], wintypes.BOOL),
            'IsIconic': ([wintypes.HWND], wintypes.BOOL),
            'GetWindowTextLengthW': ([wintypes.HWND], ctypes.c_int),
            'GetWindowTextW': ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            'GetWindowRect': ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            'GetWindowThreadProcessId': ([wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            'SetForegroundWindow': ([wintypes.HWND], wintypes.BOOL),
            'GetForegroundWindow': ([], wintypes.HWND),
            'ShowWindow': ([wintypes.HWND, ctypes.c_int], wintypes.BOOL),
            'MonitorFromWindow': ([wintypes.HWND, wintypes.DWORD], wintypes.HMONITOR),
            'GetMonitorInfoW': ([wintypes.HMONITOR, ctypes.c_void_p], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        self.kernel.GetCurrentThreadId.restype = wintypes.DWORD
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback_type, wintypes.LPARAM]
        self.user.EnumWindows.restype = wintypes.BOOL


class WindowsHotkeys(QObject):
    capture = Signal(str)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.thread = None
        self.thread_id = 0
        self.shortcuts = {}
        self.stop_event = threading.Event()
        self.api = None

    def configure(self, shortcuts):
        old = self.shortcuts.copy()
        self.stop()
        try:
            self.start(shortcuts)
        except Exception:
            if old:
                self.start(old)
            raise

    def start(self, shortcuts):
        bindings = {100+i: (mode, *virtual_key(value)) for i, (mode, value) in enumerate(shortcuts.items())}
        if len({(mask, code) for _, mask, code in bindings.values()}) != len(bindings):
            raise ValueError(tr('Duplicate hotkeys.'))
        api = self.api = WinAPI()
        ready = threading.Event()
        startup_errors = []
        self.stop_event.clear()

        def listen():
            registered = []
            try:
                self.thread_id = api.kernel.GetCurrentThreadId()
                message = wintypes.MSG()
                api.user.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
                for identifier, (_, mask, code) in bindings.items():
                    if not api.user.RegisterHotKey(None, identifier, mask, code):
                        error = ctypes.get_last_error()
                        if error == 1409:
                            raise ValueError(tr('Hotkey is in use by another application. Choose another combination.'))
                        raise ctypes.WinError(error)
                    registered.append(identifier)
                ready.set()
                while not self.stop_event.is_set():
                    result = api.user.GetMessageW(ctypes.byref(message), None, 0, 0)
                    if result == 0:
                        break
                    if result == -1:
                        raise ctypes.WinError(ctypes.get_last_error())
                    if message.message == WM_HOTKEY and message.wParam in bindings:
                        self.capture.emit(bindings[message.wParam][0])
            except Exception as exc:
                if not ready.is_set():
                    startup_errors.append(exc)
                else:
                    self.failed.emit(str(exc))
            finally:
                for identifier in registered:
                    api.user.UnregisterHotKey(None, identifier)
                self.thread_id = 0
                ready.set()

        self.thread = threading.Thread(target=listen, daemon=True)
        self.thread.start()
        if not ready.wait(5):
            self.stop()
            raise RuntimeError(tr('Could not register global hotkeys.'))
        if startup_errors:
            self.thread.join(timeout=2)
            self.thread = None
            raise startup_errors[0]
        self.shortcuts = shortcuts.copy()

    def stop(self):
        self.stop_event.set()
        if self.thread_id and self.api:
            self.api.user.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
        if self.thread:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                raise RuntimeError(tr('Could not stop the previous hotkeys.'))
        self.thread = None


def windows(with_ids=False):
    from PySide6.QtGui import QGuiApplication
    api = WinAPI()
    result = []

    class MonitorInfo(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                    ('work', wintypes.RECT), ('flags', wintypes.DWORD),
                    ('device', wintypes.WCHAR * 32)]

    def visit(hwnd, parameter):
        if not api.user.IsWindowVisible(hwnd) or api.user.IsIconic(hwnd):
            return True
        length = api.user.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        title = ctypes.create_unicode_buffer(length+1)
        api.user.GetWindowTextW(hwnd, title, length+1)
        if title.value == 'ScreenDepresso':
            return True
        if with_ids:
            import os
            pid = wintypes.DWORD()
            api.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == os.getpid():
                return True
        native = wintypes.RECT()
        if not api.user.GetWindowRect(hwnd, ctypes.byref(native)):
            return True
        rect = QRect(native.left, native.top, native.right-native.left, native.bottom-native.top)
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        monitor = api.user.MonitorFromWindow(hwnd, 2)
        if api.user.GetMonitorInfoW(monitor, ctypes.byref(info)):
            for screen in QGuiApplication.screens():
                if screen.name().lower() == info.device.lower():
                    scale = screen.devicePixelRatio()
                    origin = screen.geometry().topLeft()
                    rect = QRect(origin.x()+round((native.left-info.monitor.left)/scale),
                                 origin.y()+round((native.top-info.monitor.top)/scale),
                                 round((native.right-native.left)/scale), round((native.bottom-native.top)/scale))
                    break
        if rect.width() > 0 and rect.height() > 0:
            result.append((title.value, rect, int(hwnd)) if with_ids else (title.value, rect))
        return True

    callback = api.callback_type(visit)
    if not api.user.EnumWindows(callback, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return result


def activate_window(hwnd):
    api = WinAPI()
    if api.user.IsIconic(hwnd):
        api.user.ShowWindow(hwnd, 9)
    if not api.user.SetForegroundWindow(hwnd) and api.user.GetForegroundWindow() != hwnd:
        raise RuntimeError(tr('Could not bring the selected window to the foreground.'))
