"""Dark desktop palette and original toolbar icons."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QFont, QPalette, QPainterPath

from .theme import TOKENS, stylesheet

STYLE = stylesheet()


def icon(symbol, color=None, plate=True, size=48):
    color = color or TOKENS['accent']
    if color == 'transparent':
        plate, color = False, TOKENS['secondary']
    result = QIcon()
    for scale in (1, 2):
        result.addPixmap(_icon_pixmap(symbol, color, plate, scale, size))
        if not plate:
            selected = _icon_pixmap(symbol, TOKENS['text'], False, scale, size)
            result.addPixmap(selected, QIcon.Mode.Normal, QIcon.State.On)
            result.addPixmap(selected, QIcon.Mode.Active, QIcon.State.On)
    return result


def _icon_pixmap(symbol, color, plate, scale, size):
    pixmap = QPixmap(size*scale, size*scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.scale(scale*size/48, scale*size/48)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color) if plate else Qt.BrushStyle.NoBrush)
    if plate:
        p.drawRoundedRect(QRectF(2, 2, 44, 44), 8, 8)
    ink = TOKENS['text'] if plate else color
    pen = QPen(QColor(ink), 2.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    if symbol in ('undo', 'redo'):
        p.setBrush(Qt.BrushStyle.NoBrush)
        if symbol == 'redo':
            p.translate(48, 0)
            p.scale(-1, 1)
        path = QPainterPath(QPointF(13, 19))
        path.lineTo(28, 19)
        path.cubicTo(39, 19, 39, 35, 28, 35)
        path.lineTo(22, 35)
        p.drawPath(path)
        p.drawPolyline([QPointF(20, 12), QPointF(12, 19), QPointF(20, 26)])
    elif symbol in ('monitor', 'window', 'region', 'image', 'folder', 'workspace', 'settings', 'camera'):
        p.setBrush(Qt.BrushStyle.NoBrush)
        if symbol == 'monitor':
            p.drawRoundedRect(QRectF(9, 11, 30, 22), 2, 2)
            p.drawLine(24, 33, 24, 39)
            p.drawLine(17, 39, 31, 39)
        elif symbol == 'window':
            p.drawRoundedRect(QRectF(10, 11, 28, 27), 3, 3)
            p.drawLine(10, 18, 38, 18)
            for x in (15, 20, 25):
                p.drawPoint(x, 15)
        elif symbol == 'region':
            pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(12, 12, 24, 24)
            p.setPen(QPen(QColor(ink), 2.5))
            for x in (12, 36):
                for y in (12, 36):
                    p.fillRect(QRectF(x-3, y-3, 6, 6), QColor(ink))
        elif symbol == 'workspace':
            for y in (13, 24, 35):
                p.drawRect(10, y-2, 4, 4)
                p.drawLine(21, y, 38, y)
        elif symbol == 'settings':
            import math
            gear = QPainterPath()
            for i in range(32):
                angle = math.pi*2*i/32
                radius = 17 if i % 4 in (1, 2) else 13
                point = QPointF(24+radius*math.cos(angle), 24+radius*math.sin(angle))
                gear.moveTo(point) if i == 0 else gear.lineTo(point)
            gear.closeSubpath()
            p.drawPath(gear)
            p.drawEllipse(QRectF(20, 20, 8, 8))
        elif symbol == 'folder':
            path = QPainterPath(QPointF(9, 15))
            for x, y in ((20,15), (24,19), (39,19), (39,36), (9,36), (9,15)):
                path.lineTo(x,y)
            p.drawPath(path)
        elif symbol == 'camera':
            p.drawRoundedRect(QRectF(9, 15, 30, 23), 4, 4)
            p.drawPolyline([QPointF(16, 15), QPointF(19, 10), QPointF(29, 10), QPointF(32, 15)])
            p.drawEllipse(QRectF(18, 20, 12, 12))
        else:
            p.drawRoundedRect(QRectF(7, 8, 34, 32), 3, 3)
            p.drawEllipse(QRectF(29, 14, 5, 5))
            p.drawPolyline([QPointF(9, 35), QPointF(19, 24), QPointF(27, 31), QPointF(32, 26), QPointF(39, 35)])
    elif symbol == 'refresh':
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(11, 11, 26, 26), 40*16, 285*16)
        p.drawPolyline([QPointF(27, 10), QPointF(35, 13), QPointF(34, 22)])
    elif symbol == 'save':
        path = QPainterPath()
        path.moveTo(12, 10)
        path.lineTo(30, 10)
        path.lineTo(36, 16)
        path.lineTo(36, 37)
        path.lineTo(12, 37)
        path.closeSubpath()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.drawRect(17, 10, 12, 10)
        p.drawRect(17, 27, 14, 10)
        p.drawLine(25, 13, 25, 17)
    elif symbol == 'copy':
        # Two overlapping sheets with folded corners, like the reference.
        p.setBrush(QColor(color) if plate else QColor(TOKENS['surface']))
        back = QPainterPath()
        back.moveTo(20, 8)
        back.lineTo(28, 8)
        back.lineTo(38, 18)
        back.lineTo(38, 31)
        back.quadTo(38, 34, 35, 34)
        back.lineTo(20, 34)
        back.quadTo(17, 34, 17, 31)
        back.lineTo(17, 11)
        back.quadTo(17, 8, 20, 8)
        p.drawPath(back)
        p.drawLine(28, 8, 28, 18)
        p.drawLine(28, 18, 38, 18)
        front = QPainterPath()
        front.moveTo(12, 16)
        front.lineTo(20, 16)
        front.lineTo(30, 26)
        front.lineTo(30, 38)
        front.quadTo(30, 41, 27, 41)
        front.lineTo(12, 41)
        front.quadTo(9, 41, 9, 38)
        front.lineTo(9, 19)
        front.quadTo(9, 16, 12, 16)
        p.drawPath(front)
        fold = QPainterPath()
        fold.moveTo(20, 16)
        fold.lineTo(20, 22)
        fold.quadTo(20, 26, 24, 26)
        fold.lineTo(30, 26)
        p.drawPath(fold)
    elif symbol == 'paste':
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(11, 10, 26, 29), 3, 3)
        p.setBrush(QColor(color) if plate else QColor(TOKENS['surface']))
        p.drawRoundedRect(QRectF(18, 7, 12, 7), 2, 2)
        p.drawLine(17, 23, 31, 23)
        p.drawLine(17, 29, 28, 29)
    elif symbol.startswith('bubble:'):
        from .annotations import bubble_path
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(bubble_path(QRectF(9, 10, 30, 23), {'style': symbol.split(':')[1], 'tail': [17, 40]}))
    elif symbol == 'hand':
        hand = QPainterPath()
        hand.moveTo(18, 37)
        hand.cubicTo(15, 33, 12, 28, 10, 25)
        hand.cubicTo(8, 21, 11, 19, 14, 22)
        hand.lineTo(17, 26)
        hand.lineTo(16, 14)
        hand.cubicTo(16, 10, 20, 10, 20, 14)
        hand.lineTo(21, 22)
        hand.lineTo(21, 10)
        hand.cubicTo(21, 6, 25, 6, 25, 10)
        hand.lineTo(25, 22)
        hand.lineTo(26, 13)
        hand.cubicTo(26, 9, 30, 9, 30, 13)
        hand.lineTo(30, 24)
        hand.lineTo(32, 18)
        hand.cubicTo(33, 14, 37, 15, 36, 19)
        hand.lineTo(35, 31)
        hand.cubicTo(34, 36, 31, 39, 27, 40)
        hand.lineTo(21, 40)
        hand.quadTo(19, 40, 18, 37)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(hand)
    elif symbol.startswith('marker:'):
        from .markers import marker_path
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(marker_path(symbol.split(':')[1], QPointF(24, 24), 16))
        font = QFont()
        font.setPixelSize(19)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, 48, 48), Qt.AlignmentFlag.AlignCenter, '1')
    elif symbol == 'rectangle' or symbol == 'rectangle:rounded':
        p.setBrush(Qt.BrushStyle.NoBrush)
        if symbol.endswith(':rounded'):
            p.drawRoundedRect(QRectF(12, 15, 24, 18), 5, 5)
        else:
            p.drawRect(12, 15, 24, 18)
    elif symbol == 'arrow' or symbol.startswith('arrow:'):
        from .annotations import draw_arrow
        draw_arrow(p, {'a': [13, 35], 'b': [35, 13], 'style': symbol.split(':')[1] if ':' in symbol else 'classic', 'color': ink}, head_length=11)
    elif symbol == 'crop':
        p.drawLine(15, 10, 15, 33)
        p.drawLine(15, 33, 38, 33)
        p.drawLine(10, 15, 33, 15)
        p.drawLine(33, 15, 33, 38)
    elif symbol == 'A':
        p.drawLine(13, 12, 35, 12)
        p.drawLine(24, 12, 24, 37)
        p.drawLine(18, 37, 30, 37)
    elif symbol == 'blur':
        for x in (15, 24, 33):
            for y in (15, 24, 33):
                p.drawPoint(x, y)
    else:
        font = QFont()
        font.setPixelSize(27)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, 48, 48), Qt.AlignmentFlag.AlignCenter, symbol)
    p.end()
    pixmap.setDevicePixelRatio(scale)
    return pixmap


def dark_palette():
    palette = QPalette()
    for role, token in ((QPalette.ColorRole.Window, 'app'),
                        (QPalette.ColorRole.WindowText, 'text'),
                        (QPalette.ColorRole.Base, 'app'),
                        (QPalette.ColorRole.AlternateBase, 'surface'),
                        (QPalette.ColorRole.Text, 'text'),
                        (QPalette.ColorRole.Button, 'surface'),
                        (QPalette.ColorRole.ButtonText, 'text'),
                        (QPalette.ColorRole.Highlight, 'accent'),
                        (QPalette.ColorRole.HighlightedText, 'text')):
        palette.setColor(role, QColor(TOKENS[token]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(TOKENS['secondary']))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(TOKENS['secondary']))
    return palette
