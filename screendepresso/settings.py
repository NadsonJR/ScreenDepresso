from .i18n import tr, mode_label
import json
import os
import re
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget, QKeySequenceEdit, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QLabel, QMessageBox, QComboBox
DEFAULT_HOTKEYS = {'tela': 'Ctrl+Shift+1', 'janela': 'Ctrl+Shift+2', 'região': 'Ctrl+Shift+3'}

def parse_hotkey(value):
    parts = value.split('+')
    modifiers, key = (parts[:-1], parts[-1])
    if len(set(modifiers)) != len(modifiers) or any((m not in ('Ctrl', 'Alt', 'Shift', 'Meta') for m in modifiers)):
        raise ValueError(tr('Use a combination with Ctrl, Alt, Shift or Meta.'))
    aliases = {'Esc': 'Escape', 'Space': 'space', 'Del': 'Delete', 'Ins': 'Insert', 'PgUp': 'Prior', 'PgDown': 'Next', 'Left': 'Left', 'Right': 'Right', 'Up': 'Up', 'Down': 'Down', 'Backspace': 'BackSpace', 'Print': 'Print', 'Tab': 'Tab', 'Home': 'Home', 'End': 'End', 'Return': 'Return'}
    if re.fullmatch('[A-Za-z0-9]|F(?:[1-9]|[12][0-9]|3[0-5])', key):
        keysym = key.lower() if len(key) == 1 else key
    elif key in aliases:
        keysym = aliases[key]
    else:
        raise ValueError(tr('Choose a letter, number, F1–F35, Print or a navigation key.'))
    return (tuple(sorted(modifiers)), keysym)

class Settings:

    def __init__(self, path=None):
        from .platform_support import config_path, data_directory
        self.path = Path(path) if path is not None else config_path()
        self.directory = str(data_directory())
        self.hotkeys = DEFAULT_HOTKEYS.copy()
        self.language = 'en'
        try:
            data = json.loads(self.path.read_text())
            shortcuts = data['hotkeys']
            if set(shortcuts) != set(DEFAULT_HOTKEYS) or len({parse_hotkey(v) for v in shortcuts.values()}) != 3:
                raise ValueError(tr('Invalid hotkeys'))
            if not isinstance(data['directory'], str) or not Path(data['directory']).is_absolute():
                raise ValueError(tr('Invalid directory'))
            self.directory, self.hotkeys = (data['directory'], shortcuts)
            self.language = data.get('language', 'en') if data.get('language', 'en') in ('en', 'pt_BR') else 'en'
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass

    def save(self, directory, hotkeys, language=None):
        language = self.language if language is None else language
        if language not in ('en', 'pt_BR'):
            raise ValueError(tr('Unsupported language'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump({'directory': directory, 'hotkeys': hotkeys, 'language': language}, stream, ensure_ascii=False)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.directory, self.hotkeys = (directory, hotkeys.copy())
        self.language = language

class SettingsDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.setWindowTitle(tr('Settings'))
        self.resize(550, 300)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self.tabs = tabs
        layout.addWidget(tabs)
        hotkeys_page = QWidget()
        form = QFormLayout(hotkeys_page)
        self.shortcuts = {}
        for mode, value in parent.settings.hotkeys.items():
            editor = QKeySequenceEdit(QKeySequence(value))
            editor.setToolTip(mode_label(mode))
            editor.setMaximumSequenceLength(1)
            self.shortcuts[mode] = editor
            form.addRow(mode_label(mode), editor)
        tabs.addTab(hotkeys_page, tr('Hotkeys'))
        files = QWidget()
        files_layout = QVBoxLayout(files)
        files_layout.addWidget(QLabel(tr('Directory for new captures and exports:')))
        row = QHBoxLayout()
        self.directory = QLineEdit(parent.settings.directory)
        self.directory.setToolTip(tr('Directory for new captures and exports:'))
        row.addWidget(self.directory)
        browse = QPushButton(tr('Browse…'))
        browse.setToolTip(tr('Capture directory'))
        browse.clicked.connect(self.browse)
        row.addWidget(browse)
        files_layout.addLayout(row)
        note = QLabel(tr('Existing files stay in the previous directory. History displays the selected directory.'))
        note.setWordWrap(True)
        files_layout.addWidget(note)
        tabs.addTab(files, tr('Files'))
        self.update_panel = parent.update_panel
        self.updates_index = tabs.addTab(self.update_panel, tr('Updates'))
        self.finished.connect(self.release_update_panel)
        language_page = QWidget()
        language_form = QFormLayout(language_page)
        self.language = QComboBox()
        self.language.setToolTip(tr('Interface language:'))
        self.language.addItem('English', 'en')
        self.language.addItem('Português (Brasil)', 'pt_BR')
        self.language.setCurrentIndex(self.language.findData(parent.settings.language))
        language_form.addRow(tr('Interface language:'), self.language)
        language_note = QLabel(tr('Language changes apply immediately when you save.'))
        language_note.setWordWrap(True)
        language_form.addRow(language_note)
        tabs.addTab(language_page, tr('Language'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Close)
        self.buttons = buttons
        for button in buttons.buttons():
            button.setToolTip(button.text().replace('&', ''))
        for index in range(tabs.count()):
            tabs.setTabToolTip(index, tabs.tabText(index))
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        tabs.currentChanged.connect(self.sync_buttons)
        self.sync_buttons(tabs.currentIndex())

    def check_updates(self):
        self.show_updates()
        self.update_panel.check_for_updates()

    def show_updates(self):
        self.tabs.setCurrentIndex(self.updates_index)

    def sync_buttons(self, index):
        updates = index == self.updates_index
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setVisible(not updates)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setVisible(not updates)
        self.buttons.button(QDialogButtonBox.StandardButton.Close).setVisible(updates)

    def release_update_panel(self, result):
        # The panel belongs to the application, so workers and ready downloads
        # survive closing Settings and can be shown again without starting over.
        if self.isAncestorOf(self.update_panel):
            self.tabs.removeTab(self.tabs.indexOf(self.update_panel))
            self.update_panel.setParent(self.owner)
            self.update_panel.hide()

    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, tr('Capture directory'), self.directory.text())
        if directory:
            self.directory.setText(directory)

    def save(self):
        try:
            hotkeys = {mode: editor.keySequence().toString(QKeySequence.SequenceFormat.PortableText) for mode, editor in self.shortcuts.items()}
            parsed = [parse_hotkey(value) for value in hotkeys.values()]
            if len(set(parsed)) != len(parsed):
                raise ValueError(tr('Each capture must have a different hotkey.'))
            directory = Path(self.directory.text().strip()).expanduser()
            if not directory.is_absolute():
                raise ValueError(tr('Enter an absolute directory path.'))
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=directory):
                pass
            self.owner.apply_settings(str(directory), hotkeys, self.language.currentData())
        except (ValueError, OSError, RuntimeError) as exc:
            QMessageBox.warning(self, tr('Settings'), str(exc))
            return
        self.accept()
