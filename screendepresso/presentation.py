"""Presentation components for the 0.7.1 visual identity.

Controls delegate to the existing editor commands; no document format or capture
backend is changed by this layer.
"""
from PySide6.QtCore import Qt, QSize, QSignalBlocker
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QStackedWidget, QComboBox, QSpinBox,
    QCheckBox, QFontComboBox, QSizePolicy)
from .appearance import icon
from .theme import TOKENS
from .i18n import tr
from .annotations import ARROW_STYLES, BUBBLE_STYLES
from .markers import MARKER_STYLES

TOOL_NAMES = {'selecionar':'Select / move', 'seta':'Arrow', 'retângulo':'Rectangle',
              'texto':'Text', 'balao':'Speech balloon', 'numero':'Numbered markers',
              'desfoque':'Blur', 'recorte':'Crop', 'imagem':'Image'}


class EmptyState(QWidget):
    def __init__(self, owner, parent):
        super().__init__(parent)
        self.setObjectName('emptyState')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.card = QFrame()
        self.card.setObjectName('emptyCard')
        layout.addWidget(self.card)
        content = QVBoxLayout(self.card)
        content.setContentsMargins(20, 24, 20, 24)
        content.addStretch()
        picture = QLabel()
        picture.setPixmap(icon('image', TOKENS['secondary'], plate=False, size=96).pixmap(QSize(88, 88)))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.addWidget(picture)
        self.title = QLabel()
        self.title.setObjectName('emptyTitle')
        self.description = QLabel()
        self.description.setObjectName('emptyDescription')
        for label in (self.title, self.description):
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content.addWidget(label)
        content.addSpacing(20)
        self.actions = QGridLayout()
        self.actions.setSpacing(12)
        self.buttons = []
        for symbol, callback in (('monitor', lambda: owner.capture('tela')),
                                 ('folder', owner.open_image_file), ('paste', owner.paste)):
            button = QPushButton()
            button.setIcon(icon(symbol, TOKENS['text'], plate=False))
            button.setIconSize(QSize(22, 22))
            button.clicked.connect(callback)
            self.buttons.append(button)
        self.buttons[0].setObjectName('primaryAction')
        row = QHBoxLayout()
        row.addStretch()
        row.addLayout(self.actions)
        row.addStretch()
        content.addLayout(row)
        content.addStretch()
        self.retranslate()
        self.arrange_buttons()

    def retranslate(self):
        self.title.setText(tr('Drop an image here'))
        self.description.setText(tr('Capture, open or paste an image to start editing.'))
        for button, text in zip(self.buttons, (tr('Capture screen'), tr('Open image'), tr('Paste image'))):
            button.setText(text)
            button.setToolTip(text)
            button.setAccessibleName(text)

    def arrange_buttons(self):
        compact = self.width() < 640
        for i, button in enumerate(self.buttons):
            self.actions.removeWidget(button)
            self.actions.addWidget(button, i if compact else 0, 0 if compact else i)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.arrange_buttons()


class ContextBar(QScrollArea):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setObjectName('contextBar')
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(64)
        content = QWidget()
        content.setObjectName('contextContent')
        row = QHBoxLayout(content)
        row.setContentsMargins(16, 6, 16, 6)
        row.setSpacing(16)
        self.title = QLabel()
        self.title.setObjectName('contextTitle')
        self.title.setMinimumWidth(100)
        row.addWidget(self.title)
        self.pages = QStackedWidget()
        self.pages.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        row.addWidget(self.pages)
        row.addStretch()
        self.layouts = {}
        for kind in ('seta', 'retângulo', 'texto', 'balao', 'numero', 'desfoque', 'selecionar', 'recorte', 'imagem'):
            page = QWidget()
            page.setObjectName('contextContent')
            layout = QHBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(16)
            self.layouts[kind] = layout
            self.pages.addWidget(page)
        self.labels = []
        self.colors = {}
        self.combos = []
        for kind, callback in [('seta', owner.choose_arrow_color), ('retângulo', owner.choose_rectangle_color),
                               ('texto', owner.choose_text_color), ('numero', owner.choose_marker_color),
                               ('balao', lambda: owner.choose_bubble_color('fill'))]:
            button = QPushButton()
            button.clicked.connect(callback)
            self.colors[kind] = button
            self.field(kind, 'Color', button)
        self.arrow_style = self.combo('seta', 'Style', ARROW_STYLES, owner.choose_arrow_style)
        self.rectangle_width = self.spin('retângulo', 'Border thickness', 1, 40,
                                        lambda value: owner.canvas.set_rectangle_format(width=value))
        self.rounded = QCheckBox()
        self.rounded.toggled.connect(lambda value: owner.canvas.set_rectangle_format(rounded=value))
        self.layouts['retângulo'].addWidget(self.rounded)
        self.radius = self.spin('retângulo', 'Corner radius', 1, 100,
                               lambda value: owner.canvas.set_rectangle_format(radius=value))
        self.font = QFontComboBox()
        self.font.setFixedWidth(160)
        self.font.currentFontChanged.connect(lambda font: owner.canvas.set_text_format(font_family=font.family()))
        self.field('texto', 'Font family', self.font)
        self.font_size = self.spin('texto', 'Font size', 6, 200,
                                  lambda value: owner.canvas.set_text_format(font_size=value))
        self.bubble_style = self.combo('balao', 'Style', BUBBLE_STYLES, owner.choose_bubble_style)
        self.outline = QPushButton()
        self.outline.clicked.connect(lambda: owner.choose_bubble_color('outline'))
        self.field('balao', 'Outline', self.outline)
        self.marker_style = self.combo('numero', 'Style', MARKER_STYLES, owner.choose_marker_style)
        self.blur_strength = self.spin('desfoque', 'Blur strength:', 1, 100, lambda value: owner.canvas.set_blur_radius(value))
        self.blur_mode = self.combo('desfoque', 'Mode', {'shared':'Shared blur layer', 'sequential':'Sequential blur (legacy)'}, lambda value: owner.canvas.set_blur_mode(value))
        self.hints = []
        for kind, text in [('selecionar', 'Select an object to edit its properties.'),
                           ('recorte', 'Crop • Drag the area you want to keep'),
                           ('imagem', 'Select • Drag to move; use handles to resize')]:
            label = QLabel()
            self.layouts[kind].addWidget(label)
            self.hints.append((label, text))
        self.setWidget(content)
        self.refresh()

    def field(self, kind, text, control):
        label = QLabel()
        self.labels.append((label, control, text))
        self.layouts[kind].addWidget(label)
        self.layouts[kind].addWidget(control)

    def combo(self, kind, label, choices, callback):
        combo = QComboBox()
        for key, text in choices.items():
            combo.addItem(tr(text), key)
        combo.currentIndexChanged.connect(lambda index: callback(combo.itemData(index)))
        self.field(kind, label, combo)
        self.combos.append((combo, choices))
        return combo

    def spin(self, kind, label, low, high, callback):
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setSuffix(' px' if kind != 'desfoque' else '')
        spin.setMinimumWidth(90)
        spin.setKeyboardTracking(False)
        spin.valueChanged.connect(callback)
        self.field(kind, label, spin)
        return spin

    @staticmethod
    def set_value(control, value):
        current = (control.currentData() if isinstance(control, QComboBox) else
                   control.isChecked() if isinstance(control, QCheckBox) else control.value())
        if current == value:
            return
        with QSignalBlocker(control):
            if isinstance(control, QComboBox):
                control.setCurrentIndex(control.findData(value))
            elif isinstance(control, QCheckBox):
                control.setChecked(value)
            else:
                control.setValue(value)

    def refresh(self):
        canvas = self.owner.canvas
        selected = canvas.objects[canvas.selected] if canvas.selected is not None else None
        kind = selected['kind'] if canvas.tool == 'selecionar' and selected else canvas.tool
        if kind not in self.layouts:
            kind = 'selecionar'
        self.title.setText(tr(TOOL_NAMES[kind]))
        self.pages.setCurrentWidget(self.layouts[kind].parentWidget())
        # A stacked widget otherwise reserves the width of the widest page.
        for layout in self.layouts.values():
            page = layout.parentWidget()
            page.setSizePolicy(QSizePolicy.Policy.Minimum if page is self.pages.currentWidget() else QSizePolicy.Policy.Ignored,
                               QSizePolicy.Policy.Preferred)
        for label, control, text in self.labels:
            label.setText(tr(text))
            label.setBuddy(control)
            control.setToolTip(tr(text))
            control.setAccessibleName(tr(text))
        for combo, choices in self.combos:
            with QSignalBlocker(combo):
                for index, text in enumerate(choices.values()):
                    translated = tr(text)
                    if combo.itemText(index) != translated:
                        combo.setItemText(index, translated)
        for label, text in self.hints:
            label.setText(tr(text))
        self.rounded.setText(tr('Rounded corners'))
        self.rounded.setToolTip(tr('Rounded corners'))
        rectangle = selected if selected and selected['kind'] == 'retângulo' else canvas.rectangle_format
        text = canvas.current_text_format()
        bubble = self.owner.current_bubble_format()
        self.set_value(self.arrow_style, selected.get('style','classic') if selected and selected['kind'] == 'seta' else canvas.arrow_style)
        self.set_value(self.rectangle_width, rectangle.get('width', 4))
        self.set_value(self.rounded, rectangle.get('rounded', False))
        self.set_value(self.radius, rectangle.get('radius', 12))
        self.radius.setEnabled(self.rounded.isChecked())
        self.set_value(self.font_size, text.get('font_size', 24))
        font = self.font.currentFont()
        if font.family() != text['font_family']:
            font.setFamily(text['font_family'])
            with QSignalBlocker(self.font):
                self.font.setCurrentFont(font)
        self.set_value(self.bubble_style, bubble.get('style','oval'))
        self.set_value(self.marker_style, self.owner.current_marker_style())
        self.set_value(self.blur_strength, selected['radius'] if selected and selected['kind'] == 'desfoque' else canvas.blur_radius)
        self.set_value(self.blur_mode, canvas.blur_mode)
        colors = {'seta': canvas.arrow_color, 'retângulo': canvas.rectangle_color,
                  'texto': text['color'], 'balao': bubble['fill'], 'numero': canvas.marker_color}
        if selected and selected['kind'] in ('seta', 'retângulo'):
            colors[selected['kind']] = selected.get('color', colors[selected['kind']])
        for tool, button in self.colors.items():
            self.swatch(button, colors[tool])
        self.swatch(self.outline, bubble['outline'])
        self.widget().adjustSize()

    @staticmethod
    def swatch(button, color):
        color = QColor(color).name()
        if button.property('swatchColor') == color:
            return
        button.setProperty('swatchColor', color)
        pixmap = QPixmap(40,40)
        pixmap.fill(QColor(color))
        pixmap.setDevicePixelRatio(2)
        button.setIcon(QIcon(pixmap))
        button.setText(color.upper())
        button.setAccessibleDescription(color)
