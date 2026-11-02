"""Direction, compositing, editing and UI regression tests for local blur."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QColor, QPainter
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from screendepresso import blur
from screendepresso.editor import Canvas
from screendepresso.app import MainWindow
from screendepresso.i18n import set_language
from test_editor import gesture

app = QApplication.instance() or QApplication([])


def source(alpha=False):
    image = QImage(160, 120, QImage.Format.Format_ARGB32)
    for x in range(160):
        for y in range(120):
            image.setPixelColor(x, y, QColor(255 if x % 8 < 4 else 0, y*2, x, 100+x % 100 if alpha else 255))
    image.setPixelColor(2, 2, QColor(150, 77, 201, 0 if alpha else 255))
    return image


def effect(a=(20, 20), b=(90, 85), inside=True):
    return {'kind': 'desfoque', 'a': list(a), 'b': list(b), 'radius': 14, 'inside': inside}


@pytest.mark.parametrize('mode', ['shared', 'sequential'])
@pytest.mark.parametrize('alpha', [False, True])
def test_inside_only_changes_selected_pixels_and_preview_matches_export(mode, alpha):
    canvas = Canvas(); canvas.load(source(alpha)); canvas.blur_mode = mode
    canvas.objects = [effect()]
    expected_blur = blur.blurred_image(canvas.base, 14).convertToFormat(QImage.Format.Format_ARGB32)
    result = canvas.image
    rect = canvas.object_rect(canvas.objects[0])
    assert result != canvas.base
    for y in range(120):
        for x in range(160):
            assert result.pixel(x, y) == (expected_blur if rect.contains(x, y) else canvas.base).pixel(x, y)
    # Compare displayed alpha against the exported image on the same background.
    expected = QImage(canvas.base.size(), QImage.Format.Format_ARGB32)
    expected.fill(QColor('#202b37'))
    painter = QPainter(expected); painter.drawImage(0, 0, result); painter.end()
    target = QImage(expected.size(), expected.format()); target.fill(QColor('#202b37'))
    painter = QPainter(target); canvas.paint_document(painter); painter.end()
    assert target == expected


def test_shared_mixed_directions_overlap_without_accumulating_blur():
    canvas = Canvas(); canvas.load(source())
    canvas.objects = [effect((10, 10), (120, 100), False), effect((25, 25), (60, 60)), effect((45, 45), (90, 85))]
    filtered = blur.blurred_image(canvas.base, 14).convertToFormat(canvas.base.format())
    regions = [canvas.object_rect(obj) for obj in canvas.objects]
    result = canvas.image
    for y in range(120):
        for x in range(160):
            blurred = not regions[0].contains(x, y) or any(r.contains(x, y) for r in regions[1:])
            assert result.pixel(x, y) == (filtered if blurred else canvas.base).pixel(x, y)


@pytest.mark.parametrize('mode', ['shared', 'sequential'])
def test_direction_creation_editing_pending_preview_and_undo_redo(mode):
    canvas = Canvas(); canvas.load(source()); canvas.blur_mode = mode
    canvas.set_blur_inside(True); canvas.tool = 'desfoque'
    gesture(canvas, (20, 20), (90, 85))
    assert canvas.objects[0]['inside'] is True
    inside = canvas.image
    canvas.selected = 0
    canvas.set_blur_inside(False)
    assert canvas.image != inside
    canvas.undo()
    assert canvas.blur_inside and canvas.objects[0]['inside'] and canvas.image == inside
    canvas.redo()
    assert not canvas.blur_inside and not canvas.objects[0]['inside']
    canvas.pending = effect((40, 35), (70, 65))
    assert canvas.render_image(True) != canvas.image
    canvas.pending = None
    # Cropping retains the per-object direction, undo restores the full result.
    original = canvas.image
    canvas.selected = None; canvas.tool = 'recorte'
    gesture(canvas, (5, 5), (140, 110))
    assert canvas.objects[0]['inside'] is False
    canvas.undo()
    assert canvas.image == original


def test_switching_direction_reuses_cached_gaussian(monkeypatch):
    blur.clear_blur_cache()
    calls = []; original = blur.blurred_image
    def counted(image, radius):
        calls.append(radius)
        return original(image, radius)
    monkeypatch.setattr(blur, 'blurred_image', counted)
    canvas = Canvas(); canvas.load(source()); canvas.objects = [effect()]; canvas.selected = 0
    for inside in (True, False, True):
        canvas.set_blur_inside(inside)
        assert not canvas.image.isNull()
    assert calls == [14]
    blur.clear_blur_cache()


def test_menu_context_controls_selection_translation_and_tabs(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    window = MainWindow()
    try:
        window.finish_capture(source())
        window.blur_areas[True].trigger()
        assert window.canvas.blur_inside and window.context_bar.blur_area.currentData() is True
        assert window.tool_actions['desfoque'].toolTip() == 'Blur inside selection'
        window.choose_tool('desfoque'); gesture(window.canvas, (20, 20), (90, 85))
        window.canvas.selected = None
        window.canvas.set_blur_inside(False)
        window.choose_tool('selecionar')
        QTest.mouseClick(window.canvas, Qt.MouseButton.LeftButton, pos=QPoint(45, 45))
        assert window.blur_areas[True].isChecked()
        window.context_bar.blur_area.setCurrentIndex(window.context_bar.blur_area.findData(False))
        assert window.canvas.objects[0]['inside'] is False
        window.canvas.undo()
        assert window.canvas.objects[0]['inside'] is True
        window.canvas.set_blur_inside(True)
        window.finish_capture(source())
        assert window.blur_areas[False].isChecked()
        window.tabs.setCurrentIndex(0)
        assert window.blur_areas[True].isChecked()
        set_language('pt_BR')
        assert window.blur_areas[True].text() == 'Desfocar dentro da seleção'
        assert window.context_bar.blur_area.currentText() == 'Desfocar dentro da seleção'
    finally:
        window.close(); set_language('en')
