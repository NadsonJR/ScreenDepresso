"""Automatic update check, verified download progress, install and explicit restart."""
import sys
import shutil
import threading
from pathlib import Path
from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QProgressBar
from . import __version__
from .i18n import tr
from .updater import (check_update, download_release, system_environment,
                      start_windows_installer, start_restarted_application)


class UpdateDialog(QDialog):
    completed = Signal(str, object)
    failed = Signal(str)
    progress = Signal(int, int)
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Update ScreenDepresso'))
        self.resize(460, 180)
        self.release = None
        self.package = None
        self.busy = False
        self.process = None
        self.phase = 'idle'
        layout = QVBoxLayout(self)
        self.label = QLabel(f"{tr('Installed version: ')}{__version__}\n{tr('Checking published versions on GitHub…')}")
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setToolTip(tr('Download progress'))
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        self.button = QPushButton(tr('Download and install'))
        self.button.setToolTip(tr('Download and install'))
        self.button.clicked.connect(self.perform)
        self.button.hide()
        layout.addWidget(self.button)
        self.completed.connect(self.on_completed)
        self.failed.connect(self.on_failed)
        self.progress.connect(self.on_progress)

    def job(self, operation, function):
        self.busy = True
        self.button.hide()

        def run():
            try:
                self.completed.emit(operation, function())
            except Exception as exc:
                self.failed.emit(str(exc))
        threading.Thread(target=run, daemon=True).start()

    def perform(self):
        if self.busy:
            return
        if self.phase in ('ready', 'installed'):
            self.restart()
        elif self.release is None:
            self.phase = 'checking'
            self.label.setText(f"{tr('Installed version: ')}{__version__}\n{tr('Checking published versions on GitHub…')}")
            self.job('check', lambda: check_update(__version__))
        else:
            notice = tr('Download and install version ') + self.release.version + tr('?\nSave your edits before restarting. Your captures will be preserved.')
            if QMessageBox.question(self, tr('Install update'), notice) != QMessageBox.StandardButton.Yes:
                return
            self.phase = 'downloading'
            self.label.setText(tr('Downloading and verifying the package…'))
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.job('download', lambda: download_release(self.release, self.progress.emit))

    def on_progress(self, received, total):
        self.progress_bar.setValue(min(100, received*100//total) if total else 0)

    def on_completed(self, operation, result):
        self.busy = False
        if operation == 'check':
            self.release = result
            if result is None:
                self.phase = 'latest'
                self.label.setText(f"{tr('You are on the latest version (')}{__version__}).")
                self.button.hide()
            else:
                self.phase = 'available'
                self.label.setText(f"{tr('New version: ')}{result.version}\nDownload: {result.size / 1024 / 1024:.1f} MB")
                self.button.setText(tr('Download and install'))
                self.button.setToolTip(tr('Download and install'))
                self.button.show()
            return
        self.package = Path(result)
        self.progress_bar.setValue(100)
        if sys.platform == 'win32':
            self.show_restart('ready')
            return
        self.install_linux()

    def install_linux(self):
        if not Path('/usr/bin/pkexec').exists() or not Path('/usr/bin/apt-get').exists():
            self.phase = 'manual'
            self.label.setText(tr('Verified package saved to:\n') + str(self.package) + tr('\nInstall it using the Ubuntu package manager.'))
            return
        self.phase = 'installing'
        self.busy = True
        self.button.hide()
        self.progress_bar.setRange(0, 0)
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

    def show_restart(self, phase):
        self.phase = phase
        self.busy = False
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.label.setText(tr('Download verified. Restart to install the update and reopen the application. Save your edits first.') if phase == 'ready' else tr('Update installed. Restart the application to use the new version. Save your edits first.'))
        self.button.setText(tr('Restart application'))
        self.button.setToolTip(tr('Restart application'))
        self.button.show()

    def restart(self):
        if QMessageBox.question(self, tr('Restart application'), tr('Restart now? Unsaved edits will be lost.')) != QMessageBox.StandardButton.Yes:
            return
        try:
            if sys.platform == 'win32':
                start_windows_installer(self.package, restart=True)
            else:
                start_restarted_application()
        except OSError as exc:
            self.label.setText(tr('Could not restart the application. Try again.')+'\n'+str(exc))
            return
        self.button.hide()
        self.busy = True
        self.quit_requested.emit()

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
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.show_restart('installed')
        else:
            details = bytes(self.process.readAllStandardOutput()).decode(errors='replace')[-2000:]
            self.on_failed(tr('Installation was cancelled or failed. The current version remains available.\n')+details)
        self.cleanup()

    def on_failed(self, message):
        self.busy = False
        self.phase = 'error'
        self.progress_bar.hide()
        self.label.setText(tr('Could not complete the update. Check your connection and try again.')+'\n'+message)
        self.button.setText(tr('Download and install'))
        self.button.setToolTip(tr('Download and install'))
        self.button.setVisible(self.release is not None)

    def reject(self):
        if not self.busy:
            if self.phase == 'ready':
                self.cleanup()
            super().reject()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            if self.phase == 'ready':
                self.cleanup()
            super().closeEvent(event)
