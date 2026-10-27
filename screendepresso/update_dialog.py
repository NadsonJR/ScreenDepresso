from .i18n import tr
import shutil
import threading
from pathlib import Path
from PySide6.QtCore import QProcess, QProcessEnvironment, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox
from . import __version__
from .updater import check_update, download_release, system_environment

class UpdateDialog(QDialog):
    completed = Signal(str, object)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Update ScreenDepresso'))
        self.resize(460, 180)
        self.release = None
        self.package = None
        self.busy = False
        self.process = None
        layout = QVBoxLayout(self)
        self.label = QLabel(f"{tr('Installed version: ')}{__version__}\nUbuntu 24.04+ • x86_64 • X11")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.button = QPushButton(tr('Check for updates'))
        self.button.setToolTip(tr('Check for updates'))
        self.button.clicked.connect(self.perform)
        layout.addWidget(self.button)
        self.completed.connect(self.on_completed)
        self.failed.connect(self.on_failed)

    def job(self, operation, function):
        self.busy = True
        self.button.setEnabled(False)

        def run():
            try:
                self.completed.emit(operation, function())
            except Exception as exc:
                self.failed.emit(str(exc))
        threading.Thread(target=run, daemon=True).start()

    def perform(self):
        if self.release is None:
            self.label.setText(tr('Checking published versions on GitHub…'))
            self.job('check', lambda: check_update(__version__))
        else:
            answer = QMessageBox.question(self, tr('Install update'), tr('Download and install version ') + self.release.version + tr('?\nUbuntu will request administrator authorization. Your captures will be preserved.'))
            if answer == QMessageBox.StandardButton.Yes:
                self.label.setText(tr('Downloading and verifying the package…'))
                self.job('download', lambda: download_release(self.release))

    def on_completed(self, operation, result):
        self.busy = False
        self.button.setEnabled(True)
        if operation == 'check':
            self.release = result
            if result is None:
                self.label.setText(f"{tr('You are on the latest version (')}{__version__}).")
            else:
                self.label.setText(f"{tr('New version: ')}{result.version}\nDownload: {result.size / 1024 / 1024:.1f} MB")
                self.button.setText(tr('Download and install'))
                self.button.setToolTip(tr('Download and install'))
        else:
            self.package = Path(result)
            if not Path('/usr/bin/pkexec').exists() or not Path('/usr/bin/apt-get').exists():
                self.label.setText(tr('Verified package saved to:\n') + str(result) + tr('\nInstall it using the Ubuntu package manager.'))
                return
            self.busy = True
            self.button.setEnabled(False)
            self.label.setText(tr('Waiting for Ubuntu authorization and installation…'))
            self.process = QProcess(self)
            env = QProcessEnvironment()
            for key, value in system_environment().items():
                env.insert(key, value)
            self.process.setProcessEnvironment(env)
            self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            self.process.finished.connect(self.installed)
            self.process.errorOccurred.connect(self.process_error)
            self.process.start('/usr/bin/pkexec', ['/usr/bin/apt-get', 'install', '--yes', str(self.package)])

    def cleanup(self):
        if self.package is not None:
            shutil.rmtree(self.package.parent, ignore_errors=True)
            self.package = None

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.on_failed(tr('Could not start the Ubuntu installer.'))
            self.cleanup()

    def installed(self, code, status):
        self.busy = False
        self.button.setEnabled(True)
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.label.setText(tr('Update installed. Close and reopen ScreenDepresso to use the new version.\nSave your edits before closing.'))
            self.button.setEnabled(False)
        else:
            details = bytes(self.process.readAllStandardOutput()).decode(errors='replace')[-2000:]
            self.on_failed(tr('Installation was cancelled or failed. The current version remains available.\n') + details)
        self.cleanup()

    def on_failed(self, message):
        self.busy = False
        self.button.setEnabled(True)
        self.label.setText(tr('Could not complete the update. Check your connection and try again.'))
        QMessageBox.warning(self, tr('Update'), message)

    def reject(self):
        if not self.busy:
            super().reject()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)
