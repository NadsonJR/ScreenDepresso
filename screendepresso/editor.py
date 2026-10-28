from .i18n import tr
"""Retained annotations with undo/redo and non-destructive previews."""
import copy
import math
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSignalBlocker, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QFont, QFontMetrics, QLinearGradient
from PySide6.QtWidgets import QWidget, QPlainTextEdit, QApplication
from .annotations import ARROW_STYLES, BUBBLE_STYLES, bubble_path, draw_arrow, text_document, text_font
from .blur import shared_blur, sequential_blur
from .markers import MARKER_STYLES, marker_path, marker_body_hit
from .workspace import IMAGE_SUFFIXES, read_image

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
    marker_color_changed = Signal(str)
    rectangle_color_changed = Signal(str)
    arrow_color_changed = Signal(str)
    bubble_changed = Signal()
    text_format_changed = Signal()
    zoom_changed = Signal(int)
    arrow_style_changed = Signal()
    blur_settings_changed = Signal()
    rectangle_format_changed = Signal()
    marker_style_changed = Signal()
    drop_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.base = QImage()
        self.objects = []
        self.selected = None
        self._tool = 'seta'
        self.text_editor = None
        self.text_index = None
        self.text_state = None
        self.blur_radius = 14
        self.marker_color = '#ef233c'
        self.rectangle_color = '#ef233c'
        self.arrow_color = '#ef233c'
        self.bubble_format = {'style': 'oval', 'fill': '#ffffff', 'outline': '#111827'}
        self.text_format = {'font_family': QFont().family(), 'font_size': 24, 'color': '#ef233c'}
        self.zoom = 1.0
        self.arrow_style = 'classic'
        self.blur_mode = 'shared'
        self.rectangle_format = {'width': 4, 'rounded': False, 'radius': 12}
        self.marker_style = 'circle'
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
        if value == 'seta':
            self.arrow_color_changed.emit(self.arrow_color)
        if value == 'retângulo':
            self.rectangle_color_changed.emit(self.rectangle_color)
            self.rectangle_format_changed.emit()
        if value == 'numero':
            self.marker_style_changed.emit()
        self.setCursor(Qt.CursorShape.OpenHandCursor if value == 'selecionar' else Qt.CursorShape.CrossCursor)

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
        self.sync_size()
        self.update()

    @staticmethod
    def clone_object(obj):
        return {key: QImage(value) if isinstance(value, QImage) else copy.deepcopy(value) for key, value in obj.items()}

    def snapshot(self):
        return (QImage(self.base), [self.clone_object(obj) for obj in self.objects], self.marker_color, self.rectangle_color, self.arrow_color, self.bubble_format.copy(), self.text_format.copy(), self.arrow_style, self.blur_mode, self.blur_radius, self.rectangle_format.copy(), self.marker_style)

    def restore(self, state):
        self.finish_text(False)
        self.base, self.objects, self.marker_color, self.rectangle_color, self.arrow_color, self.bubble_format, self.text_format, self.arrow_style, self.blur_mode, self.blur_radius, self.rectangle_format, self.marker_style = state
        self.selected = None
        self.arrow_color_changed.emit(self.arrow_color)
        self.rectangle_color_changed.emit(self.rectangle_color)
        self.marker_color_changed.emit(self.marker_color)
        self.bubble_changed.emit()
        self.text_format_changed.emit()
        self.arrow_style_changed.emit()
        self.blur_settings_changed.emit()
        self.rectangle_format_changed.emit()
        self.marker_style_changed.emit()
        self.pending = self.before = self.begin = self.end = None
        self.sync_size()
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
        rect = QRect(QPoint(*obj['a']), QPoint(*obj['b'])).normalized()
        return rect.adjusted(-26, -26, 26, 26) if obj['kind'] == 'numero' else rect

    @staticmethod
    def hit_test(obj, point):
        if obj['kind'] == 'balao':
            return bubble_path(Canvas.object_rect(obj), obj).contains(QPointF(point)) or (point-QPoint(*obj['tail'])).manhattanLength() <= 12
        if obj['kind'] != 'numero':
            return Canvas.object_rect(obj).adjusted(-6, -6, 6, 6).contains(point)
        a, b = QPointF(*obj['a']), QPointF(*obj['b'])
        px, py = point.x(), point.y()
        if marker_body_hit(obj, point):
            return True
        dx, dy = b.x()-a.x(), b.y()-a.y()
        length = dx*dx + dy*dy
        t = max(0, min(1, ((px-a.x())*dx+(py-a.y())*dy)/length)) if length else 0
        return math.hypot(px-a.x()-t*dx, py-a.y()-t*dy) <= 8

    def renumber_markers(self):
        number = 1
        for obj in self.objects:
            if obj['kind'] == 'numero':
                obj['number'] = number
                number += 1

    def set_arrow_color(self, color):
        self.finish_text()
        color = QColor(color)
        if not color.isValid():
            return
        obj = self.objects[self.selected] if self.selected is not None else None
        name = color.name()
        if name == self.arrow_color and (obj is None or obj['kind'] != 'seta' or obj.get('color', '#ef233c') == name):
            return
        before = self.snapshot()
        self.arrow_color = name
        if obj is not None and obj['kind'] == 'seta':
            obj['color'] = name
        self.arrow_color_changed.emit(name)
        self.commit(before)

    def set_arrow_style(self, style):
        self.finish_text()
        if style not in ARROW_STYLES:
            return
        before = self.snapshot()
        self.arrow_style = style
        if self.selected is not None and self.objects[self.selected]['kind'] == 'seta':
            self.objects[self.selected]['style'] = style
        if self.snapshot() != before:
            self.arrow_style_changed.emit()
            self.commit(before)

    def set_blur_mode(self, mode):
        if mode not in ('shared', 'sequential') or mode == self.blur_mode:
            return
        self.finish_text()
        before = self.snapshot()
        self.blur_mode = mode
        if mode == 'shared':
            for obj in self.objects:
                if obj['kind'] == 'desfoque':
                    obj['radius'] = self.blur_radius
        self.blur_settings_changed.emit()
        self.commit(before)

    def set_rectangle_color(self, color):
        self.finish_text()
        color = QColor(color)
        if not color.isValid():
            return
        obj = self.objects[self.selected] if self.selected is not None else None
        name = color.name()
        if name == self.rectangle_color and (obj is None or obj['kind'] != 'retângulo' or obj.get('color', '#ef233c') == name):
            return
        before = self.snapshot()
        self.rectangle_color = name
        if obj is not None and obj['kind'] == 'retângulo':
            obj['color'] = name
        self.rectangle_color_changed.emit(name)
        self.commit(before)

    def set_marker_color(self, color):
        self.finish_text()
        color = QColor(color)
        if not color.isValid() or color.name() == self.marker_color:
            return
        before = self.snapshot()
        self.marker_color = color.name()
        self.marker_color_changed.emit(self.marker_color)
        self.commit(before)

    def set_rectangle_format(self, **values):
        self.finish_text()
        if 'width' in values:
            values['width'] = max(1, min(40, int(values['width'])))
        if 'radius' in values:
            values['radius'] = max(1, min(100, int(values['radius'])))
        if 'rounded' in values:
            values['rounded'] = bool(values['rounded'])
        before = self.snapshot()
        self.rectangle_format.update(values)
        if self.selected is not None and self.objects[self.selected]['kind'] == 'retângulo':
            self.objects[self.selected].update(values)
        if self.snapshot() != before:
            self.rectangle_format_changed.emit()
            self.commit(before)

    def set_marker_style(self, style):
        self.finish_text()
        if style not in MARKER_STYLES:
            return
        before = self.snapshot()
        self.marker_style = style
        if self.selected is not None and self.objects[self.selected]['kind'] == 'numero':
            self.objects[self.selected]['style'] = style
        if self.snapshot() != before:
            self.marker_style_changed.emit()
            self.commit(before)

    def set_bubble_format(self, **values):
        self.finish_text()
        if 'style' in values and values['style'] not in BUBBLE_STYLES:
            return
        for name in ('fill', 'outline'):
            if name in values:
                color = QColor(values[name])
                if not color.isValid():
                    return
                values[name] = color.name()
        before = self.snapshot()
        self.bubble_format.update(values)
        if self.selected is not None and self.objects[self.selected]['kind'] == 'balao':
            self.objects[self.selected].update(values)
        if self.snapshot() != before:
            self.bubble_changed.emit()
            self.commit(before)

    def current_text_format(self):
        if self.text_editor is not None:
            return self.text_object
        if self.selected is not None and self.objects[self.selected]['kind'] == 'texto':
            return self.objects[self.selected]
        return self.text_format

    def set_text_format(self, **values):
        if 'font_size' in values:
            values['font_size'] = max(6, min(200, int(values['font_size'])))
        if 'color' in values:
            color = QColor(values['color'])
            if not color.isValid():
                return
            values['color'] = color.name()
        before = self.snapshot()
        self.text_format.update(values)
        if self.text_editor is not None:
            self.text_object.update(values)
            self.refresh_text_editor()
        elif self.selected is not None and self.objects[self.selected]['kind'] == 'texto':
            obj = self.objects[self.selected]
            obj.update(values)
            self.fit_text_object(obj)
            self.ensure_text_space(obj)
        self.text_format_changed.emit()
        if self.text_editor is None and self.snapshot() != before:
            self.commit(before)

    def sync_size(self):
        size = self.base.size()
        if self.text_editor is not None:
            rect = self.object_rect(self.text_object)
            size = size.expandedTo(QSize(rect.right()+1, rect.bottom()+1))
        self.setFixedSize(max(0, round(size.width()*self.zoom)), max(0, round(size.height()*self.zoom)))

    def set_zoom(self, percent):
        percent = max(10, min(400, int(percent)))
        self.zoom = percent/100
        self.sync_size()
        if self.text_editor is not None:
            self.refresh_text_editor()
        self.update()
        self.zoom_changed.emit(percent)

    def image_point(self, event):
        return QPoint(round(event.position().x()/self.zoom), round(event.position().y()/self.zoom))

    def fit_text_object(self, obj):
        rect = self.object_rect(obj)
        metrics = QFontMetrics(text_font(obj))
        text = obj.get('text', '')
        natural = max((metrics.horizontalAdvance(line) for line in text.splitlines()), default=0)+8
        glyph_width = max((metrics.horizontalAdvance(char) for char in text), default=0)+8
        width = max(glyph_width, min(max(40, rect.width(), natural), self.base.width()))
        height = max(rect.height(), math.ceil(text_document(obj, width).size().height())+4)
        x = max(0, min(rect.left(), self.base.width()-width))
        y = max(0, min(rect.top(), self.base.height()-height))
        obj['a'], obj['b'] = [x, y], [x+width-1, y+height-1]

    def ensure_text_space(self, obj):
        rect = self.object_rect(obj)
        width, height = max(self.base.width(), rect.right()+1), max(self.base.height(), rect.bottom()+1)
        if width != self.base.width() or height != self.base.height():
            expanded = QImage(width, height, QImage.Format.Format_ARGB32)
            expanded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(expanded)
            painter.drawImage(0, 0, self.base)
            painter.end()
            self.base = expanded
        self.sync_size()

    def refresh_text_editor(self):
        editor = self.text_editor
        if editor is None:
            return
        self.text_object['text'] = editor.toPlainText()
        self.fit_text_object(self.text_object)
        blocker = QSignalBlocker(editor)
        editor.setFont(text_font(self.text_object, self.zoom))
        color = self.text_object.get('color', '#ef233c')
        editor.setStyleSheet(f'QPlainTextEdit {{ background: rgba(24, 28, 35, 225); color: {color}; border: 1px solid #60a5fa; padding: 0px; selection-background-color: #365d8c; }}')
        editor.setGeometry(round(self.text_object['a'][0]*self.zoom),
                           round(self.text_object['a'][1]*self.zoom),
                           max(1, round(self.object_rect(self.text_object).width()*self.zoom)),
                           max(1, round(self.object_rect(self.text_object).height()*self.zoom)))
        self.sync_size()
        del blocker

    def draw_marker(self, painter, obj):
        center, target = QPointF(*obj['a']), QPointF(*obj['b'])
        color = QColor(self.marker_color)
        painter.setPen(QPen(color, 2.5))
        painter.drawLine(center, target)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(target, 5, 5)
        style = obj.get('style', 'circle')
        if style == 'circle':
            painter.setBrush(QColor(0, 0, 0, 45))
            painter.drawEllipse(center+QPointF(1, 2), 21, 21)
            gradient = QLinearGradient(center.x(), center.y()-20, center.x(), center.y()+20)
            gradient.setColorAt(0, color.lighter(120))
            gradient.setColorAt(1, color.darker(110))
            painter.setBrush(gradient)
        else:
            painter.setBrush(QColor('white') if style == 'outline' else color)
        painter.setPen(QPen(color if style == 'outline' else color.darker(120), 3 if style == 'outline' else 1))
        painter.drawPath(marker_path(style, center))
        font = QFont()
        font.setBold(True)
        size = 23
        number = str(obj['number'])
        while size > 6:
            font.setPixelSize(size)
            if QFontMetrics(font).horizontalAdvance(number) <= (26 if style == 'diamond' else 30):
                break
            size -= 1
        painter.setFont(font)
        luminance = (299*color.red()+587*color.green()+114*color.blue())/1000
        painter.setPen(color if style == 'outline' else QColor('#111827') if luminance > 155 else QColor('white'))
        painter.drawText(QRect(round(center.x())-19, round(center.y())-20, 39, 40), Qt.AlignmentFlag.AlignCenter, number)

    def draw_object(self, image, obj):
        rect = self.object_rect(obj)
        if obj['kind'] == 'desfoque':
            sequential_blur(image, rect, obj['radius'])
            return
        p = QPainter(image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#ef233c'), 4))
        if obj['kind'] == 'numero':
            self.draw_marker(p, obj)
        elif obj['kind'] == 'balao':
            p.setPen(QPen(QColor(obj.get('outline', '#111827')), 3))
            p.setBrush(QColor(obj.get('fill', '#ffffff')))
            p.drawPath(bubble_path(rect.adjusted(2, 2, -2, -2), obj))
        elif obj['kind'] == 'imagem':
            p.drawImage(rect, obj['image'])
        elif obj['kind'] == 'seta':
            draw_arrow(p, obj)
        elif obj['kind'] == 'retângulo':
            width = min(obj.get('width', 4), max(1, min(rect.width()-1, rect.height()-1)))
            p.setPen(QPen(QColor(obj.get('color', '#ef233c')), width, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin))
            shape = QRectF(QPointF(rect.topLeft()), QPointF(rect.bottomRight())).adjusted(width/2, width/2, -width/2, -width/2)
            if obj.get('rounded', False):
                radius = min(obj.get('radius', 12), max(0, shape.width()/2), max(0, shape.height()/2))
                p.drawRoundedRect(shape, radius, radius)
            else:
                p.drawRect(shape)
        elif obj['kind'] == 'texto':
            p.translate(rect.topLeft())
            text_document(obj, rect.width()).drawContents(p)
        p.end()

    def render_image(self, preview=False):
        image = self.base.copy()
        if image.isNull():
            return image
        if self.blur_mode == 'shared':
            regions = [(self.object_rect(obj), obj['radius']) for obj in self.objects if obj['kind'] == 'desfoque']
            if preview and self.pending and self.pending['kind'] == 'desfoque':
                regions.append((self.object_rect(self.pending), self.pending['radius']))
            image = shared_blur(image, regions)
        for index, obj in enumerate(self.objects):
            if self.blur_mode == 'shared' and obj['kind'] == 'desfoque':
                continue
            if not preview or self.text_editor is None or index != self.text_index:
                self.draw_object(image, obj)
        if preview and self.pending and (self.pending['kind'] not in ('recorte', 'texto')) and not (self.blur_mode == 'shared' and self.pending['kind'] == 'desfoque'):
            self.draw_object(image, self.pending)
        return image

    def paintEvent(self, event):
        p = QPainter(self)
        p.scale(self.zoom, self.zoom)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(0, 0, self.render_image(True))
        p.setPen(QPen(QColor('#2563eb'), 1, Qt.PenStyle.DashLine))
        if self.pending and self.pending['kind'] in ('recorte', 'texto'):
            p.drawRect(self.object_rect(self.pending))
        if self.selected is not None and self.selected < len(self.objects):
            obj = self.objects[self.selected]
            if obj['kind'] == 'numero':
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(marker_path(obj.get('style', 'circle'), QPointF(*obj['a']), 23))
            else:
                p.drawRect(self.object_rect(obj))
            p.setBrush(QColor('white'))
            for key in (('b',) if obj['kind'] == 'numero' else ('a', 'b', 'tail') if obj['kind'] == 'balao' else ('a', 'b')):
                point = QPoint(*obj[key])
                p.drawRect(QRect(point - QPoint(5, 5), point + QPoint(5, 5)))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.base.isNull():
            return
        self.finish_text()
        point = self.image_point(event)
        self.begin = self.end = point
        self.before = self.snapshot()
        self.action = None
        selected_marker = self.objects[self.selected] if self.selected is not None else None
        adjust_marker = self.tool == 'numero' and selected_marker is not None and selected_marker['kind'] == 'numero' and (marker_body_hit(selected_marker, point) or (point-QPoint(*selected_marker['b'])).manhattanLength() <= 12)
        if self.tool == 'selecionar' or adjust_marker:
            if self.selected is not None:
                obj = self.objects[self.selected]
                for key in (('b',) if obj['kind'] == 'numero' else ('a', 'b', 'tail') if obj['kind'] == 'balao' else ('a', 'b')):
                    if (point - QPoint(*obj[key])).manhattanLength() <= 12:
                        self.action = key
                        return
            self.selected = next((i for i in reversed(range(len(self.objects))) if self.hit_test(self.objects[i], point)), None)
            if self.selected is not None:
                obj = self.objects[self.selected]
                self.action = 'marker_center' if obj['kind'] == 'numero' and marker_body_hit(obj, point) else 'move'
                if obj['kind'] == 'seta':
                    self.arrow_color_changed.emit(obj.get('color', '#ef233c'))
                    self.arrow_style_changed.emit()
                if obj['kind'] == 'retângulo':
                    self.rectangle_color_changed.emit(obj.get('color', '#ef233c'))
                    self.rectangle_format_changed.emit()
                if obj['kind'] == 'numero':
                    self.marker_style_changed.emit()
                if obj['kind'] == 'balao':
                    self.bubble_changed.emit()
                if obj['kind'] == 'texto':
                    self.text_format_changed.emit()
                if self.objects[self.selected]['kind'] == 'desfoque':
                    self.blur_selected.emit(self.objects[self.selected]['radius'])
            self.update()
            return
        self.selected = None
        self.pending = {'kind': self.tool, 'a': [point.x(), point.y()], 'b': [point.x(), point.y()], 'radius': self.blur_radius}
        if self.tool == 'seta':
            self.pending['color'] = self.arrow_color
            self.pending['style'] = self.arrow_style
        if self.tool == 'retângulo':
            self.pending['color'] = self.rectangle_color
            self.pending.update(self.rectangle_format)
        if self.tool == 'numero':
            self.pending['number'] = 1 + sum(obj['kind'] == 'numero' for obj in self.objects)
            self.pending['style'] = self.marker_style
        if self.tool == 'balao':
            self.pending.update(self.bubble_format)
            self.pending['tail'] = [point.x(), point.y()]

    def mouseMoveEvent(self, event):
        if self.begin is None:
            return
        point = self.image_point(event)
        point.setX(max(0, min(point.x(), self.base.width() - 1)))
        point.setY(max(0, min(point.y(), self.base.height() - 1)))
        if self.pending:
            self.pending['b'] = [point.x(), point.y()]
            if self.pending['kind'] == 'balao':
                rect = self.object_rect(self.pending)
                self.pending['tail'] = [max(0, min(self.base.width()-1, rect.center().x()-rect.width()//3)),
                                        min(self.base.height()-1, rect.bottom()+max(15, rect.height()//3))]
        elif self.action and self.selected is not None:
            obj = self.objects[self.selected]
            if self.action == 'marker_center':
                old = self.before[1][self.selected]
                delta = point-self.begin
                obj['a'] = [max(0, min(self.base.width()-1, old['a'][0]+delta.x())), max(0, min(self.base.height()-1, old['a'][1]+delta.y()))]
            elif self.action == 'move':
                old = self.before[1][self.selected]
                delta = point - self.begin
                keys = ('a', 'b', 'tail') if obj['kind'] == 'balao' else ('a', 'b')
                dx = max(-min(old[k][0] for k in keys), min(delta.x(), self.base.width() - 1 - max(old[k][0] for k in keys)))
                dy = max(-min(old[k][1] for k in keys), min(delta.y(), self.base.height() - 1 - max(old[k][1] for k in keys)))
                for key in keys:
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
            obj = {'kind': 'texto', 'a': [rect.left(), rect.top()], 'b': [rect.right(), rect.bottom()], 'text': '', **self.text_format}
            before = self.before
            self.pending = self.before = self.begin = self.end = None
            self.start_text(obj, before=before)
            self.update()
            return
        if self.pending:
            rect = self.object_rect(self.pending).intersected(self.base.rect())
            if self.pending['kind'] == 'numero' or (self.pending['kind'] == 'seta' and (self.end - self.begin).manhattanLength() > 3) or (rect.width() > 2 and rect.height() > 2):
                if self.pending['kind'] == 'recorte':
                    self.base = self.base.copy(rect)
                    for obj in self.objects:
                        for key in (('a', 'b', 'tail') if obj['kind'] == 'balao' else ('a', 'b')):
                            obj[key] = [obj[key][0] - rect.x(), obj[key][1] - rect.y()]
                    self.sync_size()
                else:
                    if self.pending['kind'] == 'numero' and (self.end-self.begin).manhattanLength() < 4:
                        a = self.pending['a']
                        self.pending['b'] = [max(0, min(self.base.width()-1, a[0]+(36 if a[0]+36 < self.base.width() else -36))), max(0, min(self.base.height()-1, a[1]+(36 if a[1]+36 < self.base.height() else -36)))]
                    self.objects.append(self.clone_object(self.pending))
                    self.selected = len(self.objects) - 1
                changed = True
        elif self.action and self.objects != self.before[1]:
            if self.objects[self.selected]['kind'] == 'texto':
                self.fit_text_object(self.objects[self.selected])
                self.ensure_text_space(self.objects[self.selected])
            changed = True
        if changed:
            self.commit(self.before)
        self.pending = self.before = self.begin = self.end = None
        self.update()

    def set_blur_radius(self, value):
        before = self.snapshot()
        self.blur_radius = value
        if self.blur_mode == 'shared':
            for obj in self.objects:
                if obj['kind'] == 'desfoque':
                    obj['radius'] = value
        elif self.selected is not None and self.objects[self.selected]['kind'] == 'desfoque':
            self.objects[self.selected]['radius'] = value
        if self.objects != before[1]:
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
        editor.setPlaceholderText(tr('Type here…'))
        editor.setToolTip(tr('Ctrl+Enter confirms • Esc cancels • Click outside to confirm'))
        editor.document().setDocumentMargin(2)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor.setPlainText(obj.get('text', ''))
        editor.textChanged.connect(self.refresh_text_editor)
        self.refresh_text_editor()
        editor.show()
        editor.setFocus()
        editor.selectAll()
        self.text_format_changed.emit()
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
            self.fit_text_object(obj)
            self.ensure_text_space(obj)
            if index is None:
                self.objects.append(obj)
                self.selected = len(self.objects) - 1
            else:
                self.objects[index] = obj
                self.selected = index
            if self.objects != before[1]:
                self.commit(before)
        self.setCursor(Qt.CursorShape.OpenHandCursor if self.tool == 'selecionar' else Qt.CursorShape.CrossCursor)
        self.sync_size()
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.tool != 'selecionar':
            return
        point = self.image_point(event)
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
            self.renumber_markers()
            self.selected = None
            self.commit(before)

    @staticmethod
    def can_drop(mime):
        if mime.hasImage():
            return True
        from pathlib import Path
        return any(url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES for url in mime.urls())

    def drop_mime(self, mime, position):
        image = QImage()
        if mime.hasImage():
            data = mime.imageData()
            image = data.toImage() if hasattr(data, 'toImage') else QImage(data) if isinstance(data, QImage) else QImage()
        if image.isNull():
            for url in mime.urls():
                if url.isLocalFile():
                    image = read_image(url.toLocalFile())
                    if not image.isNull():
                        break
        if image.isNull():
            self.drop_failed.emit(tr('Could not open the dropped image.'))
            return False
        return self.paste_image(image, position)

    def dragEnterEvent(self, event):
        if self.can_drop(event.mimeData()):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        if self.can_drop(event.mimeData()) and self.drop_mime(event.mimeData(), self.image_point(event)):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def paste_image(self, image=None, position=None):
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
        if position is not None:
            x = max(0, min(round(position.x()-width/2), self.base.width()-width))
            y = max(0, min(round(position.y()-height/2), self.base.height()-height))
        pasted = image.convertToFormat(QImage.Format.Format_ARGB32)
        pasted.setDevicePixelRatio(1)
        self.objects.append({'kind': 'imagem', 'a': [x, y], 'b': [x + width - 1, y + height - 1], 'image': pasted})
        self.selected = len(self.objects) - 1
        self.tool = 'selecionar'
        self.commit(before)
        return True
