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
        self.setWindowTitle('Atualizar ScreenDepresso')
        self.resize(460, 180)
        self.release = None
        self.package = None
        self.busy = False
        self.process = None
        layout = QVBoxLayout(self)
        self.label = QLabel(f'Versão instalada: {__version__}\nUbuntu 24.04+ • x86_64 • X11')
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.button = QPushButton('Verificar atualizações')
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
            self.label.setText('Consultando versões publicadas no GitHub…')
            self.job('check', lambda: check_update(__version__))
        else:
            answer = QMessageBox.question(self, 'Instalar atualização',
                f'Baixar e instalar a versão {self.release.version}?\nO Ubuntu solicitará autorização de administrador. Suas capturas serão preservadas.')
            if answer == QMessageBox.StandardButton.Yes:
                self.label.setText('Baixando e verificando o pacote…')
                self.job('download', lambda: download_release(self.release))

    def on_completed(self, operation, result):
        self.busy = False
        self.button.setEnabled(True)
        if operation == 'check':
            self.release = result
            if result is None:
                self.label.setText(f'Você está na versão mais recente ({__version__}).')
            else:
                self.label.setText(f'Nova versão: {result.version}\nDownload: {result.size / 1024 / 1024:.1f} MB')
                self.button.setText('Baixar e instalar')
        else:
            self.package = Path(result)
            if not Path('/usr/bin/pkexec').exists() or not Path('/usr/bin/apt-get').exists():
                self.label.setText(f'Pacote verificado salvo em:\n{result}\nInstale pelo gerenciador de pacotes do Ubuntu.')
                return
            self.busy = True
            self.button.setEnabled(False)
            self.label.setText('Aguardando autorização e instalação pelo Ubuntu…')
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
            self.on_failed('Não foi possível iniciar o instalador do Ubuntu.')
            self.cleanup()

    def installed(self, code, status):
        self.busy = False
        self.button.setEnabled(True)
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.label.setText('Atualização instalada. Feche e abra o ScreenDepresso para usar a nova versão.\nSalve suas edições antes de fechar.')
            self.button.setEnabled(False)
        else:
            details = bytes(self.process.readAllStandardOutput()).decode(errors='replace')[-2000:]
            self.on_failed('Instalação cancelada ou malsucedida. A versão atual continua disponível.\n' + details)
        self.cleanup()

    def on_failed(self, message):
        self.busy = False
        self.button.setEnabled(True)
        self.label.setText('Não foi possível concluir a atualização. Verifique a conexão e tente novamente.')
        QMessageBox.warning(self, 'Atualização', message)

    def reject(self):
        if not self.busy:
            super().reject()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)
