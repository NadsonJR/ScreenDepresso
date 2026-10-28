import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QToolBar

from screendepresso.app import MainWindow
from screendepresso.i18n import set_language
from test_editor import image, gesture

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


def capture_pair(window):
    first = image()
    second = QImage(200, 140, QImage.Format.Format_ARGB32)
    second.fill(QColor('blue'))
    window.finish_capture(first)
    a = window.canvas
    window.choose_tool('retângulo')
    gesture(a, (20, 20), (100, 80))
    window.finish_capture(second)
    return a, window.canvas


def test_captures_keep_independent_edit_and_undo_histories(window):
    a, b = capture_pair(window)
    assert window.tabs.count() == 2
    assert a.objects[0]['kind'] == 'retângulo'
    assert not b.objects and not b.undo_stack
    window.choose_tool('numero')
    gesture(b, (20, 20), (100, 80))
    edited_b = b.image
    window.tabs.setCurrentIndex(0)
    assert window.canvas is a
    assert '160 × 120' in window.dimensions.text()
    assert window.tool_actions[a.tool].isChecked()
    assert window.tabs.tabText(0) == 'Capture 1 *'
    QTest.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert not a.objects
    assert b.image == edited_b
    QTest.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert len(a.objects) == 1
    window.tabs.setCurrentIndex(1)
    assert window.tool_actions['numero'].isChecked()
    assert '200 × 140' in window.dimensions.text()
    ribbon = window.findChild(QToolBar, 'ribbon')
    next(a for a in ribbon.actions() if a.text() == 'Undo').trigger()
    assert not b.objects
    assert len(a.objects) == 1


def test_history_reuses_open_tab_without_losing_edits(window):
    a, b = capture_pair(window)
    path = window.tabs.widget(0).source_path
    item = next(window.list.item(i) for i in range(window.list.count()) if window.list.item(i).text() == path.name)
    window.open_history(item)
    assert window.tabs.count() == 2
    assert window.canvas is a and a.objects
    assert b.base.width() == 200


def test_history_opens_another_capture_without_replacing_current_edit(window):
    a, b = capture_pair(window)
    older = QImage(60, 40, QImage.Format.Format_ARGB32)
    older.fill(QColor('green'))
    path = window.history.save(older)
    window.refresh()
    item = next(window.list.item(i) for i in range(window.list.count()) if window.list.item(i).text() == path.name)
    window.open_history(item)
    assert window.tabs.count() == 3
    assert window.canvas.image == older
    assert a.objects and b.base.width() == 200


def test_switching_commits_inline_text_in_its_own_tab(window):
    a, b = capture_pair(window)
    window.choose_tool('texto')
    gesture(b, (10, 10), (150, 100))
    b.text_editor.setPlainText('Second capture only')
    window.tabs.setCurrentIndex(0)
    assert b.text_editor is None
    assert b.objects[0]['text'] == 'Second capture only'
    assert all(obj['kind'] != 'texto' for obj in a.objects)


def test_closing_dirty_tab_cancel_discard_and_last_tab(window, monkeypatch):
    a, b = capture_pair(window)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Cancel)
    window.close_tab(0)
    assert window.tabs.count() == 2 and window.canvas is a
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Discard)
    window.close_tab(0)
    assert window.tabs.count() == 1 and window.canvas is b
    window.close_tab(0)
    assert window.tabs.count() == 1 and window.canvas.base.isNull()
    assert window.tabs.tabText(0) == 'New capture'
    window.finish_capture(image())
    assert window.tabs.count() == 1


def test_close_save_cancelled_or_failed_keeps_tab(window, monkeypatch, tmp_path):
    a, b = capture_pair(window)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Save)
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: ('', ''))
    window.close_tab(0)
    assert window.tabs.count() == 2 and window.canvas is a
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(tmp_path/'missing'/'export.png'), ''))
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: None)
    window.close_tab(0)
    assert window.tabs.count() == 2
    output = tmp_path/'export.png'
    expected = a.image
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(output), ''))
    window.close_tab(0)
    assert QImage(str(output)) == expected
    assert window.tabs.count() == 1 and window.canvas is b


def test_active_tab_clipboard_paste_delete_and_blur_controls(window):
    a, b = capture_pair(window)
    window.copy()
    assert app.clipboard().image() == b.image
    window.paste()
    assert b.objects[-1]['kind'] == 'imagem'
    QTest.keyClick(window, Qt.Key.Key_Delete)
    assert not b.objects
    window.blur_strength.setValue(50)
    window.tabs.setCurrentIndex(0)
    assert window.blur_strength.value() == a.blur_radius == 14
    window.blur_strength.setValue(5)
    window.tabs.setCurrentIndex(1)
    assert window.blur_strength.value() == b.blur_radius == 50
    assert a.blur_radius == 5


def test_reordering_navigation_and_translated_titles(window):
    a, b = capture_pair(window)
    window.tabs.tabBar().moveTab(1, 0)
    assert window.canvas is b
    QTest.keyClick(window, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
    assert window.canvas is a
    QTest.keyClick(window, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert window.canvas is b
    window.tabs.mark_saved('Settings.png')
    set_language('pt_BR')
    assert window.tabs.tabText(0) == 'Settings.png'  # User filenames are never translated.
    assert window.tabs.tabText(1) == 'Captura 1 *'
    QTest.keyClick(window, Qt.Key.Key_W, Qt.KeyboardModifier.ControlModifier)
    assert window.canvas is a


def test_dirty_indicator_clears_on_undo_and_save(window, monkeypatch, tmp_path):
    a, b = capture_pair(window)
    assert window.tabs.tabText(0).endswith(' *')
    window.tabs.setCurrentIndex(0)
    a.undo()
    assert not window.tabs.tabText(0).endswith(' *')
    a.redo()
    output = tmp_path/'edited.png'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(output), ''))
    assert window.save()
    assert window.tabs.tabText(0) == 'edited.png'
    assert QImage(str(output)) == a.image
    assert not window.tabs.is_dirty(window.tabs.currentWidget())


def test_tab_preserves_scroll_position_and_annotation_colors(window):
    large = QImage(1600, 1200, QImage.Format.Format_ARGB32)
    large.fill(QColor('white'))
    window.finish_capture(large)
    a = window.canvas
    a.set_arrow_color(QColor('blue'))
    a.set_rectangle_color(QColor('green'))
    a.set_marker_color(QColor('yellow'))
    app.processEvents()
    scroll = window.scroll
    scroll.horizontalScrollBar().setValue(240)
    scroll.verticalScrollBar().setValue(180)
    positions = scroll.horizontalScrollBar().value(), scroll.verticalScrollBar().value()
    window.finish_capture(image())
    b = window.canvas
    assert b.arrow_color != a.arrow_color
    window.tabs.setCurrentIndex(0)
    assert window.canvas is a
    assert (scroll.horizontalScrollBar().value(), scroll.verticalScrollBar().value()) == positions
    assert a.arrow_color == '#0000ff'
    assert a.rectangle_color == '#008000'
    assert a.marker_color == '#ffff00'


@pytest.mark.parametrize('action,remaining', [(0, 0), (1, 2), (2, 1)])
def test_tab_context_actions_target_clicked_tab_after_reordering(window, action, remaining):
    for _ in range(3):
        window.finish_capture(image())
    tabs = window.tabs
    target = tabs.widget(0)
    tabs.setCurrentIndex(2)
    menu = tabs.context_menu(tabs.tabBar().tabRect(0).center())
    assert [a.text() for a in menu.actions()] == ['Close all tabs', 'Close this tab', 'Close other tabs']
    tabs.tabBar().moveTab(0, 1)
    menu.actions()[action].trigger()
    assert sum(not tabs.widget(i).widget().base.isNull() for i in range(tabs.count())) == remaining
    if action == 1:
        assert tabs.indexOf(target) == -1
    elif action == 2:
        assert tabs.currentWidget() is target
    else:
        assert tabs.count() == 1 and tabs.canvas.base.isNull()
        assert tabs.tabBar().isHidden()
    assert len(window.history.entries()) == 3  # Closing tabs never deletes saved captures.


def test_close_all_stops_on_cancel_after_closing_an_earlier_tab(window, monkeypatch):
    window.finish_capture(image())
    clean = window.tabs.currentWidget()
    a, b = capture_pair(window)
    dirty = window.tabs.widget(1)
    last = window.tabs.widget(2)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Cancel)
    window.close_tabs('all', clean)
    assert window.tabs.count() == 2
    assert window.tabs.currentWidget() is dirty
    assert window.tabs.indexOf(last) >= 0
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Discard)


def test_close_other_tabs_aborts_when_save_is_cancelled(window, monkeypatch):
    a, b = capture_pair(window)
    target = window.tabs.currentWidget()
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Save)
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: ('', ''))
    window.close_tabs('others', target)
    assert window.tabs.count() == 2 and window.canvas is a
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Discard)


def test_tab_context_menu_ignores_empty_space_and_translates(window):
    from PySide6.QtCore import QPoint
    window.finish_capture(image())
    tabs = window.tabs
    assert tabs.context_menu(QPoint(-10, -10)) is None
    set_language('pt_BR')
    menu = tabs.context_menu(tabs.tabBar().tabRect(0).center())
    assert [a.text() for a in menu.actions()] == ['Fechar todas as abas', 'Fechar essa aba', 'Fechar outras abas']
    assert not menu.actions()[2].isEnabled()
