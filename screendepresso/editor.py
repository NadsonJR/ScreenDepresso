"""Retained annotations with undo/redo and non-destructive previews."""
import copy
import math

from PIL import Image, ImageFilter
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QInputDialog


class Canvas(QWidget):
    changed = Signal()
    blur_selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.base = QImage()
        self.objects = []
        self.selected = None
        self.tool = 'seta'
        self.blur_radius = 14
        self.begin = self.end = None
        self.pending = None
        self.action = None
        self.before = None
        self.undo_stack = []
        self.redo_stack = []

    @property
    def image(self):
        return self.render_image()

    def load(self, image):
        self.base = image.convertToFormat(QImage.Format.Format_ARGB32)
        self.base.setDevicePixelRatio(1.0)
        self.objects = []
        self.selected = None
        self.begin = self.end = self.pending = self.before = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.setFixedSize(self.base.size())
        self.update()

    def snapshot(self):
        return QImage(self.base), copy.deepcopy(self.objects)

    def restore(self, state):
        self.base, self.objects = state
        self.selected = None
        self.pending = self.before = self.begin = self.end = None
        self.setFixedSize(self.base.size())
        self.update()
        self.changed.emit()

    def commit(self, before):
        self.undo_stack.append(before)
        self.redo_stack.clear()
        self.update()
        self.changed.emit()

    def undo(self):
        if self.before is not None:
            self.restore(self.before)
        elif self.undo_stack:
            self.redo_stack.append(self.snapshot())
            self.restore(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack and self.before is None:
            self.undo_stack.append(self.snapshot())
            self.restore(self.redo_stack.pop())

    @staticmethod
    def object_rect(obj):
        return QRect(QPoint(*obj['a']), QPoint(*obj['b'])).normalized()

    def draw_object(self, image, obj):
        rect = self.object_rect(obj)
        if obj['kind'] == 'desfoque':
            part = image.convertToFormat(QImage.Format.Format_RGBA8888)
            pil = Image.frombytes('RGBA', (part.width(), part.height()), bytes(part.bits()), 'raw', 'RGBA', part.bytesPerLine())
            data = pil.filter(ImageFilter.GaussianBlur(obj['radius'])).tobytes()
            blurred = QImage(data, part.width(), part.height(), part.width() * 4, QImage.Format.Format_RGBA8888).copy()
            original = image.copy(rect)
            p = QPainter(image)
            p.drawImage(0, 0, blurred)
            p.drawImage(rect.topLeft(), original)
            p.end()
            return
        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#ef233c'), 4))
        if obj['kind'] == 'seta':
            a, b = QPoint(*obj['a']), QPoint(*obj['b'])
            p.drawLine(a, b)
            angle = math.atan2(b.y() - a.y(), b.x() - a.x())
            for offset in (-0.5, 0.5):
                p.drawLine(b, QPoint(round(b.x() - 20 * math.cos(angle + offset)), round(b.y() - 20 * math.sin(angle + offset))))
        elif obj['kind'] == 'retângulo':
            p.drawRect(rect.adjusted(2, 2, -2, -2))
        elif obj['kind'] == 'texto':
            font = QFont()
            font.setPixelSize(max(8, rect.height() - 4))
            font.setBold(True)
            p.setFont(font)
            p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, obj['text'])
        p.end()

    def render_image(self, preview=False):
        image = self.base.copy()
        if image.isNull():
            return image
        for obj in self.objects:
            self.draw_object(image, obj)
        if preview and self.pending and self.pending['kind'] != 'recorte':
            self.draw_object(image, self.pending)
        return image

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawImage(0, 0, self.render_image(True))
        p.setPen(QPen(QColor('#2563eb'), 1, Qt.PenStyle.DashLine))
        if self.pending and self.pending['kind'] == 'recorte':
            p.drawRect(self.object_rect(self.pending))
        if self.selected is not None and self.selected < len(self.objects):
            obj = self.objects[self.selected]
            p.drawRect(self.object_rect(obj))
            p.setBrush(QColor('white'))
            for key in ('a', 'b'):
                point = QPoint(*obj[key])
                p.drawRect(QRect(point - QPoint(5, 5), point + QPoint(5, 5)))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.base.isNull():
            return
        point = event.position().toPoint()
        self.begin = self.end = point
        self.before = self.snapshot()
        self.action = None
        if self.tool == 'selecionar':
            if self.selected is not None:
                obj = self.objects[self.selected]
                for key in ('a', 'b'):
                    if (point - QPoint(*obj[key])).manhattanLength() <= 12:
                        self.action = key
                        return
            self.selected = next((i for i in reversed(range(len(self.objects))) if self.object_rect(self.objects[i]).adjusted(-6, -6, 6, 6).contains(point)), None)
            if self.selected is not None:
                self.action = 'move'
                if self.objects[self.selected]['kind'] == 'desfoque':
                    self.blur_selected.emit(self.objects[self.selected]['radius'])
            self.update()
            return
        self.selected = None
        self.pending = {'kind': self.tool, 'a': [point.x(), point.y()], 'b': [point.x(), point.y()], 'radius': self.blur_radius}
        if self.tool == 'texto':
            text, ok = QInputDialog.getText(self, 'Texto', 'Texto da anotação:')
            if ok and text:
                self.pending.update(text=text, b=[min(self.base.width()-1, point.x()+max(100, len(text)*16)), min(self.base.height()-1, point.y()+32)])
                self.objects.append(self.pending)
                self.selected = len(self.objects)-1
                self.tool = 'selecionar'
                self.commit(self.before)
            self.pending = self.before = self.begin = self.end = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.begin is None:
            return
        point = event.position().toPoint()
        point.setX(max(0, min(point.x(), self.base.width()-1)))
        point.setY(max(0, min(point.y(), self.base.height()-1)))
        if self.pending:
            self.pending['b'] = [point.x(), point.y()]
        elif self.action and self.selected is not None:
            obj = self.objects[self.selected]
            if self.action == 'move':
                old = self.before[1][self.selected]
                delta = point - self.begin
                dx = max(-min(old['a'][0], old['b'][0]), min(delta.x(), self.base.width()-1-max(old['a'][0], old['b'][0])))
                dy = max(-min(old['a'][1], old['b'][1]), min(delta.y(), self.base.height()-1-max(old['a'][1], old['b'][1])))
                for key in ('a', 'b'):
                    obj[key] = [old[key][0]+dx, old[key][1]+dy]
            else:
                obj[self.action] = [point.x(), point.y()]
        self.end = point
        self.update()

    def mouseReleaseEvent(self, event):
        if self.begin is None or event.button() != Qt.MouseButton.LeftButton:
            return
        self.mouseMoveEvent(event)
        changed = False
        if self.pending:
            rect = self.object_rect(self.pending).intersected(self.base.rect())
            # Horizontal and vertical arrows are valid too.
            if (self.pending['kind'] == 'seta' and (self.end-self.begin).manhattanLength() > 3) or (rect.width()>2 and rect.height()>2):
                if self.pending['kind'] == 'recorte':
                    self.base = self.base.copy(rect)
                    for obj in self.objects:
                        for key in ('a', 'b'):
                            obj[key] = [obj[key][0]-rect.x(), obj[key][1]-rect.y()]
                    self.setFixedSize(self.base.size())
                else:
                    self.objects.append(copy.deepcopy(self.pending))
                    self.selected = len(self.objects)-1
                    self.tool = 'selecionar'
                changed = True
        elif self.action and self.objects != self.before[1]:
            changed = True
        if changed:
            self.commit(self.before)
        self.pending = self.before = self.begin = self.end = None
        self.update()

    def set_blur_radius(self, value):
        self.blur_radius = value
        if self.selected is not None and self.objects[self.selected]['kind'] == 'desfoque':
            if self.objects[self.selected]['radius'] != value:
                before = self.snapshot()
                self.objects[self.selected]['radius'] = value
                self.commit(before)

    def mouseDoubleClickEvent(self, event):
        if self.selected is not None and self.objects[self.selected]['kind'] == 'texto':
            obj = self.objects[self.selected]
            text, ok = QInputDialog.getText(self, 'Editar texto', 'Texto:', text=obj['text'])
            if ok and text and text != obj['text']:
                before = self.snapshot()
                obj['text'] = text
                self.commit(before)

    def delete_selected(self):
        if self.selected is not None:
            before = self.snapshot()
            del self.objects[self.selected]
            self.selected = None
            self.commit(before)
