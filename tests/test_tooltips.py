import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import QEvent
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication, QToolBar, QToolTip
from screendepresso.app import MainWindow
from screendepresso.settings import SettingsDialog
from screendepresso.i18n import set_language

app = QApplication.instance() or QApplication([])


def test_hover_descriptions_and_shortcuts_are_visible_and_translated(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    monkeypatch.delenv('DISPLAY', raising=False)
    window = MainWindow()
    try:
        window.show()
        app.processEvents()
        ribbon = window.findChild(QToolBar, 'ribbon')
        tools = window.findChild(QToolBar, 'tools')
        for bar in (ribbon, tools):
            for action in bar.actions():
                if not action.isSeparator():
                    assert action.toolTip()
        save = next(a for a in ribbon.actions() if a.text() == 'Save')
        assert save.toolTip() == 'Save (Ctrl+S)'
        button = tools.widgetForAction(window.tool_actions['numero'])
        position = button.rect().center()
        app.sendEvent(button, QHelpEvent(QEvent.Type.ToolTip, position, button.mapToGlobal(position)))
        assert QToolTip.text() == 'Numbered markers'
        QToolTip.hideText()
        window.apply_settings(window.settings.directory, window.settings.hotkeys, 'pt_BR')
        assert save.toolTip() == 'Salvar (Ctrl+S)'
        assert window.blur_strength.toolTip() == 'Intensidade do desfoque (1–100)'
        assert window.tool_actions['numero'].toolTip() == 'Marcadores numerados'
        settings = SettingsDialog(window)
        assert settings.directory.toolTip() == 'Diretório para novas capturas e exportações:'
        assert settings.language.toolTip() == 'Idioma da interface:'
        menu = window.menuBar()
        action = menu.actions()[0]
        position = menu.actionGeometry(action).center()
        app.sendEvent(menu, QHelpEvent(QEvent.Type.ToolTip, position, menu.mapToGlobal(position)))
        assert QToolTip.text() == 'Configurações…'
    finally:
        QToolTip.hideText()
        window.close()
        set_language('en')
