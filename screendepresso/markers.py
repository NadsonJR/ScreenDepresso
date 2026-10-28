"""Numbered marker silhouettes share hit testing and rendering geometry."""
import math
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

MARKER_STYLES = {
    'circle': 'Classic circle', 'flat': 'Flat circle', 'square': 'Square marker',
    'diamond': 'Diamond marker', 'outline': 'Outlined circle', 'hexagon': 'Hexagon marker',
}


def marker_path(style, center, radius=20):
    center = QPointF(center)
    path = QPainterPath()
    if style == 'square':
        path.addRect(center.x()-radius, center.y()-radius, radius*2, radius*2)
    elif style in ('diamond', 'hexagon'):
        sides = 4 if style == 'diamond' else 6
        radius *= 1.2 if style == 'diamond' else 1.1
        for index in range(sides):
            angle = -math.pi/2+index*math.tau/sides
            point = center+QPointF(math.cos(angle)*radius, math.sin(angle)*radius)
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        path.closeSubpath()
    else:
        path.addEllipse(center, radius, radius)
    return path


def marker_body_hit(obj, point):
    return marker_path(obj.get('style', 'circle'), QPointF(*obj['a']), 24).contains(QPointF(point))
