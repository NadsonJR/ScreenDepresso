import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import ast
from pathlib import Path
from PySide6.QtWidgets import QApplication,QFileDialog,QLabel,QAbstractButton
from PySide6.QtGui import QAction
from PySide6.QtCore import QPoint
from screendepresso import i18n
from screendepresso.annotations import ARROW_STYLES,BUBBLE_STYLES
from screendepresso.markers import MARKER_STYLES
from screendepresso.editor import Canvas
from test_editor import image,gesture

app=QApplication.instance() or QApplication([])


def test_all_literal_application_translations_and_model_labels_have_portuguese_entries():
    missing=[]
    for path in (Path(__file__).parents[1]/'screendepresso').glob('*.py'):
        if path.name=='i18n.py':continue
        for node in ast.walk(ast.parse(path.read_text())):
            if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='tr'
                and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str)
                and node.args[0].value not in i18n.CATALOG):
                missing.append(f'{path.name}:{node.lineno}: {node.args[0].value}')
    for mapping in (ARROW_STYLES,BUBBLE_STYLES,MARKER_STYLES):
        missing.extend(label for label in mapping.values() if label not in i18n.CATALOG)
    assert not missing, '\n'.join(missing)


def test_qt_translation_catalog_covers_context_menus_and_unknown_keys_remain_visible():
    i18n.set_language('pt_BR')
    try:
        translator=i18n._translator
        assert not translator.native.isEmpty()
        assert translator.translate('QWidgetTextControl','Select All')=='Selecionar tudo'
        assert translator.translate('QFileDialog','&Look in:')=='&Examinar:'
        assert translator.translate('QFileDialog','Files of &type:')=='Arquivos do &tipo:'
        assert translator.translate('QShortcut','Ctrl')=='Ctrl'
        assert translator.translate('Unknown','Unknown source')=='Unknown source'
    finally:i18n.set_language('en')


def test_file_dialog_has_no_untranslated_standard_labels_in_portuguese():
    i18n.set_language('pt_BR')
    dialog=QFileDialog(None,'Files','/tmp')
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
    try:
        texts={widget.text() for widget in dialog.findChildren(QLabel)+dialog.findChildren(QAbstractButton)+dialog.findChildren(QAction)}
        assert '&Examinar:' in texts
        assert 'Arquivos do &tipo:' in texts
        assert not {'&Look in:','Files of &type:','File &name:'}.intersection(texts)
    finally:
        dialog.close()
        i18n.set_language('en')


def test_language_switch_preserves_user_text_and_changes_placeholder_and_decimal_format():
    canvas=Canvas()
    canvas.load(image())
    canvas.tool='texto'
    gesture(canvas,(10,10),(150,100))
    canvas.text_editor.setPlainText('Save / Workspace')
    canvas.show()
    i18n.set_language('pt_BR')
    try:
        assert canvas.text_editor.toPlainText()=='Save / Workspace'
        assert canvas.text_editor.placeholderText()=='Digite aqui…'
        assert i18n.format_number(12.5)=='12,5'
        i18n.set_language('en')
        assert canvas.text_editor.toPlainText()=='Save / Workspace'
        assert canvas.text_editor.placeholderText()=='Type here…'
        assert i18n.format_number(12.5)=='12.5'
    finally:
        canvas.finish_text(False)
        canvas.close()
        i18n.set_language('en')
