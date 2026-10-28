"""Dark desktop palette and original toolbar icons."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QFont, QPalette, QPainterPath

STYLE = '''
QMainWindow, QDialog { background: #252830; color: #e5e7eb; }
QWidget { color: #e5e7eb; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #30343d; color: #e5e7eb; }
QMenuBar { padding: 3px; }
QMenuBar::item:selected, QMenu::item:selected { background: #465164; }
QToolBar { border: 0; spacing: 8px; padding: 10px; }
QToolBar#tools { background: #30343d; padding: 8px; spacing: 8px; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 5px; }
QToolButton:hover { background: #414854; border-color: #64748b; }
QToolButton:checked { background: #3b5273; border-color: #7bb5ff; }
QToolButton:disabled { color: #737b8b; }
QScrollArea, QScrollArea > QWidget > QWidget { background: #171a20; border: 0; }
QDockWidget { color: #e5e7eb; }
QDockWidget::title { background: #30343d; padding: 8px; }
QListWidget, QLineEdit, QKeySequenceEdit, QSpinBox, QComboBox { background: #1c2028; color: #e5e7eb; border: 1px solid #475163; border-radius: 4px; padding: 6px; }
QListWidget::item { padding: 10px; }
QListWidget::item:selected { background: #36577d; }
QPushButton { background: #3b4351; border: 1px solid #566277; border-radius: 5px; padding: 8px 12px; }
QPushButton:hover { background: #4a5870; }
QTabWidget::pane { border: 1px solid #475163; }
QTabBar::tab { background: #30343d; padding: 10px 18px; }
QTabBar::tab:selected { background: #3d5270; }
QTabWidget#captureTabs::pane { border: 0; }
QTabWidget#captureTabs QTabBar::tab { min-width: 100px; max-width: 220px; padding: 9px 12px; margin-right: 2px; }
QTabWidget#captureTabs QTabBar::tab:hover { background: #414854; }
QSlider::groove:horizontal { background: #566277; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #80b8ff; border: 1px solid #bedbff; width: 14px; margin: -5px 0; border-radius: 7px; }
QComboBox QAbstractItemView { background: #1c2028; color: #e5e7eb; selection-background-color: #36577d; }
QToolTip { background: #111827; color: #f8fafc; border: 1px solid #64748b; padding: 6px; }
QScrollBar:vertical { background: #252830; width: 12px; }
QScrollBar::handle:vertical { background: #586174; min-height: 30px; border-radius: 5px; }
QScrollBar:horizontal { background: #252830; height: 12px; }
QScrollBar::handle:horizontal { background: #586174; min-width: 30px; border-radius: 5px; }
'''


def icon(symbol, color='#3878a8'):
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QRectF(2, 2, 44, 44))
    p.setPen(QPen(QColor('#f8fafc'), 2.5))
    if symbol == 'save':
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
        p.setBrush(QColor(color))
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
        p.setBrush(QColor(color))
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
    elif symbol == 'rectangle':
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(12, 15, 24, 18)
    elif symbol == 'arrow':
        p.drawLine(13, 35, 35, 13)
        p.drawLine(23, 13, 35, 13)
        p.drawLine(35, 13, 35, 25)
    elif symbol == 'crop':
        p.drawLine(15, 10, 15, 33)
        p.drawLine(15, 33, 38, 33)
        p.drawLine(10, 15, 33, 15)
        p.drawLine(33, 15, 33, 38)
    elif symbol == 'blur':
        for x in (15, 24, 33):
            for y in (15, 24, 33):
                p.drawPoint(x, y)
    else:
        font = QFont()
        font.setPixelSize(27)
        font.setBold(True)
        p.setFont(font)
        p.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, symbol)
    p.end()
    return QIcon(pixmap)


def dark_palette():
    palette = QPalette()
    for role, color in ((QPalette.ColorRole.Window, '#252830'),
                        (QPalette.ColorRole.WindowText, '#e5e7eb'),
                        (QPalette.ColorRole.Base, '#1c2028'),
                        (QPalette.ColorRole.AlternateBase, '#30343d'),
                        (QPalette.ColorRole.Text, '#e5e7eb'),
                        (QPalette.ColorRole.Button, '#3b4351'),
                        (QPalette.ColorRole.ButtonText, '#e5e7eb'),
                        (QPalette.ColorRole.Highlight, '#36577d'),
                        (QPalette.ColorRole.HighlightedText, '#ffffff')):
        palette.setColor(role, QColor(color))
    return palette
