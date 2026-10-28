import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtWidgets import QApplication, QToolBar
from screendepresso.annotations import ARROW_STYLES
from screendepresso.app import MainWindow
from screendepresso.editor import Canvas
from screendepresso.i18n import set_language
from test_editor import gesture

app = QApplication.instance() or QApplication([])


def pattern():
    image = QImage(240, 180, QImage.Format.Format_ARGB32)
    for x in range(image.width()):
        for y in range(image.height()):
            image.setPixelColor(x, y, QColor('black' if x//4 % 2 else 'white'))
    return image


def two_blurs(canvas):
    for start, end in [((20,20), (80,80)), ((120,20), (180,80))]:
        canvas.tool = 'desfoque'
        gesture(canvas, start, end)


def test_shared_blur_preserves_union_and_legacy_is_reversible():
    canvas = Canvas()
    original = pattern()
    canvas.load(original)
    two_blurs(canvas)
    shared = canvas.image
    for x in (20, 120):
        assert shared.copy(x,20,61,61) == original.copy(x,20,61,61)
    assert shared.copy(10,100,200,60) != original.copy(10,100,200,60)
    canvas.set_blur_mode('sequential')
    legacy = canvas.image
    assert legacy.copy(20,20,61,61) != original.copy(20,20,61,61)
    canvas.undo()
    assert canvas.blur_mode == 'shared' and canvas.image == shared
    canvas.redo()
    assert canvas.blur_mode == 'sequential' and canvas.image == legacy
    canvas.set_blur_mode('shared')
    assert canvas.image == shared


def test_shared_blur_has_one_strength_and_does_not_blur_annotations():
    canvas = Canvas()
    canvas.load(pattern())
    canvas.tool = 'seta'
    gesture(canvas, (20,140), (180,140))
    two_blurs(canvas)
    assert canvas.image.pixelColor(80,140) == QColor('#ef233c')
    before = canvas.image
    canvas.set_blur_radius(2)
    assert [obj['radius'] for obj in canvas.objects if obj['kind']=='desfoque'] == [2,2]
    assert canvas.image != before
    canvas.undo()
    assert canvas.image == before
    assert canvas.blur_radius == 14
    canvas.set_blur_mode('sequential')
    canvas.selected = 1
    canvas.set_blur_radius(3)
    assert [obj['radius'] for obj in canvas.objects if obj['kind']=='desfoque'] == [3,14]


@pytest.mark.parametrize('style', ARROW_STYLES)
def test_arrow_styles_preview_edit_and_undo(style):
    canvas = Canvas()
    white = QImage(240,180,QImage.Format.Format_ARGB32)
    white.fill(QColor('white'))
    canvas.load(white)
    canvas.set_arrow_style(style)
    canvas.tool = 'seta'
    from PySide6.QtTest import QTest
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(30,80))
    QTest.mouseMove(canvas, QPoint(190,80))
    preview = canvas.render_image(True)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(190,80))
    assert canvas.image == preview and canvas.image != white
    assert canvas.objects[0]['style'] == style
    if style == 'line':
        assert canvas.image.pixelColor(172,89) == QColor('white')
    canvas.set_arrow_color(QColor('blue'))
    colored = canvas.image
    canvas.undo()
    assert canvas.image == preview
    canvas.redo()
    assert canvas.image == colored
    canvas.selected = 0
    alternate = 'line' if style != 'line' else 'double'
    canvas.set_arrow_style(alternate)
    assert canvas.objects[0]['style'] == alternate
    canvas.undo()
    assert canvas.objects[0]['style'] == style


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


def wheel(view, delta, position=QPointF(200,150), modifiers=Qt.KeyboardModifier.NoModifier):
    event = QWheelEvent(position, QPointF(view.mapToGlobal(position.toPoint())), QPoint(), QPoint(0,delta),
                        Qt.MouseButton.NoButton, modifiers, Qt.ScrollPhase.NoScrollPhase, False)
    app.sendEvent(view, event)
    app.processEvents()


def test_mouse_wheel_zoom_syncs_slider_and_keeps_export_unchanged(window):
    original = pattern()
    window.finish_capture(original)
    view = window.scroll.viewport()
    wheel(view,120)
    assert window.zoom_slider.value() == 110
    wheel(view,60)
    assert window.zoom_slider.value() == 110
    wheel(view,60)
    assert window.zoom_slider.value() == 120
    wheel(view,-120)
    assert window.zoom_slider.value() == 110
    assert window.canvas.image == original
    window.zoom_slider.setValue(400)
    wheel(view,120)
    assert window.zoom_slider.value() == 400
    window.zoom_slider.setValue(10)
    wheel(view,-120)
    assert window.zoom_slider.value() == 10


def test_wheel_zoom_anchors_cursor_and_shift_preserves_zoom(window):
    large = QImage(2200,1800,QImage.Format.Format_ARGB32)
    large.fill(QColor('white'))
    window.finish_capture(large)
    app.processEvents()
    view = window.scroll.viewport()
    position = QPointF(300,200)
    old = (position-QPointF(window.canvas.pos()))/window.canvas.zoom
    wheel(view,120,position)
    new = (position-QPointF(window.canvas.pos()))/window.canvas.zoom
    assert abs(old.x()-new.x()) < 2 and abs(old.y()-new.y()) < 2
    wheel(view,-120,position,Qt.KeyboardModifier.ShiftModifier)
    assert window.zoom_slider.value() == 110


def test_arrow_and_blur_modes_are_on_tool_menus_and_per_tab(window):
    window.finish_capture(pattern())
    tools = window.findChild(QToolBar,'tools')
    menu = tools.widgetForAction(window.tool_actions['seta']).menu()
    assert all(action in menu.actions() for action in window.arrow_styles.values())
    window.arrow_styles['line'].trigger()
    assert window.canvas.arrow_style == 'line'
    window.blur_modes['sequential'].trigger()
    assert window.canvas.blur_mode == 'sequential'
    window.finish_capture(pattern())
    assert window.blur_modes['shared'].isChecked()
    window.tabs.setCurrentIndex(0)
    assert window.arrow_styles['line'].isChecked()
    assert window.blur_modes['sequential'].isChecked()
    set_language('pt_BR')
    assert window.arrow_styles['line'].text() == 'Linha'
    assert window.blur_modes['shared'].text() == 'Camada única de desfoque'
