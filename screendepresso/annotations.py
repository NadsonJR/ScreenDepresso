"""Vector speech balloons and shared text layout for preview and export."""
import math

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import (QColor, QFont, QPainterPath, QTextCharFormat,
                          QTextCursor, QTextDocument, QTextOption)

BUBBLE_STYLES = {'oval': 'Speech', 'rounded': 'Rounded',
                 'thought': 'Thought', 'shout': 'Shout'}


def bubble_path(rect, obj):
    rect = QRectF(rect)
    body = QPainterPath()
    style = obj.get('style', 'oval')
    if style == 'rounded':
        body.addRoundedRect(rect, 15, 15)
    elif style == 'shout':
        center = rect.center()
        for index in range(48):
            angle = index * math.tau / 48
            radius = 1 if index % 2 == 0 else 0.79
            point = center + QPointF(math.cos(angle)*rect.width()*radius/2,
                                     math.sin(angle)*rect.height()*radius/2)
            if index == 0:
                body.moveTo(point)
            else:
                body.lineTo(point)
        body.closeSubpath()
    elif style == 'thought':
        body.addEllipse(rect.adjusted(rect.width()*.05, rect.height()*.05,
                                      -rect.width()*.05, -rect.height()*.05))
        for index in range(12):
            angle = index * math.tau / 12
            center = rect.center() + QPointF(math.cos(angle)*rect.width()*.35,
                                            math.sin(angle)*rect.height()*.35)
            puff = QPainterPath()
            puff.addEllipse(center, rect.width()*.15, rect.height()*.16)
            body = body.united(puff)
    else:
        body.addEllipse(rect)
    tail = QPointF(*obj.get('tail', [rect.right(), rect.bottom()]))
    center = rect.center()
    delta = tail - center
    length = math.hypot(delta.x(), delta.y()) or 1
    if style == 'thought':
        for fraction, radius in ((.75, 6), (.9, 3)):
            dot = QPainterPath()
            dot.addEllipse(center + delta*fraction, radius, radius)
            body = body.united(dot)
    else:
        perpendicular = QPointF(-delta.y()/length, delta.x()/length)
        width = max(4, min(rect.width(), rect.height())*.15)
        triangle = QPainterPath()
        triangle.moveTo(center+perpendicular*width)
        triangle.lineTo(tail)
        triangle.lineTo(center-perpendicular*width)
        triangle.closeSubpath()
        body = body.united(triangle)
    return body


def text_font(obj, zoom=1):
    font = QFont(obj.get('font_family', QFont().family()))
    font.setPixelSize(max(1, round(obj.get('font_size', 24)*zoom)))
    font.setBold(True)
    return font


def text_document(obj, width):
    document = QTextDocument()
    document.setDocumentMargin(2)
    document.setDefaultFont(text_font(obj))
    option = QTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    document.setDefaultTextOption(option)
    document.setPlainText(obj.get('text', ''))
    document.setTextWidth(max(1, width))
    cursor = QTextCursor(document)
    cursor.select(QTextCursor.SelectionType.Document)
    color = QTextCharFormat()
    color.setForeground(QColor(obj.get('color', '#ef233c')))
    cursor.mergeCharFormat(color)
    return document
