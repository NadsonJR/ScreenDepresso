from .i18n import tr
"""Retained annotations with undo/redo and non-destructive previews."""
import copy
import math
from PIL import Image, ImageFilter
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QPlainTextEdit, QApplication

class InlineTextEdit(QPlainTextEdit):

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.parent().finish_text(False)
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.parent().finish_text()
        elif event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier and QApplication.clipboard().mimeData().hasImage():
            self.parent().paste_image()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.parent().finish_text()

class Canvas(QWidget):
    changed = Signal()
    blur_selected = Signal(int)
    tool_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.base = QImage()
        self.objects = []
        self.selected = None
        self._tool = 'seta'
        self.text_editor = None
        self.text_index = None
        self.text_state = None
        self.blur_radius = 14
        self.begin = self.end = None
        self.pending = None
        self.action = None
        self.before = None
        self.undo_stack = []
        self.redo_stack = []

    @property
    def tool(self):
        return self._tool

    @tool.setter
    def tool(self, value):
        self.finish_text()
        self._tool = value
        self.tool_changed.emit(value)
        self.setCursor(Qt.CursorShape.ArrowCursor if value == 'selecionar' else Qt.CursorShape.CrossCursor)

    @property
    def image(self):
        return self.render_image()

    def load(self, image):
        self.finish_text()
        self.base = image.convertToFormat(QImage.Format.Format_ARGB32)
        self.base.setDevicePixelRatio(1.0)
        self.objects = []
        self.selected = None
        self.begin = self.end = self.pending = self.before = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.setFixedSize(self.base.size())
        self.update()

    @staticmethod
    def clone_object(obj):
        return {key: QImage(value) if isinstance(value, QImage) else copy.deepcopy(value) for key, value in obj.items()}

    def snapshot(self):
        return (QImage(self.base), [self.clone_object(obj) for obj in self.objects])

    def restore(self, state):
        self.finish_text(False)
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
        if self.text_editor is not None:
            self.text_editor.undo()
            return
        if self.before is not None:
            self.restore(self.before)
        elif self.undo_stack:
            self.redo_stack.append(self.snapshot())
            self.restore(self.undo_stack.pop())

    def redo(self):
        if self.text_editor is not None:
            self.text_editor.redo()
            return
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
        if obj['kind'] == 'imagem':
            p.drawImage(rect, obj['image'])
        elif obj['kind'] == 'seta':
            a, b = (QPoint(*obj['a']), QPoint(*obj['b']))
            p.drawLine(a, b)
            angle = math.atan2(b.y() - a.y(), b.x() - a.x())
            for offset in (-0.5, 0.5):
                p.drawLine(b, QPoint(round(b.x() - 20 * math.cos(angle + offset)), round(b.y() - 20 * math.sin(angle + offset))))
        elif obj['kind'] == 'retângulo':
            p.drawRect(rect.adjusted(2, 2, -2, -2))
        elif obj['kind'] == 'texto':
            font = QFont()
            font.setPixelSize(obj.get('font_size', 24))
            font.setBold(True)
            p.setFont(font)
            p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, obj.get('text', ''))
        p.end()

    def render_image(self, preview=False):
        image = self.base.copy()
        if image.isNull():
            return image
        for index, obj in enumerate(self.objects):
            if not preview or self.text_editor is None or index != self.text_index:
                self.draw_object(image, obj)
        if preview and self.pending and (self.pending['kind'] not in ('recorte', 'texto')):
            self.draw_object(image, self.pending)
        return image

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawImage(0, 0, self.render_image(True))
        p.setPen(QPen(QColor('#2563eb'), 1, Qt.PenStyle.DashLine))
        if self.pending and self.pending['kind'] in ('recorte', 'texto'):
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
        self.finish_text()
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

    def mouseMoveEvent(self, event):
        if self.begin is None:
            return
        point = event.position().toPoint()
        point.setX(max(0, min(point.x(), self.base.width() - 1)))
        point.setY(max(0, min(point.y(), self.base.height() - 1)))
        if self.pending:
            self.pending['b'] = [point.x(), point.y()]
        elif self.action and self.selected is not None:
            obj = self.objects[self.selected]
            if self.action == 'move':
                old = self.before[1][self.selected]
                delta = point - self.begin
                dx = max(-min(old['a'][0], old['b'][0]), min(delta.x(), self.base.width() - 1 - max(old['a'][0], old['b'][0])))
                dy = max(-min(old['a'][1], old['b'][1]), min(delta.y(), self.base.height() - 1 - max(old['a'][1], old['b'][1])))
                for key in ('a', 'b'):
                    obj[key] = [old[key][0] + dx, old[key][1] + dy]
            else:
                obj[self.action] = [point.x(), point.y()]
        self.end = point
        self.update()

    def mouseReleaseEvent(self, event):
        if self.begin is None or event.button() != Qt.MouseButton.LeftButton:
            return
        self.mouseMoveEvent(event)
        changed = False
        if self.pending and self.pending['kind'] == 'texto':
            rect = self.object_rect(self.pending).intersected(self.base.rect())
            if rect.width() < 12 or rect.height() < 12:
                rect = QRect(self.begin, QPoint(min(self.base.width() - 1, self.begin.x() + 240), min(self.base.height() - 1, self.begin.y() + 80)))
            obj = {'kind': 'texto', 'a': [rect.left(), rect.top()], 'b': [rect.right(), rect.bottom()], 'text': '', 'font_size': 24}
            before = self.before
            self.pending = self.before = self.begin = self.end = None
            self.start_text(obj, before=before)
            self.update()
            return
        if self.pending:
            rect = self.object_rect(self.pending).intersected(self.base.rect())
            if self.pending['kind'] == 'seta' and (self.end - self.begin).manhattanLength() > 3 or (rect.width() > 2 and rect.height() > 2):
                if self.pending['kind'] == 'recorte':
                    self.base = self.base.copy(rect)
                    for obj in self.objects:
                        for key in ('a', 'b'):
                            obj[key] = [obj[key][0] - rect.x(), obj[key][1] - rect.y()]
                    self.setFixedSize(self.base.size())
                else:
                    self.objects.append(self.clone_object(self.pending))
                    self.selected = len(self.objects) - 1
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

    def start_text(self, obj, index=None, before=None):
        self.finish_text()
        self.text_state = before if before is not None else self.snapshot()
        self.text_index = index
        self.text_object = self.clone_object(obj)
        editor = InlineTextEdit(self)
        self.text_editor = editor
        editor.setObjectName('inlineText')
        editor.setFrameStyle(0)
        editor.setStyleSheet('QPlainTextEdit { background: rgba(24, 28, 35, 225); color: #ef233c; border: 1px solid #60a5fa; padding: 0px; selection-background-color: #365d8c; }')
        editor.setPlaceholderText(tr('Type here…'))
        editor.setToolTip(tr('Ctrl+Enter confirms • Esc cancels • Click outside to confirm'))
        font = QFont()
        font.setPixelSize(obj.get('font_size', 24))
        font.setBold(True)
        editor.setFont(font)
        editor.document().setDocumentMargin(0)
        editor.setGeometry(self.object_rect(obj).intersected(self.base.rect()))
        editor.setPlainText(obj.get('text', ''))
        editor.show()
        editor.setFocus()
        editor.selectAll()
        self.update()

    def finish_text(self, accept=True):
        editor = self.text_editor
        if editor is None:
            return
        self.text_editor = None
        text = editor.toPlainText()
        editor.hide()
        editor.deleteLater()
        before = self.text_state
        index = self.text_index
        self.text_state = self.text_index = None
        if accept and text.strip():
            obj = self.text_object
            obj['text'] = text
            if index is None:
                self.objects.append(obj)
                self.selected = len(self.objects) - 1
            else:
                self.objects[index] = obj
                self.selected = index
            if self.objects != before[1]:
                self.commit(before)
        self._tool = 'selecionar'
        self.tool_changed.emit('selecionar')
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mouseDoubleClickEvent(self, event):
        point = event.position().toPoint()
        index = next((i for i in reversed(range(len(self.objects))) if self.objects[i]['kind'] == 'texto' and self.object_rect(self.objects[i]).contains(point)), None)
        if index is not None:
            self.pending = self.before = self.begin = self.end = None
            self.selected = index
            self.start_text(self.objects[index], index)

    def delete_selected(self):
        self.finish_text()
        if self.selected is not None:
            before = self.snapshot()
            del self.objects[self.selected]
            self.selected = None
            self.commit(before)

    def paste_image(self, image=None):
        self.finish_text()
        image = QApplication.clipboard().image() if image is None else image
        if image.isNull():
            return False
        if self.base.isNull():
            self.load(image)
            self.changed.emit()
            return True
        before = self.snapshot()
        ratio = min(1.0, self.base.width() / image.width(), self.base.height() / image.height())
        width, height = (max(1, round(image.width() * ratio)), max(1, round(image.height() * ratio)))
        x, y = ((self.base.width() - width) // 2, (self.base.height() - height) // 2)
        pasted = image.convertToFormat(QImage.Format.Format_ARGB32)
        pasted.setDevicePixelRatio(1)
        self.objects.append({'kind': 'imagem', 'a': [x, y], 'b': [x + width - 1, y + height - 1], 'image': pasted})
        self.selected = len(self.objects) - 1
        self.tool = 'selecionar'
        self.commit(before)
        return True
