import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication, QToolBar, QTabWidget, QDialogButtonBox, QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from screendepresso.app import MainWindow
from screendepresso.settings import Settings, SettingsDialog, DEFAULT_HOTKEYS
from screendepresso.update_panel import UpdatePanel
from screendepresso.i18n import tr, set_language
from test_editor import image, drag

app = QApplication.instance() or QApplication([])


def test_english_default_and_live_portuguese_setting(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    monkeypatch.delenv('DISPLAY', raising=False)
    window = MainWindow()
    try:
        assert window.settings.language == 'en'
        ribbon = window.findChild(QToolBar, 'ribbon')
        assert 'Save' in [a.text() for a in ribbon.actions()]
        settings = SettingsDialog(window)
        assert 'Ctrl' in settings.shortcuts['tela'].findChild(QLineEdit).text()
        assert 'Shift' in settings.shortcuts['tela'].findChild(QLineEdit).text()
        tabs = settings.findChild(QTabWidget)
        assert [tabs.tabText(i) for i in range(tabs.count())] == ['Hotkeys', 'Files', 'Updates', 'Language']
        assert [settings.language.itemData(i) for i in range(settings.language.count())] == ['en', 'pt_BR']
        settings.language.setCurrentIndex(1)
        settings.save()
        assert window.settings.language == 'pt_BR'
        assert 'Salvar' in [a.text() for a in ribbon.actions()]
        assert 'Colar imagem' in [a.text() for a in ribbon.actions()]
        assert Settings().language == 'pt_BR'
        translated = SettingsDialog(window)
        assert translated.windowTitle() == 'Configurações'
        translated_tabs = translated.findChild(QTabWidget)
        assert translated_tabs.tabText(3) == 'Idioma'
        assert translated.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).text().replace('&', '') == 'Salvar'
        update = UpdatePanel(window)
        assert update.button.text() == 'Verificar atualizações'
        assert 'Versão instalada' in update.label.text()
        window.apply_settings(window.settings.directory, DEFAULT_HOTKEYS, 'en')
        assert 'Save' in [a.text() for a in ribbon.actions()]
        assert 'Paste image' in [a.text() for a in ribbon.actions()]
    finally:
        window.close()
        set_language('en')


def test_blur_slider_changes_selected_effect_and_clipboard_paste(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    monkeypatch.delenv('DISPLAY', raising=False)
    window = MainWindow()
    original = image()
    for x in range(original.width()):
        for y in range(original.height()):
            from PySide6.QtGui import QColor
            original.setPixelColor(x,y,QColor('black' if (x//8)%2 else 'white'))
    window.canvas.load(original)
    drag(window.canvas, 'desfoque')
    initial = window.canvas.image
    window.blur_slider.setValue(1)
    assert window.blur_strength.value() == 1
    assert window.canvas.objects[0]['radius'] == 1
    assert window.canvas.image != initial
    window.canvas.undo()
    assert window.canvas.image == initial
    window.show()
    window.activateWindow()
    app.processEvents()
    QApplication.clipboard().setImage(image().copy(0, 0, 30, 30))
    QTest.keyClick(window, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    assert window.canvas.objects[-1]['kind'] == 'imagem'
    window.close()
