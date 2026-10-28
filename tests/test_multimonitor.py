import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import pytest
from PySide6.QtCore import QRect, QPoint, QPointF, Qt, QEvent
from PySide6.QtGui import QColor, QImage, QPixmap, QGuiApplication, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QListView
from screendepresso import platform_support as platform
from screendepresso import app as application
from screendepresso import capture_ui
from screendepresso.capture_ui import Selector, WindowPicker
from screendepresso.i18n import set_language

app = QApplication.instance() or QApplication([])


class Screen:
    def __init__(self, name, rect, color, scale=1):
        self.title, self.rect, self.color, self.scale = name, rect, color, scale
        self.requests = []
    def name(self):
        return self.title
    def geometry(self):
        return self.rect
    def devicePixelRatio(self):
        return self.scale
    def availableGeometry(self):
        raise AssertionError('Capture must include panels and taskbars')
    def grabWindow(self, *args):
        self.requests.append(args)
        image = QImage(round(self.rect.width()*self.scale), round(self.rect.height()*self.scale), QImage.Format.Format_ARGB32)
        image.fill(QColor(self.color))
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(self.scale)
        return pixmap


def screens(monkeypatch, values):
    monkeypatch.setattr(QGuiApplication,'screens',lambda: values)
    monkeypatch.setattr(QGuiApplication,'primaryScreen',lambda: values[0])


def test_all_monitors_include_negative_origin_and_native_full_bounds(monkeypatch):
    left = Screen('left',QRect(-200,0,200,100),'red')
    right = Screen('right',QRect(0,0,300,100),'blue')
    screens(monkeypatch,[left,right])
    pixmap, geometry = platform.capture_desktop()
    assert geometry == QRect(-200,0,500,100)
    assert pixmap.size().width() == 500 and pixmap.size().height() == 100
    assert pixmap.toImage().pixelColor(0,99) == QColor('red')
    assert pixmap.toImage().pixelColor(499,99) == QColor('blue')
    assert left.requests == [(0,0,0,200,100)]
    assert right.requests == [(0,0,0,300,100)]


def test_stacked_monitors_and_gaps_preserve_layout(monkeypatch):
    top = Screen('top',QRect(0,-100,200,100),'red')
    bottom = Screen('bottom',QRect(50,0,150,120),'blue')
    screens(monkeypatch,[top,bottom])
    pixmap, geometry = platform.capture_desktop()
    assert geometry == QRect(0,-100,200,220)
    assert pixmap.toImage().pixelColor(0,219).alpha() == 0
    assert pixmap.toImage().pixelColor(199,219) == QColor('blue')
    assert pixmap.toImage().pixelColor(0,0) == QColor('red')


def test_monitor_choice_captures_only_that_monitor_and_handles_disconnect(monkeypatch):
    left = Screen('left',QRect(-200,0,200,100),'red')
    right = Screen('right',QRect(0,0,300,100),'blue')
    screens(monkeypatch,[left,right])
    pixmap, geometry = platform.capture_desktop('right')
    assert geometry == right.geometry()
    assert pixmap.size() == right.grabWindow(0).size()
    assert not left.requests
    with pytest.raises(RuntimeError,match='no longer available'):
        platform.capture_desktop('disconnected')


def test_mixed_scale_composition_and_global_cropping(monkeypatch):
    left = Screen('left',QRect(-200,-50,200,100),'red',1)
    right = Screen('right',QRect(0,-50,150,100),'blue',2)
    screens(monkeypatch,[left,right])
    pixmap, geometry = platform.capture_desktop()
    assert geometry == QRect(-200,-50,350,100)
    assert pixmap.devicePixelRatio() == 2
    assert pixmap.width() == 700 and pixmap.height() == 200
    cut = platform.crop_desktop(pixmap, geometry, QRect(-10,-40,30,20))
    assert cut.width() == 60 and cut.height() == 40
    assert cut.toImage().pixelColor(0,0) == QColor('red')
    assert cut.toImage().pixelColor(59,0) == QColor('blue')
    single, _ = platform.capture_desktop('left')
    assert single.width() == 200 and single.devicePixelRatio() == 1


def test_fractional_scaling_shares_exact_edges():
    geometry = QRect(-100,0,203,100)
    left = platform.desktop_pixel_rect(geometry,QRect(-100,0,101,100),1.25)
    right = platform.desktop_pixel_rect(geometry,QRect(1,0,102,100),1.25)
    assert left.x()+left.width() == right.x()
    assert right.right()+1 == round(203*1.25)


def test_failed_monitor_does_not_silently_return_partial_capture(monkeypatch):
    failed = Screen('failed',QRect(200,0,100,100),'blue')
    monkeypatch.setattr(failed,'grabWindow',lambda *args: QPixmap())
    screens(monkeypatch,[Screen('first',QRect(0,0,200,100),'red'),failed])
    with pytest.raises(RuntimeError,match='failed'):
        platform.capture_desktop()


def test_region_overlay_uses_whole_screen_not_work_area(monkeypatch):
    screen = QGuiApplication.primaryScreen()
    geometry = QRect(-120,-30,400,300)
    monkeypatch.setattr(screen,'geometry',lambda: geometry)
    monkeypatch.setattr(screen,'availableGeometry',lambda: QRect(-120,-30,400,240))
    image = QImage(400,300,QImage.Format.Format_ARGB32)
    image.fill(QColor('green'))
    for y in range(270,300):
        for x in range(400):
            image.setPixelColor(x,y,QColor('red'))
    selector = Selector(QPixmap.fromImage(image),geometry,screens=[screen])
    selected = []
    selector.selected.connect(selected.append)
    try:
        selector.show()
        overlay = selector.overlays[0]
        app.processEvents()
        assert overlay.geometry() == geometry
        assert overlay.image.size() == image.size()
        assert overlay.image.pixelColor(399,299) == QColor('red')
        if platform.sys.platform.startswith('linux'):
            assert overlay.windowFlags() & Qt.WindowType.X11BypassWindowManagerHint
        for kind, point, button in [(QEvent.Type.MouseButtonPress,QPoint(0,0),Qt.MouseButton.LeftButton),
                                     (QEvent.Type.MouseMove,QPoint(399,299),Qt.MouseButton.NoButton),
                                     (QEvent.Type.MouseButtonRelease,QPoint(399,299),Qt.MouseButton.LeftButton)]:
            event = QMouseEvent(kind,QPointF(point),QPointF(point+geometry.topLeft()),button,
                                Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            app.sendEvent(overlay,event)
        assert selected == [geometry]
        assert not selector.overlays
    finally:
        selector.close()


def test_region_escape_cancels_once_and_releases_overlays():
    screen = QGuiApplication.primaryScreen()
    geometry = screen.geometry()
    image = QImage(geometry.size(),QImage.Format.Format_ARGB32)
    image.fill(QColor('white'))
    selector = Selector(QPixmap.fromImage(image),geometry,screens=[screen])
    cancelled = []
    selector.cancelled.connect(lambda: cancelled.append(True))
    selector.show()
    QTest.keyClick(selector.overlays[0],Qt.Key.Key_Escape)
    selector.cancel()
    assert cancelled == [True] and not selector.overlays


def test_window_picker_shows_thumbnail_grid_and_returns_selected_window(monkeypatch):
    image = QImage(200,100,QImage.Format.Format_ARGB32)
    image.fill(QColor('red'))
    desktop = QPixmap.fromImage(image)
    choices = [('Browser',QRect(0,0,100,100),11),('Terminal',QRect(100,0,100,100),12)]
    monkeypatch.setattr(capture_ui,'window_preview',lambda *args: desktop)
    picker = WindowPicker(choices,desktop,QRect(0,0,200,100))
    try:
        assert picker.grid.viewMode() == QListView.ViewMode.IconMode
        assert picker.grid.count() == 2
        assert all(not picker.grid.item(i).icon().isNull() for i in range(2))
        picker.grid.setCurrentRow(1)
        assert picker.selected_window() == choices[1]
        picker.grid.itemDoubleClicked.emit(picker.grid.item(1))
        assert picker.result() == QDialog.DialogCode.Accepted
    finally:
        picker.close()


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path/'data'))
    window = application.MainWindow()
    window.show()
    app.processEvents()
    yield window
    window.request_quit()
    set_language('en')


def test_monitor_menu_all_monitors_and_specific_selection(window,monkeypatch):
    values = [Screen('left',QRect(-200,0,200,100),'red'),Screen('right',QRect(0,0,300,100),'blue')]
    monkeypatch.setattr(QApplication,'screens',lambda: values)
    monkeypatch.setattr(QApplication,'primaryScreen',lambda: values[0])
    calls = []
    monkeypatch.setattr(window,'capture',lambda *args: calls.append(args))
    window.refresh_monitor_menu()
    actions = [a for a in window.monitor_menu.actions() if not a.isSeparator()]
    actions[0].trigger()
    actions[2].trigger()
    assert calls == [('tela',),('tela','right')]
    assert '300 × 100' in actions[2].text()
    assert 'Primary' in actions[1].text()


def test_window_capture_uses_preview_choice_and_refreshes_window_geometry(window,monkeypatch):
    image = QImage(300,120,QImage.Format.Format_ARGB32)
    image.fill(QColor('blue'))
    pixmap = QPixmap.fromImage(image)
    target = ('Terminal',QRect(-80,10,60,80),42)
    monkeypatch.setattr(application,'capture_desktop',lambda name=None: (pixmap,QRect(-100,0,300,120)))
    monkeypatch.setattr(application,'windows',lambda: [target])
    calls = []
    monkeypatch.setattr(application,'activate_window',lambda wid: calls.append(wid))
    monkeypatch.setattr('screendepresso.macos_backend.capture_window', lambda wid: image.copy(20, 10, 60, 80))
    monkeypatch.setattr(application.QTimer,'singleShot',lambda milliseconds,callback: callback())
    class Picker:
        DialogCode = QDialog.DialogCode
        def __init__(self,*args):
            pass
        def exec(self):
            return self.DialogCode.Accepted
        def selected_window(self):
            return target
        def deleteLater(self):
            pass
    monkeypatch.setattr(application,'WindowPicker',Picker)
    window._capture_pending = True
    window.prepare_capture('janela')
    assert calls == [42]
    assert window.canvas.base.width() == 60 and window.canvas.base.height() == 80
    assert window.canvas.image.pixelColor(0,0) == QColor('blue')
    assert not window._capture_pending


def test_cancelled_window_picker_restores_editor_without_capture(window,monkeypatch):
    image = QImage(300,120,QImage.Format.Format_ARGB32)
    image.fill(QColor('blue'))
    monkeypatch.setattr(application,'capture_desktop',lambda: (QPixmap.fromImage(image),QRect(0,0,300,120)))
    monkeypatch.setattr(application,'windows',lambda: [('Terminal',QRect(0,0,60,80),42)])
    class Picker:
        DialogCode = QDialog.DialogCode
        def __init__(self,*args):
            pass
        def exec(self):
            return self.DialogCode.Rejected
        def deleteLater(self):
            pass
    monkeypatch.setattr(application,'WindowPicker',Picker)
    window.hide()
    window._capture_pending = True
    window.prepare_capture('janela')
    assert window.isVisible() and window.canvas.base.isNull()
    assert not window._capture_pending


def test_region_selection_crosses_monitor_boundaries_and_crops_global_origin():
    image = QImage(500,100,QImage.Format.Format_ARGB32)
    image.fill(QColor('red'))
    geometry = QRect(-200,0,500,100)
    selector = Selector(QPixmap.fromImage(image),geometry,screens=[])
    selected = []
    selector.selected.connect(selected.append)
    selector.begin,selector.end = QPoint(-50,10),QPoint(100,90)
    selector.complete()
    assert selected == [QRect(-50,10,151,81)]
    cropped = platform.crop_desktop(selector.pixmap,geometry,selected[0])
    assert cropped.width() == 151 and cropped.height() == 81
