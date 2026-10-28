import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFontDatabase, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolBar

from screendepresso.annotations import BUBBLE_STYLES, text_document
from screendepresso.app import MainWindow
from screendepresso.editor import Canvas
from screendepresso.i18n import set_language
from test_editor import gesture, image

app = QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    window = MainWindow()
    window.show()
    app.processEvents()
    yield window
    window.request_quit()
    set_language('en')


def test_no_visible_tabs_without_an_image(window):
    assert not window.tabs.tabBar().isVisible()
    assert not window.zoom_slider.isEnabled()
    window.finish_capture(image())
    assert window.tabs.tabBar().isVisible()
    assert window.zoom_slider.isEnabled()
    window.close_tab(0)
    assert not window.tabs.tabBar().isVisible()
    assert not window.zoom_slider.isEnabled()
    app.clipboard().setImage(image())
    window.paste()
    assert window.tabs.tabBar().isVisible()


@pytest.mark.parametrize('style', BUBBLE_STYLES)
def test_balloon_preview_export_edit_tail_and_undo(style):
    canvas = Canvas()
    canvas.load(image())
    canvas.set_bubble_format(style=style, fill='#00ff00', outline='#0000ff')
    canvas.tool = 'balao'
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    QTest.mouseMove(canvas, QPoint(110, 70))
    preview = canvas.render_image(True)
    assert preview != image()
    assert preview.pixelColor(65, 45) == QColor('#00ff00')
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(110, 70))
    assert canvas.image == preview
    assert canvas.objects[0]['style'] == style
    old_tail = canvas.objects[0]['tail'][:]
    gesture(canvas, old_tail, (135, 110))
    assert canvas.objects[0]['tail'] == [135, 110]
    canvas.undo()
    assert canvas.objects[0]['tail'] == old_tail
    canvas.redo()
    assert canvas.objects[0]['tail'] == [135, 110]
    gesture(canvas, (65, 45), (65, 45))
    canvas.set_bubble_format(fill='#ffff00')
    assert canvas.image.pixelColor(65, 45) == QColor('#ffff00')
    canvas.undo()
    assert canvas.image.pixelColor(65, 45) == QColor('#00ff00')


def test_balloon_controls_live_on_its_tool_button(window):
    window.finish_capture(image())
    tools = window.findChild(QToolBar, 'tools')
    assert tools.widgetForAction(window.tool_actions['balao']).menu() is window.bubble_menu
    for style in BUBBLE_STYLES:
        window.bubble_styles[style].trigger()
        assert window.canvas.bubble_format['style'] == style
        assert window.canvas.tool == 'balao'
    gesture(window.canvas, (20, 20), (110, 70))
    window.bubble_styles['rounded'].trigger()
    assert window.canvas.objects[0]['style'] == 'rounded'
    set_language('pt_BR')
    assert window.tool_actions['balao'].text() == 'Balão de fala'
    assert window.bubble_styles['thought'].text() == 'Pensamento'


def test_undo_selected_balloon_creation_resets_controls(window):
    window.finish_capture(image())
    window.bubble_styles['rounded'].trigger()
    gesture(window.canvas, (20, 20), (110, 70))
    window.canvas.undo()
    assert not window.canvas.objects
    assert window.canvas.selected is None
    assert window.bubble_styles['rounded'].isChecked()
    window.canvas.redo()
    assert window.canvas.objects[0]['style'] == 'rounded'


def test_zoom_keeps_export_pixels_and_maps_mouse_coordinates(window):
    window.finish_capture(image())
    canvas = window.canvas
    window.zoom_slider.setValue(200)
    assert canvas.width() == 320 and canvas.height() == 240
    assert window.zoom_label.text() == '200%'
    window.choose_tool('retângulo')
    gesture(canvas, (40, 40), (200, 160))
    assert canvas.objects[0]['a'] == [20, 20]
    assert canvas.objects[0]['b'] == [100, 80]
    exported = canvas.image
    assert exported.size() == image().size()
    window.zoom_slider.setValue(50)
    assert canvas.size().width() == 80
    assert canvas.image == exported
    window.finish_capture(image())
    assert window.zoom_slider.value() == 100
    window.tabs.setCurrentIndex(0)
    assert window.zoom_slider.value() == 50
    canvas.undo()
    assert canvas.image == image() and canvas.width() == 80


def test_font_size_color_edit_existing_text_and_undo():
    canvas = Canvas()
    canvas.load(image())
    family = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
    canvas.set_text_format(font_family=family, font_size=18, color='#0000ff')
    canvas.tool = 'texto'
    gesture(canvas, (10, 10), (150, 90))
    canvas.text_editor.setPlainText('Hello')
    canvas.finish_text()
    obj = canvas.objects[0]
    assert obj['font_family'] == family and obj['font_size'] == 18 and obj['color'] == '#0000ff'
    before = canvas.image
    canvas.set_text_format(font_size=30, color='#008000')
    assert canvas.objects[0]['font_size'] == 30
    assert canvas.image != before
    canvas.undo()
    assert canvas.objects[0]['font_size'] == 18 and canvas.image == before
    canvas.redo()
    assert canvas.objects[0]['font_size'] == 30


def test_long_multiline_text_grows_box_and_canvas_without_clipping():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'texto'
    gesture(canvas, (120, 90), (150, 110))
    content = '\n'.join(f'Visible line {i}' for i in range(15))
    canvas.text_editor.setPlainText(content)
    canvas.set_text_format(font_size=32)
    assert canvas.text_editor.height() > 120
    canvas.finish_text()
    obj = canvas.objects[0]
    rect = canvas.object_rect(obj)
    assert rect.height() >= text_document(obj, rect.width()).size().height()
    assert canvas.base.rect().contains(rect)
    assert canvas.base.height() > 120
    result = canvas.image
    assert result.copy(0, result.height()-45, result.width(), 45) != canvas.base.copy(0, result.height()-45, result.width(), 45)
    canvas.undo()
    assert canvas.image == image()
    canvas.redo()
    assert canvas.objects[0]['text'] == content


def test_cancel_long_text_restores_canvas_size():
    canvas = Canvas()
    canvas.load(image())
    canvas.set_zoom(150)
    canvas.tool = 'texto'
    gesture(canvas, (15, 15), (200, 130))
    canvas.text_editor.setPlainText('Line\n'*25)
    assert canvas.height() > 180
    canvas.finish_text(False)
    assert canvas.image == image()
    assert canvas.height() == 180


def test_text_menu_changes_selected_text_and_preserves_tab_defaults(window):
    window.finish_capture(image())
    tools = window.findChild(QToolBar, 'tools')
    assert tools.widgetForAction(window.tool_actions['texto']).menu() is window.text_menu
    window.text_size.setValue(22)
    window.choose_tool('texto')
    gesture(window.canvas, (10, 10), (150, 90))
    window.canvas.text_editor.setPlainText('First tab')
    window.canvas.finish_text()
    window.text_size.setValue(40)
    assert window.canvas.objects[0]['font_size'] == 40
    window.finish_capture(image())
    assert window.text_size.value() == 24
    window.tabs.setCurrentIndex(0)
    assert window.text_size.value() == 40
    assert window.text_size.width() >= 115


def test_text_and_balloon_editing_at_zoom_preserve_image_coordinates():
    canvas = Canvas()
    canvas.load(image())
    canvas.set_zoom(200)
    canvas.tool = 'balao'
    gesture(canvas, (40, 40), (220, 140))
    obj = canvas.objects[0]
    assert obj['a'] == [20, 20] and obj['b'] == [110, 70]
    tail = obj['tail'][:]
    gesture(canvas, [v*2 for v in tail], (280, 220))
    assert obj['tail'] == [140, 110]
    canvas.tool = 'texto'
    gesture(canvas, (50, 50), (200, 100))
    canvas.text_editor.setPlainText('Text')
    assert canvas.text_editor.font().pixelSize() == 48
    canvas.finish_text()
    canvas.set_zoom(100)
    result = canvas.image
    canvas.set_zoom(300)
    assert canvas.image == result
    obj = canvas.objects[-1]
    point = QPoint(*obj['a'])+QPoint(5, 5)
    QTest.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=point*3)
    assert canvas.text_editor is not None
    canvas.text_editor.setPlainText('Edited')
    canvas.finish_text()
    assert canvas.objects[-1]['text'] == 'Edited'


def test_changing_font_via_popup_keeps_the_text(window):
    window.finish_capture(image())
    window.choose_tool('texto')
    gesture(window.canvas, (10, 10), (150, 100))
    window.canvas.text_editor.setPlainText('Keep this text')
    tools = window.findChild(QToolBar, 'tools')
    button = tools.widgetForAction(window.tool_actions['texto'])
    window.text_menu.popup(button.mapToGlobal(button.rect().bottomRight()))
    app.processEvents()
    window.text_size.setValue(36)
    window.text_menu.close()
    window.canvas.finish_text()
    assert window.canvas.objects[-1]['text'] == 'Keep this text'
    assert window.canvas.objects[-1]['font_size'] == 36
