"""Explicit close choices; keeping the application running is never implicit."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from .i18n import tr


class CloseDialog(QDialog):
    def __init__(self, parent, tray_available):
        super().__init__(parent)
        self.setWindowTitle(tr('Close ScreenDepresso'))
        self.choice = 'cancel'
        layout = QVBoxLayout(self)
        question = QLabel(tr('Keep ScreenDepresso running in the background or quit?'))
        question.setWordWrap(True)
        layout.addWidget(question)
        note = QLabel(tr('Minimizing keeps your image and capture hotkeys available. Save your edits before quitting.'))
        note.setWordWrap(True)
        layout.addWidget(note)
        if not tray_available:
            fallback = QLabel(tr('The system tray is unavailable. The window will remain minimized in the taskbar.'))
            fallback.setWordWrap(True)
            layout.addWidget(fallback)
        buttons = QDialogButtonBox()
        self.minimize_button = buttons.addButton(tr('Minimize to tray') if tray_available else tr('Minimize to taskbar'), QDialogButtonBox.ButtonRole.ActionRole)
        self.quit_button = buttons.addButton(tr('Quit'), QDialogButtonBox.ButtonRole.DestructiveRole)
        self.cancel_button = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        for button in buttons.buttons():
            button.setToolTip(button.text().replace('&', ''))
        self.minimize_button.clicked.connect(lambda: self.finish('minimize'))
        self.quit_button.clicked.connect(lambda: self.finish('quit'))
        self.cancel_button.clicked.connect(self.reject)
        self.minimize_button.setDefault(True)
        layout.addWidget(buttons)

    def finish(self, choice):
        self.choice = choice
        self.accept()
