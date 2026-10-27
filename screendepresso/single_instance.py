"""Per-user/profile ownership lock and a small, user-only activation channel."""
import hashlib
import os
from pathlib import Path
import sys
import time
from PySide6.QtCore import QObject, QLockFile, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from .i18n import tr
from .platform_support import config_path


class SingleInstance(QObject):
    activation_requested = Signal()

    def __init__(self, directory=None, parent=None):
        super().__init__(parent)
        directory = Path(directory) if directory is not None else config_path().parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        identity = os.path.normcase(str(directory.resolve()))
        self.name = 'screendepresso-'+hashlib.sha256(identity.encode()).hexdigest()[:32]
        self.lock = QLockFile(str(directory/'instance.lock'))
        # Long-running or minimized instances never become stale due to age.
        # Qt can still recover the lock of a process that is no longer alive.
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept_connections)
        self.owns_lock = False
        self.pending_activation = False

    def acquire(self):
        if self.owns_lock:
            return True
        if not self.lock.tryLock(0):
            if self.lock.error() == QLockFile.LockError.LockFailedError:
                return False
            raise RuntimeError(tr('Could not create the application instance lock.'))
        self.owns_lock = True
        # Only the lock owner may remove an endpoint left behind after a crash.
        QLocalServer.removeServer(self.name)
        if not self.server.listen(self.name):
            self.release()
            raise RuntimeError(tr('Could not start the application activation channel.'))
        return True

    def _accept_connections(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            received = bytearray()
            completed = [False]

            def read_request(socket=socket, received=received, completed=completed):
                if completed[0]:
                    return
                received.extend(bytes(socket.read(65-len(received))))
                if len(received) > 64:
                    socket.abort()
                elif b'\n' in received:
                    completed[0] = True
                    if bytes(received) == b'activate\n':
                        self.pending_activation = True
                        self.activation_requested.emit()
                    socket.disconnectFromServer()

            socket.readyRead.connect(read_request)
            socket.disconnected.connect(socket.deleteLater)
            timeout = QTimer(socket)
            timeout.setSingleShot(True)
            timeout.timeout.connect(socket.abort)
            timeout.start(2000)
            if socket.bytesAvailable():
                read_request()

    def set_activation_handler(self, callback):
        self.activation_requested.connect(callback)
        if self.pending_activation:
            QTimer.singleShot(0, callback)

    def notify_existing(self, timeout_ms=2500):
        # A newly launched Windows process can grant foreground access to the
        # existing one before asking it to restore its window.
        if sys.platform == 'win32':
            import ctypes
            info = self.lock.getLockInfo()
            if info and info[0] > 0:
                pid = info[0]
                user = ctypes.WinDLL('user32', use_last_error=True)
                user.AllowSetForegroundWindow.argtypes = [ctypes.c_ulong]
                user.AllowSetForegroundWindow(pid)
        deadline = time.monotonic()+timeout_ms/1000
        while time.monotonic() < deadline:
            socket = QLocalSocket()
            socket.connectToServer(self.name)
            if socket.waitForConnected(100):
                written = socket.write(b'activate\n')
                if written == len(b'activate\n') and (socket.bytesToWrite() == 0 or socket.waitForBytesWritten(500)):
                    socket.disconnectFromServer()
                    return True
                socket.abort()
            time.sleep(0.05)
        return False

    def release(self):
        if self.owns_lock:
            for socket in self.server.findChildren(QLocalSocket):
                socket.abort()
            self.server.close()
            QLocalServer.removeServer(self.name)
            self.lock.unlock()
            self.owns_lock = False
