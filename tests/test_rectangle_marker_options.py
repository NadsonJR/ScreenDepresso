import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolBar
from screendepresso.app import MainWindow
from screendepresso.editor import Canvas
from screendepresso.i18n import set_language
from screendepresso.markers import MARKER_STYLES
from test_editor import gesture

app = QApplication.instance() or QApplication([])


def image():
    image = QImage(260,180,QImage.Format.Format_ARGB32)
    image.fill(QColor('white'))
    return image


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path/'data'))
    window = MainWindow()
    window.show()
    app.processEvents()
    yield window
    window.request_quit()
    set_language('en')


def test_rectangle_width_and_rounding_change_rendering_and_support_undo():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'retângulo'
    gesture(canvas,(30,30),(190,130))
    original = canvas.image
    assert canvas.objects[0]['width'] == 4 and not canvas.objects[0]['rounded']
    assert original.pixelColor(36,80) == QColor('white')
    canvas.set_rectangle_format(width=16,rounded=True,radius=25)
    obj = canvas.objects[0]
    assert obj['width'] == 16 and obj['rounded'] and obj['radius'] == 25
    rounded = canvas.image
    assert rounded.pixelColor(36,80) == QColor('#ef233c')
    assert rounded.pixelColor(31,31) == QColor('white')
    assert rounded != original
    canvas.undo()
    assert canvas.image == original
    canvas.redo()
    assert canvas.image == rounded
    canvas.selected = 0
    canvas.set_rectangle_format(rounded=False)
    assert canvas.image.pixelColor(31,31) != QColor('white')


def test_rectangle_style_is_in_live_preview_and_survives_resize_at_zoom():
    canvas = Canvas()
    canvas.load(image())
    canvas.set_rectangle_format(width=10,rounded=True,radius=20)
    canvas.set_zoom(150)
    canvas.tool = 'retângulo'
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=QPoint(45,45))
    QTest.mouseMove(canvas,QPoint(285,195))
    preview = canvas.render_image(True)
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=QPoint(285,195))
    assert canvas.image == preview
    gesture(canvas,(285,195),(330,225))
    obj = canvas.objects[0]
    assert obj['b'] == [220,150]
    assert obj['width'] == 10 and obj['rounded'] and obj['radius'] == 20
    canvas.undo()
    assert canvas.image == preview


@pytest.mark.parametrize('style',MARKER_STYLES)
def test_marker_models_preview_color_pointer_and_undo(style):
    canvas = Canvas()
    canvas.load(image())
    canvas.set_marker_style(style)
    canvas.tool = 'numero'
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=QPoint(45,45))
    QTest.mouseMove(canvas,QPoint(150,100))
    preview = canvas.render_image(True)
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=QPoint(150,100))
    assert canvas.image == preview and preview != image()
    assert canvas.objects[0]['style'] == style
    gesture(canvas,(150,100),(180,130))
    assert canvas.objects[0]['a'] == [45,45]
    assert canvas.objects[0]['b'] == [180,130]
    canvas.set_marker_color('#0000ff')
    assert canvas.image.pixelColor(180,130) == QColor('blue')
    canvas.undo()
    assert canvas.image.pixelColor(180,130) == QColor('#ef233c')
    canvas.redo()
    assert canvas.image.pixelColor(180,130) == QColor('blue')


def test_mixed_marker_models_share_sequential_numbers_and_global_color():
    canvas = Canvas()
    canvas.load(image())
    for index,style in enumerate(MARKER_STYLES):
        canvas.selected = None
        canvas.set_marker_style(style)
        canvas.tool = 'numero'
        gesture(canvas,(30+index*40,40),(35+index*40,110))
    assert [o['number'] for o in canvas.objects] == [1,2,3,4,5,6]
    before = canvas.image
    canvas.set_marker_color('#008000')
    for obj in canvas.objects:
        assert canvas.image.pixelColor(*obj['b']) == QColor('#008000')
    canvas.undo()
    assert canvas.image == before
    canvas.selected = 2
    canvas.set_marker_style('hexagon')
    assert canvas.objects[2]['style'] == 'hexagon'
    assert canvas.objects[1]['style'] == 'flat'
    canvas.delete_selected()
    assert [o['number'] for o in canvas.objects] == [1,2,3,4,5]
    canvas.undo()
    assert [o['number'] for o in canvas.objects] == [1,2,3,4,5,6]


def test_square_corners_hit_and_move_existing_marker_in_number_mode():
    canvas = Canvas()
    canvas.load(image())
    canvas.set_marker_style('square')
    canvas.tool = 'numero'
    gesture(canvas,(50,50),(160,110))
    assert Canvas.hit_test(canvas.objects[0],QPoint(69,69))
    gesture(canvas,(69,69),(79,79))
    assert len(canvas.objects) == 1
    assert canvas.objects[0]['a'] == [60,60]
    assert canvas.objects[0]['b'] == [160,110]


def test_six_models_render_distinctly():
    canvas = Canvas()
    canvas.load(image())
    images = []
    for style in MARKER_STYLES:
        canvas.objects = [{'kind':'numero','a':[50,50],'b':[160,110],'number':23,'style':style}]
        rendered = canvas.image
        assert all(rendered != previous for previous in images)
        images.append(rendered)


def test_options_are_in_tool_buttons_translate_and_remain_independent_per_tab(window):
    window.finish_capture(image())
    tools = window.findChild(QToolBar,'tools')
    rectangle_menu = tools.widgetForAction(window.tool_actions['retângulo']).menu()
    assert rectangle_menu.isAncestorOf(window.rectangle_width)
    assert rectangle_menu.isAncestorOf(window.rectangle_rounded)
    assert rectangle_menu.isAncestorOf(window.rectangle_radius)
    marker_menu = tools.widgetForAction(window.tool_actions['numero']).menu()
    assert all(action in marker_menu.actions() for action in window.marker_styles.values())
    window.rectangle_width.setValue(12)
    window.rectangle_rounded.setChecked(True)
    window.rectangle_radius.setValue(30)
    window.choose_tool('retângulo')
    gesture(window.canvas,(30,30),(190,130))
    window.rectangle_width.setValue(20)
    assert window.canvas.objects[0]['width'] == 20
    window.canvas.selected = None
    window.marker_styles['diamond'].trigger()
    gesture(window.canvas,(55,55),(180,140))
    window.marker_styles['outline'].trigger()
    assert window.canvas.objects[-1]['style'] == 'outline'
    window.finish_capture(image())
    assert window.rectangle_width.value() == 4
    assert not window.rectangle_rounded.isChecked()
    assert not window.rectangle_radius.isEnabled()
    assert window.marker_styles['circle'].isChecked()
    window.tabs.setCurrentIndex(0)
    assert window.rectangle_width.value() == 20
    assert window.rectangle_rounded.isChecked()
    assert window.rectangle_radius.value() == 30
    assert window.marker_styles['outline'].isChecked()
    set_language('pt_BR')
    assert window.rectangle_rounded.text() == 'Cantos arredondados'
    assert window.rectangle_width.toolTip() == 'Espessura da borda'
    assert window.marker_styles['hexagon'].text() == 'Marcador hexagonal'
