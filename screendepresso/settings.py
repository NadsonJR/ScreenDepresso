import json
import os
import re
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QKeySequenceEdit, QLineEdit, QPushButton, QFileDialog,
    QDialogButtonBox, QLabel, QMessageBox)

DEFAULT_HOTKEYS = {'tela': 'Ctrl+Shift+1', 'janela': 'Ctrl+Shift+2', 'região': 'Ctrl+Shift+3'}


def parse_hotkey(value):
    parts = value.split('+')
    modifiers, key = parts[:-1], parts[-1]
    if len(set(modifiers)) != len(modifiers) or any(m not in ('Ctrl', 'Alt', 'Shift', 'Meta') for m in modifiers):
        raise ValueError('Use uma combinação com Ctrl, Alt, Shift ou Meta.')
    aliases = {'Esc': 'Escape', 'Space': 'space', 'Del': 'Delete', 'Ins': 'Insert', 'PgUp': 'Prior', 'PgDown': 'Next', 'Left': 'Left', 'Right': 'Right', 'Up': 'Up', 'Down': 'Down', 'Backspace': 'BackSpace', 'Print': 'Print', 'Tab': 'Tab', 'Home': 'Home', 'End': 'End', 'Return': 'Return'}
    if re.fullmatch(r'[A-Za-z0-9]|F(?:[1-9]|[12][0-9]|3[0-5])', key):
        keysym = key.lower() if len(key) == 1 else key
    elif key in aliases:
        keysym = aliases[key]
    else:
        raise ValueError('Escolha letra, número, F1–F35, Print ou uma tecla de navegação.')
    return tuple(sorted(modifiers)), keysym


class Settings:
    def __init__(self, path=None):
        self.path = Path(path or Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'screendepresso/settings.json')
        self.directory = str(Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'screendepresso')
        self.hotkeys = DEFAULT_HOTKEYS.copy()
        try:
            data = json.loads(self.path.read_text())
            shortcuts = data['hotkeys']
            if set(shortcuts) != set(DEFAULT_HOTKEYS) or len({parse_hotkey(v) for v in shortcuts.values()}) != 3:
                raise ValueError('Atalhos inválidos')
            if not isinstance(data['directory'], str) or not Path(data['directory']).is_absolute():
                raise ValueError('Diretório inválido')
            self.directory, self.hotkeys = data['directory'], shortcuts
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass

    def save(self, directory, hotkeys):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump({'directory': directory, 'hotkeys': hotkeys}, stream, ensure_ascii=False)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.directory, self.hotkeys = directory, hotkeys.copy()


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.setWindowTitle('Configurações')
        self.resize(550, 300)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        hotkeys_page = QWidget()
        form = QFormLayout(hotkeys_page)
        self.shortcuts = {}
        for mode, value in parent.settings.hotkeys.items():
            editor = QKeySequenceEdit(QKeySequence(value))
            editor.setMaximumSequenceLength(1)
            self.shortcuts[mode] = editor
            form.addRow(mode.capitalize(), editor)
        tabs.addTab(hotkeys_page, 'Hotkeys')
        files = QWidget()
        files_layout = QVBoxLayout(files)
        files_layout.addWidget(QLabel('Diretório para novas capturas e exportações:'))
        row = QHBoxLayout()
        self.directory = QLineEdit(parent.settings.directory)
        row.addWidget(self.directory)
        browse = QPushButton('Escolher…')
        browse.clicked.connect(self.browse)
        row.addWidget(browse)
        files_layout.addLayout(row)
        note = QLabel('Arquivos existentes permanecem no diretório anterior. O histórico mostra o diretório escolhido.')
        note.setWordWrap(True)
        files_layout.addWidget(note)
        tabs.addTab(files, 'Arquivos')
        updates = QWidget()
        update_layout = QVBoxLayout(updates)
        button = QPushButton('Verificar atualizações')
        button.clicked.connect(self.check_updates)
        update_layout.addWidget(button)
        tabs.addTab(updates, 'Atualizações')
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def check_updates(self):
        from .update_dialog import UpdateDialog
        dialog = UpdateDialog(self)
        dialog.perform()
        dialog.exec()

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, 'Diretório das capturas', self.directory.text())
        if directory:
            self.directory.setText(directory)

    def save(self):
        try:
            hotkeys = {mode: editor.keySequence().toString(QKeySequence.SequenceFormat.PortableText) for mode, editor in self.shortcuts.items()}
            parsed = [parse_hotkey(value) for value in hotkeys.values()]
            if len(set(parsed)) != len(parsed):
                raise ValueError('Cada captura deve ter um atalho diferente.')
            directory = Path(self.directory.text().strip()).expanduser()
            if not directory.is_absolute():
                raise ValueError('Informe um diretório absoluto.')
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=directory):
                pass
            self.owner.apply_settings(str(directory), hotkeys)
        except (ValueError, OSError, RuntimeError) as exc:
            QMessageBox.warning(self, 'Configurações', str(exc))
            return
        self.accept()
