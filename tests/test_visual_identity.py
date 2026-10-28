import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import pytest
from PySide6.QtCore import Qt, QPointF, QMimeData, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QFileDialog
from screendepresso.app import MainWindow
from screendepresso.i18n import set_language, CATALOG
from screendepresso.presentation import TOOL_NAMES
from screendepresso.theme import TOKENS, stylesheet
from test_editor import image, gesture

app = QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    w = MainWindow()
    w.resize(1280,800)
    w.show()
    app.processEvents()
    yield w
    w.request_quit()
    set_language('en')


def test_empty_state_opens_images_reuses_tabs_and_accepts_drops(window, tmp_path, monkeypatch):
    empty = window.scroll.empty_state
    assert empty.isVisible() and not window.tabs.tabBar().isVisible()
    assert len(empty.buttons) == 3
    path = tmp_path/'input.png'
    image().save(str(path))
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(path), ''))
    empty.buttons[1].click()
    assert window.canvas.image == image() and empty.isHidden()
    assert window.tabs.currentWidget().source_path == path
    window.open_image_file()
    assert window.tabs.count() == 1
    window.close_tab(0)
    empty = window.scroll.empty_state
    assert empty.isVisible()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    assert window.canvas.drop_mime(mime, QPointF(0,0))
    assert empty.isHidden() and window.canvas.image == image()


def test_empty_state_buttons_use_existing_capture_and_clipboard_commands(window, monkeypatch):
    empty = window.scroll.empty_state
    captures = []
    monkeypatch.setattr(window, 'capture', lambda mode: captures.append(mode))
    empty.buttons[0].click()
    assert captures == ['tela']
    QApplication.clipboard().setImage(image())
    empty.buttons[2].click()
    assert window.canvas.image == image() and empty.isHidden()


def test_context_properties_edit_existing_rectangle_and_support_undo(window):
    window.tabs.open_image(image())
    window.choose_tool('retângulo')
    gesture(window.canvas, (20,20), (100,80))
    window.choose_tool('selecionar')
    bar = window.context_bar
    assert bar.title.text() == 'Rectangle'
    bar.rectangle_width.setValue(9)
    bar.rounded.setChecked(True)
    bar.radius.setValue(18)
    obj = window.canvas.objects[0]
    assert (obj['width'], obj['rounded'], obj['radius']) == (9, True, 18)
    window.canvas.undo()
    assert window.canvas.objects[0]['radius'] == 12
    assert window.canvas.tool == 'selecionar'
    window.canvas.redo()
    assert window.canvas.objects[0]['radius'] == 18


def test_context_properties_follow_current_tab_without_mutating_other_document(window):
    window.tabs.open_image(image())
    window.choose_tool('texto')
    window.context_bar.font_size.setValue(40)
    first = window.canvas
    window.tabs.open_image(image())
    second = window.canvas
    window.choose_tool('desfoque')
    window.context_bar.blur_strength.setValue(30)
    window.context_bar.blur_mode.setCurrentIndex(1)
    assert second.blur_radius == 30 and second.blur_mode == 'sequential'
    window.tabs.setCurrentIndex(0)
    assert window.canvas is first and first.text_format['font_size'] == 40
    assert window.context_bar.title.text() == 'Text'
    assert window.context_bar.font_size.value() == 40
    assert second.text_format['font_size'] == 24
    window.choose_tool('seta')
    window.context_bar.arrow_style.setCurrentIndex(4)
    assert first.arrow_style == 'line' and second.arrow_style == 'classic'


@pytest.mark.parametrize('width,height', [(1280,800), (820,620)])
def test_responsive_layout_preserves_actions_and_document_pixels(window,width,height):
    window.tabs.open_image(image())
    pixels = window.canvas.image.copy()
    window.resize(width,height)
    app.processEvents()
    assert window.canvas.image == pixels
    assert window.scroll.viewport().width() >= 300
    if width < 900:
        assert window.ribbon.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
        assert window.tools.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
    else:
        for action in window.tool_actions.values():
            button = window.tools.widgetForAction(action)
            assert button.fontMetrics().horizontalAdvance(action.iconText()) < button.width()-56
    window.choose_tool('texto')
    app.processEvents()
    assert window.context_bar.horizontalScrollBar().maximum() >= 0
    assert window.version_label.isVisible()


def test_new_controls_translate_without_translating_document_text(window):
    empty = window.scroll.empty_state
    set_language('pt_BR')
    assert empty.title.text() == 'Arraste uma imagem aqui'
    assert empty.buttons[1].text() == 'Abrir imagem'
    assert window.tool_actions['texto'].iconText() == 'Texto'
    assert window.tool_actions['numero'].iconText() == 'Números'
    window.choose_tool('desfoque')
    assert window.context_bar.title.text() == 'Desfoque'
    assert window.context_bar.blur_mode.itemText(0) == 'Camada única de desfoque'
    assert not set(TOOL_NAMES.values())-CATALOG.keys()


def test_identity_text_and_active_buttons_have_aa_contrast():
    def luminance(hex_color):
        rgb = QColor(hex_color).getRgbF()[:3]
        values = [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*c for v,c in zip(values, (.2126,.7152,.0722)))
    def contrast(a,b):
        light,dark=sorted((luminance(a),luminance(b)),reverse=True)
        return (light+.05)/(dark+.05)
    for foreground,background in [('text','surface'),('secondary','canvas'),('text','accent_active')]:
        assert contrast(TOKENS[foreground],TOKENS[background]) >= 4.5
    assert '@' not in stylesheet()
