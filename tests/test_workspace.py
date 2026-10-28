import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import shutil
import time
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QMimeData, QUrl
from PySide6.QtGui import QImage, QColor, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListView
from screendepresso import workspace as module
from screendepresso.workspace import WorkspaceStore, WORKSPACE_LIMITS
from screendepresso.settings import Settings, SettingsDialog, DEFAULT_HOTKEYS
from screendepresso.app import MainWindow
from screendepresso.i18n import set_language

app = QApplication.instance() or QApplication([])


def image(color='blue', width=40, height=30):
    result=QImage(width,height,QImage.Format.Format_ARGB32)
    result.fill(QColor(color))
    return result


def pump(predicate):
    deadline=time.monotonic()+5
    while not predicate() and time.monotonic()<deadline:
        app.processEvents()
        QTest.qWait(10)
    assert predicate()


@pytest.fixture
def trash(tmp_path,monkeypatch):
    folder=tmp_path/'trash'
    folder.mkdir()
    moved=[]
    def move(path):
        path=Path(path)
        shutil.move(str(path),folder/path.name)
        moved.append(path)
    monkeypatch.setattr(module,'move_to_trash',move)
    return moved


@pytest.mark.parametrize('limit',WORKSPACE_LIMITS)
def test_retention_uses_configured_limit_and_keeps_newest_images(tmp_path,trash,limit):
    store=WorkspaceStore(tmp_path/'workspace',limit)
    count=limit+2 if limit else 105
    saved=[store.save(image()) for _ in range(count)]
    assert len(store.entries())==(limit or count)
    assert len(trash)==(2 if limit else 0)
    assert all(path.exists() for path in saved[-(limit or count):])
    assert not store.retention_error


def test_opening_existing_directory_does_not_remove_images_until_limit_is_applied(tmp_path,trash):
    store=WorkspaceStore(tmp_path/'workspace',0)
    for _ in range(30):store.save(image())
    limited=WorkspaceStore(store.directory)
    assert len(limited.entries())==30 and not trash
    limited.enforce_limit()
    assert len(limited.entries())==25 and len(trash)==5


def test_retention_failure_preserves_files_and_reports_error(tmp_path,monkeypatch):
    store=WorkspaceStore(tmp_path/'workspace',0)
    original=[store.save(image()) for _ in range(25)]
    store.limit=25
    def failure(path):raise OSError('Trash unavailable')
    monkeypatch.setattr(module,'move_to_trash',failure)
    newest=store.save(image())
    assert newest.exists() and all(path.exists() for path in original)
    assert len(store.entries())==26 and store.retention_error


def test_duplicate_preserves_bytes_and_delete_is_recoverable(tmp_path,trash):
    store=WorkspaceStore(tmp_path/'workspace')
    original=store.directory/'photo.JPG'
    assert image().save(str(original),'JPEG')
    duplicated=store.duplicate(original)
    assert duplicated!=original and duplicated.suffix=='.jpg'
    assert duplicated.read_bytes()==original.read_bytes()
    store.trash(duplicated)
    assert not duplicated.exists() and original.exists()
    assert trash==[duplicated]
    assert (tmp_path/'trash'/duplicated.name).read_bytes()==original.read_bytes()


def test_operations_cannot_delete_or_duplicate_outside_workspace(tmp_path,trash):
    store=WorkspaceStore(tmp_path/'workspace')
    outside=tmp_path/'outside.png'
    image().save(str(outside))
    for operation in (store.trash,store.duplicate):
        with pytest.raises(OSError):operation(outside)
    assert outside.exists() and not trash


def test_entries_ignore_subfolders_and_symlinks(tmp_path):
    store=WorkspaceStore(tmp_path/'workspace')
    nested=store.directory/'nested'
    nested.mkdir()
    image().save(str(nested/'nested.png'))
    photo=store.directory/'photo.JPEG'
    image().save(str(photo),'JPEG')
    (store.directory/'notes.txt').write_text('not an image')
    assert store.entries()==[photo]
    link=store.directory/'link.png'
    try:link.symlink_to(photo)
    except OSError:pytest.skip('Symlink creation is unavailable')
    assert store.entries()==[photo]
    with pytest.raises(OSError):store.trash(link)


def test_settings_defaults_choices_roundtrip_and_invalid_limit(tmp_path):
    settings=Settings(tmp_path/'settings.json')
    assert settings.workspace_limit==25
    for limit in WORKSPACE_LIMITS:
        settings.save(str(tmp_path/'images'),DEFAULT_HOTKEYS,'en',limit)
        assert Settings(settings.path).workspace_limit==limit
    for value in (True,-1,1,26,101,'25'):
        with pytest.raises(ValueError):settings.save(str(tmp_path),DEFAULT_HOTKEYS,'en',value)


@pytest.fixture
def window(tmp_path,monkeypatch,trash):
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path/'data'))
    window=MainWindow()
    window.show()
    window.activateWindow()
    app.processEvents()
    yield window
    window.request_quit()
    set_language('en')


def select_path(window,path):
    item=next(window.list.item(i) for i in range(window.list.count()) if window.list.item(i).data(Qt.ItemDataRole.UserRole)==str(path))
    window.list.setCurrentItem(item)
    return item


def test_workspace_thumbnails_duplicate_delete_and_open_tabs_are_preserved(window,trash):
    window.finish_capture(image('white',160,120))
    original=window.history.entries()[0]
    assert window.history_dock.windowTitle()=='Workspace'
    assert window.list.viewMode()==QListView.ViewMode.IconMode
    pump(lambda:not window.workspace._pending)
    assert not window.list.item(0).icon().isNull()
    select_path(window,original)
    window.workspace.duplicate_button.click()
    duplicate=window.workspace.selected_path()
    assert duplicate and duplicate!=original and duplicate.read_bytes()==original.read_bytes()
    assert window.tabs.count()==1
    window.workspace.delete_button.click()
    assert duplicate in trash and not duplicate.exists()
    assert window.canvas.image==image('white',160,120)
    assert window.tabs.count()==1
    select_path(window,original)
    window.list.itemDoubleClicked.emit(window.list.currentItem())
    assert window.tabs.count()==1  # Existing editable tab is reused.


def test_delete_key_in_workspace_does_not_delete_selected_annotation(window,trash):
    window.finish_capture(image('white',160,120))
    from test_editor import gesture
    window.choose_tool('retângulo')
    gesture(window.canvas,(20,20),(100,80))
    path=window.history.entries()[0]
    select_path(window,path)
    window.list.setFocus()
    app.processEvents()
    QTest.keyClick(window.list,Qt.Key.Key_Delete)
    assert path in trash and not path.exists()
    assert len(window.canvas.objects)==1


def test_dragged_thumbnail_is_copy_only_and_adds_editable_layer_at_zoom(window):
    window.finish_capture(image('white',160,120))
    path=window.history.save(image('blue',40,30))
    window.refresh()
    item=select_path(window,path)
    mime=window.list.mimeData([item])
    assert Path(mime.urls()[0].toLocalFile())==path
    window.zoom_slider.setValue(200)
    event=QDropEvent(QPointF(100,80),Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    window.canvas.dropEvent(event)
    assert event.isAccepted() and path.exists()
    obj=window.canvas.objects[-1]
    assert obj['kind']=='imagem' and obj['a']==[30,25] and obj['b']==[69,54]
    window.canvas.undo()
    assert not window.canvas.objects and window.canvas.image==image('white',160,120)
    window.canvas.redo()
    assert window.canvas.objects[-1]['kind']=='imagem'


def test_drop_on_empty_editor_viewport_creates_image_and_rejects_remote_urls(window):
    path=window.history.save(image())
    window.refresh()
    mime=window.list.mimeData([select_path(window,path)])
    event=QDropEvent(QPointF(100,80),Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    window.scroll.dropEvent(event)
    assert event.isAccepted() and window.canvas.image==image()
    assert window.tabs.tabBar().isVisible()
    remote=QMimeData()
    remote.setUrls([QUrl('https://example.com/image.png')])
    assert not window.canvas.can_drop(remote)


def test_files_limit_choices_translate_and_apply_without_changing_image_data(window,trash):
    dialog=SettingsDialog(window)
    assert [dialog.workspace_limit.itemData(i) for i in range(dialog.workspace_limit.count())]==list(WORKSPACE_LIMITS)
    window.finish_capture(image())
    before=window.canvas.image
    window.apply_settings(window.settings.directory,window.settings.hotkeys,'pt_BR',0)
    assert dialog.workspace_limit.itemText(4)=='Sem limite'
    assert window.canvas.image==before
    assert 'Imagens:' in window.workspace.count_label.text()
    assert window.settings.workspace_limit==0
    assert Settings(window.settings.path).workspace_limit==0
    window.apply_settings(window.settings.directory,window.settings.hotkeys,'en',50)
    assert dialog.workspace_limit.itemText(4)=='No limit'
    assert 'Images:' in window.workspace.count_label.text()
    dialog.reject()


def test_external_images_are_observed_and_shown_as_thumbnails(window):
    path=window.history.directory/'external.png'
    image().save(str(path))
    pump(lambda:window.list.count()==1 and not window.workspace._pending)
    assert window.list.item(0).text()=='external.png'
    assert not window.list.item(0).icon().isNull()


def test_native_trash_moves_an_owned_image_out_of_the_directory(tmp_path):
    import subprocess,sys
    path=tmp_path/'native-trash.png'
    image().save(str(path))
    env=os.environ.copy()
    env['XDG_DATA_HOME']=str(tmp_path/'xdg')
    script='''
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from screendepresso.workspace import move_to_trash
app=QApplication([])
path=Path(sys.argv[1])
move_to_trash(path)
assert not path.exists()
'''
    result=subprocess.run([sys.executable,'-c',script,str(path)],env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode==0, result.stdout+result.stderr


def test_settings_utf8_and_legacy_windows_encoding_preserve_directory(tmp_path,monkeypatch):
    import json
    from screendepresso import settings as settings_module
    settings=Settings(tmp_path/'settings.json')
    folder=str(tmp_path/'capturas-á-日本')
    settings.save(folder,DEFAULT_HOTKEYS,'pt_BR',75)
    assert json.loads(settings.path.read_text(encoding='utf-8'))['directory']==folder
    assert Settings(settings.path).directory==folder
    legacy=str(tmp_path/'capturas-á')
    settings.path.write_bytes(json.dumps({'directory':legacy,'hotkeys':DEFAULT_HOTKEYS,'language':'pt_BR'},ensure_ascii=False).encode('cp1252'))
    monkeypatch.setattr(settings_module.locale,'getpreferredencoding',lambda *args:'cp1252')
    assert Settings(settings.path).directory==legacy
    assert Settings(settings.path).workspace_limit==25
