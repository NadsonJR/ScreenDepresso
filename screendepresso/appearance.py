"""Dark desktop palette and original toolbar icons."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QFont, QPalette

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
    if symbol == 'rectangle':
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
