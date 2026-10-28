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


def test_text_content_edit():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'texto'
    gesture(canvas, (10, 10), (150, 90))
    assert canvas.text_editor is not None
    canvas.text_editor.setPlainText('Primeiro')
    QTest.keyClick(canvas.text_editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert canvas.objects[0]['text'] == 'Primeiro'
    assert canvas.image != image()
    assert canvas.base == image()
    QTest.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(30, 25))
    assert canvas.text_editor is not None
    canvas.text_editor.setPlainText('Editado')
    canvas.finish_text()
    assert canvas.objects[0]['text'] == 'Editado'
    canvas.undo()
    assert canvas.objects[0]['text'] == 'Primeiro'
    canvas.redo()
    assert canvas.objects[0]['text'] == 'Editado'


def test_text_preview_and_cancel_keep_image_visible():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'texto'
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    QTest.mouseMove(canvas, QPoint(150, 90))
    assert canvas.render_image(True) == image()
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(150, 90))
    canvas.text_editor.setPlainText('Cancelar')
    QTest.keyClick(canvas.text_editor, Qt.Key.Key_Escape)
    assert canvas.image == image()
    assert canvas.objects == []
    assert not canvas.undo_stack


def test_empty_text_is_not_inserted_and_multiline_is_visible():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'texto'
    gesture(canvas, (10, 10), (150, 100))
    canvas.finish_text()
    assert canvas.objects == []
    canvas.tool = 'texto'
    gesture(canvas, (10, 10), (150, 100))
    canvas.text_editor.setPlainText('Linha 1\nLinha 2')
    canvas.finish_text()
    result = canvas.image
    assert result.copy(10, 10, 140, 30) != image().copy(10, 10, 140, 30)
    assert result.copy(10, 40, 140, 40) != image().copy(10, 40, 140, 40)
    assert result.pixelColor(0, 0) == QColor('white')
    canvas.undo()
    assert canvas.objects == []
    canvas.redo()
    assert canvas.objects[0]['text'] == 'Linha 1\nLinha 2'


def test_high_dpi_image_uses_pixel_coordinates():
    original = image()
    original.setDevicePixelRatio(2)
    canvas = Canvas()
    canvas.load(original)
    assert canvas.base.devicePixelRatio() == 1
    drag(canvas, 'seta')
    assert canvas.image.pixelColor(60, 50) != QColor('white')


def test_typing_text_and_clicking_outside_confirms_without_popup():
    canvas = Canvas()
    canvas.load(image())
    canvas.show()
    canvas.tool = 'texto'
    gesture(canvas, (10, 10), (150, 90))
    editor = canvas.text_editor
    QTest.keyClicks(editor, 'Texto digitado')
    assert editor.toPlainText() == 'Texto digitado'
    # Canvas click commits text as a single document operation.
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(155, 110))
    assert canvas.text_editor is None
    assert canvas.objects[0]['text'] == 'Texto digitado'
    assert len(canvas.undo_stack) == 1
    assert canvas.image != image()
    canvas.close()


def test_pasted_image_is_editable_and_undoable():
    canvas = Canvas()
    canvas.load(image())
    overlay = QImage(40, 30, QImage.Format.Format_ARGB32)
    overlay.fill(QColor('blue'))
    assert canvas.paste_image(overlay)
    obj = canvas.objects[0]
    assert obj['kind'] == 'imagem'
    assert canvas.image.pixelColor(70, 50) == QColor('blue')
    assert canvas.image.pixelColor(0, 0) == QColor('white')
    gesture(canvas, tuple(obj['b']), (130, 100))
    assert canvas.objects[0]['b'] == [130, 100]
    canvas.undo()
    assert canvas.objects[0]['b'] == [99, 74]
    canvas.redo()
    assert canvas.objects[0]['b'] == [130, 100]
    canvas.delete_selected()  # Redo clears selection: select again first.
    gesture(canvas, (75, 60), (80, 65))
    assert canvas.objects[0]['a'] != [60, 45]
    canvas.delete_selected()
    assert canvas.objects == []
    canvas.undo()
    assert canvas.objects[0]['image'] == overlay


def test_paste_fits_large_images_and_keeps_alpha():
    canvas = Canvas()
    canvas.load(image())
    overlay = QImage(400, 300, QImage.Format.Format_ARGB32)
    overlay.fill(QColor(0, 0, 255, 128))
    canvas.paste_image(overlay)
    assert canvas.object_rect(canvas.objects[0]).size() == canvas.base.size()
    color = canvas.image.pixelColor(20, 20)
    assert color.blue() == 255
    assert 120 <= color.red() <= 130
    canvas.undo()
    assert canvas.image == image()
    canvas.redo()
    assert canvas.objects[0]['kind'] == 'imagem'


def test_image_paste_during_text_edit_commits_both_layers():
    canvas = Canvas()
    canvas.load(image())
    canvas.tool = 'texto'
    gesture(canvas, (10, 10), (150, 100))
    canvas.text_editor.setPlainText('Label')
    app.clipboard().setImage(image().copy(0, 0, 20, 20))
    QTest.keyClick(canvas.text_editor, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    assert canvas.text_editor is None
    assert [obj['kind'] for obj in canvas.objects] == ['texto', 'imagem']
    canvas.undo()
    assert [obj['kind'] for obj in canvas.objects] == ['texto']
    canvas.undo()
    assert not canvas.objects


def test_history_never_overwrites_when_clock_has_low_precision(tmp_path, monkeypatch):
    from datetime import datetime as RealDatetime
    from screendepresso import workspace as module
    frozen = RealDatetime(2026, 10, 27, 12, 30)
    class FixedClock:
        @staticmethod
        def now():
            return frozen
    monkeypatch.setattr(module, 'datetime', FixedClock)
    first = History(tmp_path)
    second = History(tmp_path)
    a = first.save(image())
    b = first.save(image())
    different = image()
    different.fill(QColor('blue'))
    c = second.save(different)
    assert len({a, b, c}) == 3
    assert first.entries() == [c, b, a]
    assert QImage(str(a)) == image()
    assert QImage(str(c)) == different
