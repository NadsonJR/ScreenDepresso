import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from screendepresso.app import Canvas, History

app = QApplication.instance() or QApplication([])


def image():
    result = QImage(160, 120, QImage.Format.Format_ARGB32)
    result.fill(QColor('white'))
    return result


def drag(canvas, tool):
    canvas.tool = tool
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    QTest.mouseMove(canvas, QPoint(100, 80))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(100, 80))


def test_annotations_and_undo():
    for tool in ('seta', 'retângulo'):
        canvas = Canvas()
        original = image()
        canvas.load(original)
        drag(canvas, tool)
        assert canvas.image != original
        canvas.undo()
        assert canvas.image == original


def test_crop_and_undo():
    canvas = Canvas()
    canvas.load(image())
    drag(canvas, 'recorte')
    assert canvas.image.width() == 81
    assert canvas.image.height() == 61
    canvas.undo()
    assert canvas.image.size() == image().size()


def test_blur_changes_pattern():
    canvas = Canvas()
    original = image()
    for x in range(40, 60):
        for y in range(30, 70):
            original.setPixelColor(x, y, QColor('black'))
    canvas.load(original)
    drag(canvas, 'desfoque')
    assert canvas.image != original
    assert canvas.image.pixelColor(0, 0) == QColor('white')
    canvas.undo()
    assert canvas.image == original


def test_history_roundtrip(tmp_path):
    history = History(tmp_path)
    original = image()
    first = history.save(original)
    second = history.save(original)
    assert history.entries() == [second, first]
    assert QImage(str(first)) == original


def gesture(canvas, start, end):
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(*start))
    QTest.mouseMove(canvas, QPoint(*end))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(*end))


def test_redo_and_new_action_clears_redo():
    canvas = Canvas()
    canvas.load(image())
    drag(canvas, 'retângulo')
    edited = canvas.image
    canvas.undo()
    canvas.redo()
    assert canvas.image == edited
    canvas.undo()
    drag(canvas, 'seta')
    assert not canvas.redo_stack
    assert canvas.objects[0]['kind'] == 'seta'


def test_resize_move_delete_with_undo_redo():
    canvas = Canvas()
    canvas.load(image())
    drag(canvas, 'retângulo')
    gesture(canvas, (100, 80), (140, 100))
    assert canvas.objects[0]['b'] == [140, 100]
    canvas.undo()
    assert canvas.objects[0]['b'] == [100, 80]
    canvas.redo()
    gesture(canvas, (60, 50), (70, 60))
    assert canvas.objects[0]['a'] == [30, 30]
    canvas.delete_selected()
    assert canvas.objects == []
    canvas.undo()
    assert len(canvas.objects) == 1


def test_arrow_live_preview_and_axis_aligned_arrow():
    canvas = Canvas()
    canvas.load(image())
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    QTest.mouseMove(canvas, QPoint(100, 80))
    preview = canvas.render_image(True)
    assert preview.pixelColor(60, 50) != QColor('white')
    assert preview.pixelColor(100, 30) == QColor('white')
    assert canvas.image == image()  # Preview does not modify the document.
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(100, 80))
    assert canvas.image == preview
    canvas.load(image())
    canvas.tool = 'seta'
    gesture(canvas, (20, 50), (100, 50))
    assert len(canvas.objects) == 1


def test_blur_keeps_selection_and_blurs_outside_with_adjustable_strength():
    canvas = Canvas()
    original = image()
    for x in range(original.width()):
        for y in range(original.height()):
            original.setPixelColor(x, y, QColor('black' if (x//8)%2 else 'white'))
    canvas.load(original)
    drag(canvas, 'desfoque')
    assert canvas.image.copy(20, 20, 81, 61) == original.copy(20, 20, 81, 61)
    assert canvas.image.pixelColor(120, 50) != original.pixelColor(120, 50)
    before = canvas.image
    canvas.set_blur_radius(1)
    assert canvas.image != before
    assert canvas.image.copy(20, 20, 81, 61) == original.copy(20, 20, 81, 61)
    canvas.undo()
    assert canvas.image == before
    canvas.redo()
    assert canvas.objects[0]['radius'] == 1


def test_crop_preserves_editable_annotations():
    canvas = Canvas()
    canvas.load(image())
    drag(canvas, 'retângulo')
    drag(canvas, 'recorte')
    assert len(canvas.objects) == 1
    assert canvas.objects[0]['a'] == [0, 0]
    canvas.undo()
    assert canvas.objects[0]['a'] == [20, 20]


def test_text_content_edit(monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **kw: ('Primeiro', True))
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'texto'
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    assert canvas.objects[0]['text'] == 'Primeiro'
    monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **kw: ('Editado', True))
    QTest.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(30, 25))
    assert canvas.objects[0]['text'] == 'Editado'
    canvas.undo()
    assert canvas.objects[0]['text'] == 'Primeiro'


def test_high_dpi_image_uses_pixel_coordinates():
    original = image()
    original.setDevicePixelRatio(2)
    canvas = Canvas()
    canvas.load(original)
    assert canvas.base.devicePixelRatio() == 1
    drag(canvas, 'seta')
    assert canvas.image.pixelColor(60, 50) != QColor('white')
