import select
import threading

from PySide6.QtCore import QObject, Signal
from .settings import parse_hotkey


class Hotkeys(QObject):
    capture = Signal(str)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.thread = None
        self.connection = None
        self.stop_event = threading.Event()
        self.shortcuts = {}

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                raise RuntimeError('Não foi possível encerrar os atalhos anteriores.')
        if self.connection:
            from Xlib import X
            self.connection.screen().root.ungrab_key(X.AnyKey, X.AnyModifier)
            self.connection.sync()
            self.connection.close()
        self.connection = self.thread = None

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
        from Xlib import X, XK, display
        connection = display.Display()
        root = connection.screen().root
        errors, bindings = [], {}
        connection.set_error_handler(lambda err, request: errors.append(str(err)))
        try:
            masks = {'Ctrl': X.ControlMask, 'Shift': X.ShiftMask, 'Alt': X.Mod1Mask, 'Meta': X.Mod4Mask}
            for mode, value in shortcuts.items():
                modifiers, key = parse_hotkey(value)
                code = connection.keysym_to_keycode(XK.string_to_keysym(key))
                if not code:
                    raise ValueError(f'Tecla não disponível neste teclado: {value}')
                mask = sum(masks[m] for m in modifiers)
                if (code, mask) in bindings:
                    raise ValueError('Atalhos duplicados.')
                bindings[code, mask] = mode
                for locks in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                    root.grab_key(code, mask | locks, False, X.GrabModeAsync, X.GrabModeAsync)
            connection.sync()
            if errors:
                raise ValueError('Atalho ocupado por outro aplicativo. Escolha outra combinação.')
        except Exception:
            root.ungrab_key(X.AnyKey, X.AnyModifier)
            connection.sync()
            connection.close()
            raise
        self.connection = connection
        self.shortcuts = shortcuts.copy()
        self.stop_event.clear()
        def listen():
            try:
                while not self.stop_event.is_set():
                    if not connection.pending_events() and not select.select([connection.fileno()], [], [], 0.15)[0]:
                        continue
                    event = connection.next_event()
                    if event.type == X.KeyPress:
                        mode = bindings.get((event.detail, event.state & (X.ControlMask | X.ShiftMask | X.Mod1Mask | X.Mod4Mask)))
                        if mode:
                            self.capture.emit(mode)
            except Exception as exc:
                self.failed.emit(str(exc))
        self.thread = threading.Thread(target=listen, daemon=True)
        self.thread.start()
