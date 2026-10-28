"""ScreenDepresso identity tokens, independent of capture and document state."""
TOKENS = {
    'app': '#171D25', 'surface': '#1E2732', 'canvas': '#202B37',
    'hover': '#2D3C4D', 'border': '#344354', 'text': '#F4F7FB',
    'secondary': '#B6C3D2', 'accent': '#2583F5', 'accent_hover': '#0F5CBE',
    'accent_active': '#146BD6', 'success_surface': '#238653', 'warning_surface': '#A5641D',
    'success': '#2EAF70', 'warning': '#E79A40', 'danger': '#EF4059',
}


STYLE_TEMPLATE = '''
QMainWindow, QDialog, QWidget#editorShell { background: @app; color: @text; }
QWidget { color: @text; }
QMenuBar, QMenu, QToolBar, QStatusBar, QWidget#contextContent { background: @surface; color: @text; }
QMenu { border: 1px solid @border; padding: 8px; }
QMenu::item { padding: 9px 20px; border-radius: 6px; }
QMenu::item:selected { background: @hover; }
QMenu::separator { height: 1px; background: @border; margin: 6px; }
QToolBar { border: 0; spacing: 8px; padding: 12px; }
QToolBar#ribbon { border-bottom: 1px solid @border; min-height: 80px; }
QToolBar::separator { background: @border; width: 1px; height: 1px; margin: 8px; }
QToolBar#tools { background: @surface; border-right: 1px solid @border; padding: 12px 8px; spacing: 8px; }
QToolBar#tools QToolButton { text-align: left; padding: 8px; min-height: 32px; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 8px; min-width: 20px; min-height: 20px; }
QToolButton:hover { background: @hover; border-color: @border; }
QToolButton:checked { background: @accent_active; color: white; border-color: @accent_active; }
QToolButton:focus, QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QFontComboBox:focus, QKeySequenceEdit:focus, QTextBrowser:focus { border: 1px solid @accent; }
QToolButton:disabled, QPushButton:disabled { color: @secondary; background: @surface; }
QToolButton::menu-button { border-left: 1px solid @border; width: 16px; }
QScrollArea, QScrollArea > QWidget > QWidget { background: @canvas; border: 0; }
QScrollArea#contextBar { background: @surface; border-bottom: 1px solid @border; }
QDockWidget { color: @text; }
QDockWidget::title { background: @surface; padding: 12px; border-bottom: 1px solid @border; }
QWidget#workspaceView { background: @surface; }
QListWidget, QLineEdit, QKeySequenceEdit, QSpinBox, QComboBox, QTextBrowser, QFontComboBox { background: @app; color: @text; border: 1px solid @border; border-radius: 8px; padding: 8px; selection-background-color: @accent; }
QListWidget::item { padding: 10px; border-radius: 8px; }
QListWidget::item:selected { background: @hover; border: 1px solid @accent; }
QListWidget::item:hover { background: @hover; }
QPushButton { background: @surface; border: 1px solid @border; border-radius: 8px; padding: 9px 14px; min-height: 18px; }
QPushButton:hover { background: @hover; }
QPushButton:checked, QPushButton#primaryAction { background: @accent_active; color: white; border-color: @accent_active; }
QPushButton#primaryAction:hover { background: @accent_hover; }
QProgressBar { background: @app; color: @text; border: 1px solid @border; border-radius: 6px; text-align: center; min-height: 18px; }
QProgressBar::chunk { background: @accent; border-radius: 5px; }
QTabWidget::pane { border: 1px solid @border; border-radius: 10px; }
QTabBar::tab { background: @surface; padding: 10px 16px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { background: @hover; border-bottom: 2px solid @accent; }
QTabBar::tab:hover { background: @hover; }
QTabWidget#captureTabs::pane { border: 0; }
QTabWidget#captureTabs QTabBar::tab { min-width: 90px; max-width: 220px; padding: 9px 12px; margin-right: 2px; }
QStatusBar { border-top: 1px solid @border; min-height: 40px; padding: 0 12px; }
QStatusBar QLabel { font-size: 12px; color: @secondary; }
QStatusBar::item { border: 0; }
QSlider::groove:horizontal { background: @border; height: 6px; border-radius: 3px; }
QSlider::sub-page:horizontal { background: @accent; border-radius: 3px; }
QSlider::handle:horizontal { background: @accent; border: 2px solid @text; width: 14px; margin: -6px 0; border-radius: 9px; }
QComboBox QAbstractItemView { background: @surface; color: @text; selection-background-color: @accent; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid @secondary; border-radius: 4px; background: @app; }
QCheckBox::indicator:checked { background: @accent; border-color: @text; }
QToolTip { background: @app; color: @text; border: 1px solid @border; border-radius: 6px; padding: 8px; }
QScrollBar:vertical { background: @surface; width: 12px; }
QScrollBar::handle:vertical { background: @border; min-height: 30px; border-radius: 6px; }
QScrollBar:horizontal { background: @surface; height: 10px; }
QScrollBar::handle:horizontal { background: @border; min-width: 30px; border-radius: 5px; }
QFrame#emptyCard { background: @canvas; border: 1px dashed @border; border-radius: 12px; }
QLabel#emptyTitle { font-size: 20px; font-weight: 600; color: @text; }
QLabel#emptyDescription { font-size: 14px; color: @secondary; }
QLabel#contextTitle { font-size: 14px; font-weight: 600; }
'''


def stylesheet():
    style = STYLE_TEMPLATE
    for key in sorted(TOKENS, key=len, reverse=True):
        style = style.replace('@'+key, TOKENS[key])
    return style
