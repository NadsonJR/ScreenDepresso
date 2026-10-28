"""Open captures keep independent canvases, edit history and scroll positions."""
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QScrollArea, QTabWidget

from .editor import Canvas
from .i18n import tr


class CaptureScrollArea(QScrollArea):
    def __init__(self):
        super().__init__()
        self.wheel_steps = 0.0

    def set_zoom(self, percent, anchor=None):
        canvas = self.widget()
        anchor = QPointF(anchor if anchor is not None else self.viewport().rect().center())
        point = (anchor-QPointF(canvas.pos()))/canvas.zoom
        canvas.set_zoom(percent)
        offset = QPointF(canvas.pos())+point*canvas.zoom-anchor
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()+round(offset.x()))
        self.verticalScrollBar().setValue(self.verticalScrollBar().value()+round(offset.y()))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            super().wheelEvent(event)
            return
        if self.widget().base.isNull():
            event.ignore()
            return
        delta = event.angleDelta().y()/120 if event.angleDelta().y() else event.pixelDelta().y()/60
        self.wheel_steps += delta
        steps = int(self.wheel_steps)
        if steps:
            self.wheel_steps -= steps
            self.set_zoom(round(self.widget().zoom*100)+steps*10, event.position())
        event.accept()


class CaptureTabs(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('captureTabs')
        self.setDocumentMode(True)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setUsesScrollButtons(True)
        self.tabBar().setExpanding(False)
        self.tabBar().setElideMode(Qt.TextElideMode.ElideMiddle)
        self.next_number = 1
        self.add_document()

    @property
    def canvas(self):
        return self.currentWidget().widget()

    def add_document(self, image=None, path=None, capture=False):
        page = CaptureScrollArea()
        page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canvas = Canvas()
        page.setWidget(canvas)
        page.source_path = Path(path).resolve() if path is not None else None
        page.export_name = None
        page.is_capture = capture
        page.number = self.next_number
        self.next_number += 1
        if image is not None:
            canvas.load(image)
        page.saved_state = canvas.snapshot()
        canvas.changed.connect(lambda: self.update_title(page))
        self.addTab(page, '')
        self.update_title(page)
        self.setCurrentWidget(page)
        return canvas

    def is_dirty(self, page):
        return not page.widget().base.isNull() and page.widget().snapshot() != page.saved_state

    def update_title(self, page):
        index = self.indexOf(page)
        if index < 0:
            return
        name = page.export_name
        if not name:
            if page.widget().base.isNull():
                name = tr('New capture')
            elif page.source_path is not None and not page.is_capture:
                name = page.source_path.name
            else:
                name = tr('Capture {number}').format(number=page.number)
        self.setTabText(index, name + (' *' if self.is_dirty(page) else ''))
        self.setTabToolTip(index, str(page.source_path) if page.source_path else name)
        self.tabBar().setVisible(any(not self.widget(i).widget().base.isNull() for i in range(self.count())))

    def retranslate(self):
        self.setToolTip(tr('Switch between captures. Drag tabs to reorder.'))
        for index in range(self.count()):
            self.update_title(self.widget(index))

    def open_image(self, image, path=None, capture=False):
        self.canvas.finish_text()
        source = Path(path).resolve() if path is not None else None
        if source is not None:
            for index in range(self.count()):
                if self.widget(index).source_path == source:
                    self.setCurrentIndex(index)
                    return self.canvas
        # Reuse the initial empty tab, but never replace an existing capture.
        if self.count() == 1 and self.canvas.base.isNull():
            page = self.currentWidget()
            self.canvas.load(image)
            page.source_path = source
            page.is_capture = capture
            page.saved_state = self.canvas.snapshot()
            self.update_title(page)
            return self.canvas
        return self.add_document(image, source, capture)

    def mark_saved(self, path):
        page = self.currentWidget()
        page.saved_state = self.canvas.snapshot()
        page.export_name = Path(path).name
        self.update_title(page)

    def remove_document(self, index):
        page = self.widget(index)
        self.removeTab(index)
        page.deleteLater()
        if not self.count():
            self.add_document()

    def cycle(self, direction):
        self.setCurrentIndex((self.currentIndex() + direction) % self.count())
