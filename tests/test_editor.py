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
