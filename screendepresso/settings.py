from .i18n import tr, mode_label
import json
import locale
import os
import re
import tempfile
from pathlib import Path
from .workspace import WORKSPACE_LIMITS
from .recorder import FRAME_RATES, QUALITIES, COUNTDOWNS, default_recording, normalize_recording
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget, QKeySequenceEdit, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QLabel, QMessageBox, QComboBox, QCheckBox
DEFAULT_HOTKEYS = {'tela': 'Ctrl+Shift+1', 'janela': 'Ctrl+Shift+2', 'região': 'Ctrl+Shift+3', 'gravação': 'Ctrl+Alt+R'}

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


RECORDING_HOTKEYS = ('Ctrl+Alt+R', 'Ctrl+Shift+R', 'Ctrl+Alt+Shift+R', 'Ctrl+Alt+F9', 'Ctrl+Alt+Shift+F9')


def recording_hotkey(used):
    """Pick the recording hotkey for older settings without clashing with the
    capture keys already chosen there."""
    taken = set()
    for value in used:
        try:
            taken.add(parse_hotkey(value))
        except (ValueError, AttributeError):
            pass
    return next((value for value in RECORDING_HOTKEYS if parse_hotkey(value) not in taken), RECORDING_HOTKEYS[0])

class Settings:

    def __init__(self, path=None):
        from .platform_support import config_path, data_directory
        self.path = Path(path) if path is not None else config_path()
        self.directory = str(data_directory())
        self.hotkeys = DEFAULT_HOTKEYS.copy()
        self.language = 'en'
        self.workspace_limit = 25
        self.recording = default_recording()
        try:
            try:
                content = self.path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Preserve settings written by older Windows versions using
                # the local ANSI code page; all new writes use UTF-8.
                content = self.path.read_text(encoding=locale.getpreferredencoding(False))
            data = json.loads(content)
            shortcuts = data['hotkeys']
            self.recording = normalize_recording(data.get('recording'))
            if isinstance(shortcuts, dict) and 'gravação' not in shortcuts:
                # Settings written before screen recording: keep the capture keys.
                shortcuts = dict(shortcuts, gravação=recording_hotkey(shortcuts.values()))
            if set(shortcuts) != set(DEFAULT_HOTKEYS) or len({parse_hotkey(v) for v in shortcuts.values()}) != len(DEFAULT_HOTKEYS):
                raise ValueError(tr('Invalid hotkeys'))
            if not isinstance(data['directory'], str) or not Path(data['directory']).is_absolute():
                raise ValueError(tr('Invalid directory'))
            self.directory, self.hotkeys = (data['directory'], shortcuts)
            self.language = data.get('language', 'en') if data.get('language', 'en') in ('en', 'pt_BR') else 'en'
            limit = data.get('workspace_limit', 25)
            self.workspace_limit = limit if type(limit) is int and limit in WORKSPACE_LIMITS else 25
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass

    def save(self, directory, hotkeys, language=None, workspace_limit=None, recording=None):
        recording = normalize_recording(self.recording if recording is None else recording)
        language = self.language if language is None else language
        if language not in ('en', 'pt_BR'):
            raise ValueError(tr('Unsupported language'))
        workspace_limit = self.workspace_limit if workspace_limit is None else workspace_limit
        if type(workspace_limit) is not int or workspace_limit not in WORKSPACE_LIMITS:
            raise ValueError(tr('Invalid workspace limit.'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'directory': directory, 'hotkeys': hotkeys, 'language': language, 'workspace_limit': workspace_limit, 'recording': recording}, stream, ensure_ascii=False)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.directory, self.hotkeys = (directory, hotkeys.copy())
        self.language = language
        self.workspace_limit = workspace_limit
        self.recording = recording

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
        self.workspace_limit = QComboBox()
        self.workspace_limit.setProperty('translateItems', True)
        self.workspace_limit.setToolTip(tr('Maximum images in workspace:'))
        for limit in WORKSPACE_LIMITS:
            self.workspace_limit.addItem(str(limit) if limit else tr('No limit'), limit)
        self.workspace_limit.setCurrentIndex(self.workspace_limit.findData(parent.settings.workspace_limit))
        limit_row = QFormLayout()
        limit_row.addRow(tr('Maximum images in workspace:'), self.workspace_limit)
        files_layout.addLayout(limit_row)
        retention = QLabel(tr('When saving images or applying a new limit, the oldest images are moved to the system trash. Subfolders are not changed.'))
        retention.setWordWrap(True)
        files_layout.addWidget(retention)
        note = QLabel(tr('Existing files stay in the previous directory. Workspace shows the selected directory.'))
        note.setWordWrap(True)
        files_layout.addWidget(note)
        tabs.addTab(files, tr('Files'))
        self.update_panel = parent.update_panel
        self.updates_index = tabs.addTab(self.update_panel, tr('Updates'))
        self.finished.connect(self.release_update_panel)
        tabs.addTab(self.recording_page(parent.settings.recording), tr('Recording'))
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

    def recording_page(self, options):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.recording_fps = QComboBox()
        self.recording_fps.setToolTip(tr('Frames per second:'))
        for fps in FRAME_RATES:
            self.recording_fps.addItem(f'{fps} fps', fps)
        self.recording_fps.setCurrentIndex(self.recording_fps.findData(options['fps']))
        form.addRow(tr('Frames per second:'), self.recording_fps)
        self.recording_quality = QComboBox()
        self.recording_quality.setProperty('translateItems', True)
        self.recording_quality.setToolTip(tr('Video quality:'))
        for key, label in QUALITIES.items():
            self.recording_quality.addItem(tr(label), key)
        self.recording_quality.setCurrentIndex(self.recording_quality.findData(options['quality']))
        form.addRow(tr('Video quality:'), self.recording_quality)
        self.recording_countdown = QComboBox()
        self.recording_countdown.setToolTip(tr('Countdown before recording:'))
        for seconds in COUNTDOWNS:
            self.recording_countdown.addItem(tr('{seconds} seconds').format(seconds=seconds) if seconds else tr('Off'), seconds)
        self.recording_countdown.setCurrentIndex(self.recording_countdown.findData(options['countdown']))
        form.addRow(tr('Countdown before recording:'), self.recording_countdown)
        self.recording_microphone = QCheckBox(tr('Record microphone audio'))
        self.recording_microphone.setToolTip(tr('Record microphone audio'))
        self.recording_microphone.setChecked(options['microphone'])
        form.addRow(self.recording_microphone)
        self.recording_device = QComboBox()
        self.recording_device.setToolTip(tr('Microphone:'))
        self.recording_device.addItem(tr('System default'), '')
        try:
            from .recorder import microphones
            for name, key in microphones():
                self.recording_device.addItem(name, key)
        except Exception:
            pass
        self.recording_device.setCurrentIndex(max(0, self.recording_device.findData(options['microphone_device'])))
        self.recording_device.setEnabled(options['microphone'])
        self.recording_microphone.toggled.connect(self.recording_device.setEnabled)
        form.addRow(tr('Microphone:'), self.recording_device)
        layout.addLayout(form)
        note = QLabel(tr("Recordings are saved in the workspace as MP4: H.264 when the system provides an encoder, otherwise MPEG-4. Lower frame rates and quality use less CPU and disk."))
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return page

    def recording_options(self):
        return {'fps': self.recording_fps.currentData(),
                'quality': self.recording_quality.currentData(), 'countdown': self.recording_countdown.currentData(),
                'microphone': self.recording_microphone.isChecked(), 'microphone_device': self.recording_device.currentData()}

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
        directory = QFileDialog.getExistingDirectory(self, tr('Capture directory'), self.directory.text(), QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontUseNativeDialog)
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
            self.owner.apply_settings(str(directory), hotkeys, self.language.currentData(), self.workspace_limit.currentData(),
                                      self.recording_options())
        except (ValueError, OSError, RuntimeError) as exc:
            QMessageBox.warning(self, tr('Settings'), str(exc))
            return
        self.accept()
