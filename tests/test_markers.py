import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QColorDialog
from screendepresso.editor import Canvas
from screendepresso.app import MainWindow
from screendepresso.i18n import set_language
from test_editor import image, gesture

app = QApplication.instance() or QApplication([])


def test_sequential_clicks_delete_and_undo_redo():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'numero'
    for point in [(30, 30), (80, 30), (125, 80)]:
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(*point))
    assert [o['number'] for o in canvas.objects] == [1, 2, 3]
    assert canvas.tool == 'numero'  # Ready to place the next number.
    assert all(o['a'] != o['b'] for o in canvas.objects)
    canvas.selected = 1
    canvas.delete_selected()
    assert [o['number'] for o in canvas.objects] == [1, 2]
    canvas.undo()
    assert [o['number'] for o in canvas.objects] == [1, 2, 3]
    canvas.redo()
    assert [o['number'] for o in canvas.objects] == [1, 2]
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(120, 30))
    assert [o['number'] for o in canvas.objects] == [1, 2, 3]
    canvas.load(image())
    canvas.tool = 'numero'
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(40, 40))
    assert canvas.objects[0]['number'] == 1


def test_pointer_and_circle_are_independently_adjustable():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'numero'
    gesture(canvas, (40, 40), (110, 80))
    assert canvas.objects[0]['a'] == [40, 40]
    assert canvas.objects[0]['b'] == [110, 80]
    # The selected marker's handles also work without leaving numbering mode.
    gesture(canvas, (110, 80), (135, 95))
    assert canvas.objects[0]['a'] == [40, 40]
    assert canvas.objects[0]['b'] == [135, 95]
    gesture(canvas, (40, 40), (60, 55))
    assert canvas.objects[0]['a'] == [60, 55]
    assert canvas.objects[0]['b'] == [135, 95]
    canvas.undo()
    assert canvas.objects[0]['a'] == [40, 40]
    canvas.redo()
    assert canvas.objects[0]['a'] == [60, 55]


def test_marker_preview_and_global_color_are_rendered_and_undoable():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'numero'
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(35, 35))
    QTest.mouseMove(canvas, QPoint(80, 70))
    preview = canvas.render_image(True)
    assert preview != image()
    assert canvas.image == image()
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(80, 70))
    assert canvas.image == preview
    gesture(canvas, (110, 35), (120, 90))
    before = canvas.image
    canvas.set_marker_color('#1565c0')
    after = canvas.image
    # Circle fills and target dots of both annotations use the selected color.
    for x, y in [(35, 45), (110, 45), (80, 70), (120, 90)]:
        color = after.pixelColor(x, y)
        assert color.blue() > color.red()
    assert after != before
    canvas.undo()
    assert canvas.image == before
    assert canvas.marker_color == '#ef233c'
    canvas.redo()
    assert canvas.image == after
    gesture(canvas, (55, 90), (90, 100))
    assert canvas.objects[-1]['number'] == 3
    assert canvas.marker_color == '#1565c0'


def test_marker_hit_area_includes_circle_and_leader_not_empty_bounding_box():
    marker = {'kind': 'numero', 'a': [30, 30], 'b': [120, 100], 'number': 1}
    assert Canvas.hit_test(marker, QPoint(15, 30))
    assert Canvas.hit_test(marker, QPoint(75, 65))
    assert not Canvas.hit_test(marker, QPoint(110, 30))


def test_rectangle_color_changes_selected_and_future_rectangles_only():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'retângulo'
    gesture(canvas, (10, 10), (55, 55))
    canvas.tool = 'retângulo'
    gesture(canvas, (90, 60), (145, 105))
    before = canvas.image
    canvas.set_rectangle_color('#00aa00')
    assert canvas.objects[0]['color'] == '#ef233c'
    assert canvas.objects[1]['color'] == '#00aa00'
    assert canvas.image.pixelColor(115, 62).green() > 100
    canvas.undo()
    assert canvas.image == before
    assert canvas.rectangle_color == '#ef233c'
    canvas.redo()
    canvas.tool = 'retângulo'
    gesture(canvas, (20, 75), (60, 115))
    assert canvas.objects[-1]['color'] == '#00aa00'


def test_color_buttons_and_translations(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    monkeypatch.delenv('DISPLAY', raising=False)
    window = MainWindow()
    try:
        window.canvas.load(image())
        window.tool_actions['numero'].trigger()
        assert window.canvas.tool == 'numero'
        gesture(window.canvas, (40, 40), (100, 80))
        monkeypatch.setattr(QColorDialog, 'getColor', lambda *a, **kw: QColor('#3366ff'))
        window.color_actions['numero'].trigger()
        assert window.canvas.marker_color == '#3366ff'
        window.choose_tool('retângulo')
        gesture(window.canvas, (80, 15), (140, 55))
        window.color_actions['retângulo'].trigger()
        assert window.canvas.objects[-1]['color'] == '#3366ff'
        history_size = len(window.canvas.undo_stack)
        monkeypatch.setattr(QColorDialog, 'getColor', lambda *a, **kw: QColor())
        window.color_actions['numero'].trigger()
        window.color_actions['retângulo'].trigger()
        assert len(window.canvas.undo_stack) == history_size
        window.apply_settings(window.settings.directory, window.settings.hotkeys, 'pt_BR')
        assert window.tool_actions['numero'].text() == 'Marcadores numerados'
        assert window.color_actions['numero'].text() == 'Cor dos marcadores…'
        assert window.color_actions['retângulo'].text() == 'Cor do retângulo…'
    finally:
        window.close()
        set_language('en')


def test_arrow_color_affects_selected_and_next_arrow_with_undo():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'seta'
    gesture(canvas, (10, 10), (50, 50))
    canvas.tool = 'seta'
    gesture(canvas, (80, 20), (140, 80))
    original = canvas.image
    canvas.set_arrow_color('#1565c0')
    assert canvas.objects[0]['color'] == '#ef233c'
    assert canvas.objects[1]['color'] == '#1565c0'
    assert canvas.image.pixelColor(110, 50).blue() > canvas.image.pixelColor(110, 50).red()
    blue = canvas.image
    canvas.undo()
    assert canvas.image == original
    assert canvas.arrow_color == '#ef233c'
    canvas.redo()
    assert canvas.image == blue
    canvas.tool = 'seta'
    gesture(canvas, (10, 90), (70, 110))
    assert canvas.objects[-1]['color'] == '#1565c0'


def test_sidebar_split_buttons_select_tools_and_expose_color_menus(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QToolBar, QToolButton
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    monkeypatch.delenv('DISPLAY', raising=False)
    window = MainWindow()
    try:
        tools = window.findChild(QToolBar, 'tools')
        for kind in ('numero', 'retângulo', 'seta'):
            button = tools.widgetForAction(window.tool_actions[kind])
            assert button.popupMode() == QToolButton.ToolButtonPopupMode.MenuButtonPopup
            assert window.color_actions[kind] in button.menu().actions()
            assert window.color_actions[kind].toolTip()
            button.click()
            assert window.canvas.tool == kind
        window.canvas.load(image())
        gesture(window.canvas, (20, 20), (100, 80))
        monkeypatch.setattr(QColorDialog, 'getColor', lambda *a, **kw: QColor('#00aa00'))
        window.color_actions['seta'].trigger()
        assert window.canvas.objects[-1]['color'] == '#00aa00'
        history_size = len(window.canvas.undo_stack)
        monkeypatch.setattr(QColorDialog, 'getColor', lambda *a, **kw: QColor())
        window.color_actions['seta'].trigger()
        assert len(window.canvas.undo_stack) == history_size
        window.apply_settings(window.settings.directory, window.settings.hotkeys, 'pt_BR')
        assert window.color_actions['seta'].text() == 'Cor da seta…'
    finally:
        window.close()
        set_language('en')
