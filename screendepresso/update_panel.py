"""Persistent inline update flow embedded in the Settings updates tab."""
import sys
import shutil
import threading
from pathlib import Path
from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QStackedWidget, QSizePolicy
from . import __version__
from .i18n import tr, format_number
from .updater import (check_update, download_release, system_environment,
                      start_windows_installer, start_restarted_application)


class UpdatePanel(QWidget):
    completed = Signal(str, object)
    failed = Signal(str)
    progress = Signal(int, int)
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('updatesPanel')
        self.release = None
        self.package = None
        self.busy = False
        self.process = None
        self.phase = 'idle'
        self.error_message = ''
        self.received = self.total = 0
        self.installer_started = False
        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setWordWrap(True)
        self.label.setMinimumHeight(60)
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        actions = QHBoxLayout()
        self.action_stack = QStackedWidget()
        self.action_stack.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.button = QPushButton()
        self.button.setMinimumWidth(210)
        self.button.clicked.connect(self.perform)
        self.loader = QProgressBar()
        self.loader.setRange(0, 0)
        self.loader.setTextVisible(False)
        self.loader.setMinimumWidth(210)
        self.action_stack.addWidget(self.button)
        self.action_stack.addWidget(self.loader)
        actions.addWidget(self.action_stack)
        self.keep_button = QPushButton()
        self.keep_button.clicked.connect(self.keep_current)
        actions.addWidget(self.keep_button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        self.completed.connect(self.on_completed)
        self.failed.connect(self.on_failed)
        self.progress.connect(self.on_progress)
        self.render()

    def render(self):
        installed = f"{tr('Installed version: ')}{__version__}"
        if self.phase == 'checking':
            text = installed+'\n'+tr('Checking published versions on GitHub…')
        elif self.phase == 'latest':
            text = f"{tr('You are on the latest version (')}{__version__})."
        elif self.phase == 'kept':
            text = tr('Keeping the current version: ')+__version__
        elif self.phase == 'available':
            text = installed+'\n'+tr('New version: ')+self.release.version+' • '+format_number(self.release.size / 1024 / 1024)+' MB'
        elif self.phase == 'downloading':
            text = tr('Downloading and verifying the package…')
        elif self.phase == 'installing':
            text = tr('Waiting for Ubuntu authorization and installation…')
        elif self.phase == 'ready':
            text = tr('Download verified. Restart to install the update and reopen the application. Save your edits first.')
        elif self.phase == 'installed':
            text = tr('Update installed. Restart the application to use the new version. Save your edits first.')
        elif self.phase == 'manual':
            text = tr('Verified package saved to:\n')+str(self.package)+tr('\nInstall it using the Ubuntu package manager.')
        elif self.phase == 'restarting':
            text = tr('Restarting the application…')
        elif self.phase == 'error':
            text = tr('Could not complete the update. Check your connection and try again.')
        else:
            text = installed
        self.label.setText(text+('\n'+tr(self.error_message) if self.error_message else ''))
        primary = ('Restart application' if self.phase in ('ready', 'installed') else
                   'Download and install' if self.release is not None and self.phase in ('available', 'error') else
                   'Check for updates')
        self.button.setText(tr(primary))
        self.button.setToolTip(tr(primary))
        self.keep_button.setText(tr('Keep current version'))
        self.keep_button.setToolTip(tr('Keep current version'))
        self.keep_button.setVisible(self.release is not None and self.phase in ('available', 'error'))
        self.action_stack.setVisible(not self.busy or self.phase == 'checking')
        self.action_stack.setCurrentWidget(self.loader if self.phase == 'checking' else self.button)
        self.loader.setToolTip(tr('Checking published versions on GitHub…'))
        self.progress_bar.setToolTip(tr('Download progress'))
        self.progress_bar.setVisible(self.phase in ('downloading', 'installing', 'ready', 'installed', 'restarting'))
        self.progress_bar.setRange(0, 0 if self.phase == 'installing' else 100)
        if self.phase in ('ready', 'installed', 'restarting'):
            self.progress_bar.setValue(100)
        elif self.phase == 'downloading':
            self.progress_bar.setValue(self.received*100//self.total if self.total else 0)

    def job(self, operation, function):
        self.busy = True
        self.render()
        def run():
            try:
                self.completed.emit(operation, function())
            except Exception as exc:
                self.failed.emit(str(exc))
        threading.Thread(target=run, daemon=True).start()

    def check_for_updates(self):
        if self.busy or self.phase in ('ready', 'installed'):
            return
        self.release = None
        self.error_message = ''
        self.phase = 'checking'
        self.job('check', lambda: check_update(__version__))

    def perform(self):
        if self.busy:
            return
        if self.phase in ('ready', 'installed'):
            self.restart()
        elif self.release is not None and self.phase in ('available', 'error'):
            self.phase = 'downloading'
            self.error_message = ''
            self.received, self.total = 0, self.release.size
            self.job('download', lambda: download_release(self.release, self.progress.emit))
        else:
            self.check_for_updates()

    def keep_current(self):
        if self.busy or self.phase not in ('available', 'error') or self.release is None:
            return
        self.release = None
        self.phase = 'kept'
        self.error_message = ''
        self.render()

    def on_progress(self, received, total):
        self.received, self.total = received, total
        self.progress_bar.setValue(min(100, received*100//total) if total else 0)

    def on_completed(self, operation, result):
        self.busy = False
        if operation == 'check':
            self.release = result
            self.phase = 'available' if result is not None else 'latest'
            self.render()
            return
        self.package = Path(result)
        if sys.platform == 'win32':
            self.show_restart('ready')
        else:
            self.install_linux()

    def install_linux(self):
        if not Path('/usr/bin/pkexec').exists() or not Path('/usr/bin/apt-get').exists():
            self.phase = 'manual'
            self.render()
            return
        self.phase = 'installing'
        self.busy = True
        self.render()
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
        self.error_message = ''
        self.render()

    def restart(self):
        try:
            if sys.platform == 'win32':
                start_windows_installer(self.package, restart=True)
                self.installer_started = True
            else:
                start_restarted_application()
        except OSError as exc:
            self.error_message = tr('Could not restart the application. Try again.')+'\n'+str(exc)
            self.render()
            return
        self.phase = 'restarting'
        self.busy = True
        self.render()
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
        self.error_message = message
        self.render()

    def shutdown(self):
        if not self.installer_started and self.phase != 'manual':
            self.cleanup()
