"""Image and video directory operations and a thumbnail workspace with copy-only dragging."""
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
from html import escape
import os
import sys
from send2trash import send2trash
from PySide6.QtCore import (Qt, QSize, QTimer, QFile, QMimeData, QUrl,
                            QFileSystemWatcher, QByteArray, QBuffer, QIODevice, Signal, QEvent)
from PySide6.QtGui import QIcon, QImage, QImageReader, QDrag, QPixmap, QPainter, QColor, QPolygonF
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel, QMenu,
                               QListWidget, QListWidgetItem, QListView, QAbstractItemView)
from .i18n import tr, native_help
from .appearance import icon

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff'}
VIDEO_SUFFIXES = {'.mp4', '.webm', '.mkv', '.mov', '.avi'}
# Hidden helpers inside the workspace; subfolders are never listed or trimmed.
THUMBNAILS = '.thumbnails'
RECORDING = '.recording'
WORKSPACE_LIMITS = (25, 50, 75, 100, 0)


def move_to_trash(path):
    if sys.platform == 'win32':
        # Qt fails rather than permanently deleting when recycling is unavailable.
        result = QFile.moveToTrash(str(path))
        if not (result[0] if isinstance(result, tuple) else result):
            raise OSError(tr('Could not move this image to the system trash.'))
    else:
        send2trash(str(path))


def is_video(path):
    return Path(path).suffix.lower() in VIDEO_SUFFIXES


def read_image(path):
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    return reader.read()


class WorkspaceStore:
    def __init__(self, directory, limit=25):
        if type(limit) is not int or limit not in WORKSPACE_LIMITS:
            raise ValueError(tr('Invalid workspace limit.'))
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.limit = limit
        self._last_saved_time = None
        self.retention_error = ''

    def _list(self, suffixes):
        def key(path):
            try:
                return path.stat().st_mtime_ns, path.name
            except OSError:
                return 0, path.name
        return sorted((path for path in self.directory.iterdir()
                       if not path.is_symlink() and path.is_file() and path.suffix.lower() in suffixes),
                      key=key, reverse=True)

    def entries(self):
        """Images only: the workspace limit never trashes recordings."""
        return self._list(IMAGE_SUFFIXES)

    def videos(self):
        return self._list(VIDEO_SUFFIXES)

    def items(self):
        return self._list(IMAGE_SUFFIXES | VIDEO_SUFFIXES)

    def recording_target(self):
        """Return (temporary, final) paths for a new recording. The video is
        written in a hidden subfolder and moved in by add_video when complete."""
        stamp = datetime.now()
        while True:
            name = stamp.strftime('%Y%m%d-%H%M%S-%f')+'.mp4'
            final = self.directory/name
            temporary = self.directory/RECORDING/name
            if not final.exists() and not temporary.exists():
                temporary.parent.mkdir(exist_ok=True)
                return temporary, final
            stamp += timedelta(microseconds=1)

    def add_video(self, temporary, final, poster=None):
        temporary, final = Path(temporary), Path(final)
        if final.exists():
            raise OSError(tr('Could not save the recording in the workspace.'))
        os.replace(temporary, final)
        try:
            temporary.parent.rmdir()
        except OSError:
            pass
        if poster is not None and not poster.isNull():
            thumbnail = self.thumbnail_path(final)
            try:
                thumbnail.parent.mkdir(exist_ok=True)
                poster.save(str(thumbnail), 'PNG')
            except OSError:
                pass  # A missing thumbnail only shows the placeholder.
        return final

    def thumbnail_path(self, video):
        return self.directory/THUMBNAILS/(Path(video).name+'.png')

    def _write(self, payload, suffix='.png'):
        stamp = datetime.now()
        if self._last_saved_time is not None:
            stamp = max(stamp, self._last_saved_time+timedelta(microseconds=1))
        while True:
            path = self.directory/(stamp.strftime('%Y%m%d-%H%M%S-%f')+suffix.lower())
            try:
                stream = path.open('xb')
            except FileExistsError:
                stamp += timedelta(microseconds=1)
                continue
            try:
                with stream:
                    stream.write(payload)
            except OSError:
                path.unlink(missing_ok=True)
                raise
            self._last_saved_time = stamp
            self.enforce_limit(protect=path)
            return path

    def save(self, image):
        payload = QByteArray()
        buffer = QBuffer(payload)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, 'PNG'):
            raise OSError(tr('Could not save the capture.'))
        buffer.close()
        return self._write(bytes(payload))

    def require_path(self, path):
        path = Path(path)
        if (path.is_symlink() or path.parent.resolve() != self.directory.resolve()
                or path.suffix.lower() not in IMAGE_SUFFIXES | VIDEO_SUFFIXES or not path.is_file()):
            raise OSError(tr('This image is no longer available in the workspace.'))
        return path

    def duplicate(self, path):
        path = self.require_path(path)
        if is_video(path):
            raise OSError(tr('Recordings cannot be duplicated in the workspace.'))
        return self._write(path.read_bytes(), path.suffix)

    def trash(self, path):
        path = self.require_path(path)
        try:
            move_to_trash(path)
        except OSError as exc:
            raise OSError(tr('Could not move this image to the system trash.')) from exc
        if is_video(path):
            self.thumbnail_path(path).unlink(missing_ok=True)
        self.retention_error = ''

    def enforce_limit(self, protect=None):
        self.retention_error = ''
        if not self.limit:
            return
        entries = self.entries()
        excess = max(0, len(entries)-self.limit)
        for path in reversed(entries):
            if excess == 0:
                break
            if path == protect:
                continue
            try:
                self.trash(path)
                excess -= 1
            except OSError as exc:
                self.retention_error = str(exc)
                break  # Never fall back to permanent deletion.


class WorkspaceGrid(QListWidget):
    delete_requested = Signal()
    duplicate_requested = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setIconSize(QSize(120, 90))
        self.setGridSize(QSize(140, 150))
        self.setSpacing(4)
        self.setWordWrap(True)
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def mimeData(self, items):
        mime = QMimeData()
        if items:
            mime.setUrls([QUrl.fromLocalFile(items[0].data(Qt.ItemDataRole.UserRole))])
        return mime

    def startDrag(self, supported_actions):
        items = self.selectedItems()
        if items:
            drag = QDrag(self)
            drag.setMimeData(self.mimeData(items))
            drag.setPixmap(items[0].icon().pixmap(self.iconSize()))
            drag.exec(Qt.DropAction.CopyAction, Qt.DropAction.CopyAction)

    def event(self, event):
        if event.type() == QEvent.Type.ShortcutOverride and (
            event.key() == Qt.Key.Key_Delete or
            event.key() == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_requested.emit()
        elif event.key() == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.duplicate_requested.emit()
        else:
            super().keyPressEvent(event)


class WorkspaceView(QWidget):
    open_requested = Signal(str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setObjectName('workspaceView')
        self.store = store
        self._cache = {}
        self._pending = deque()
        self._message = None
        self._stopped = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        actions = QHBoxLayout()
        actions.addStretch()
        self.refresh_button = QToolButton()
        self.refresh_button.setAutoRaise(True)
        self.refresh_button.setIcon(icon('refresh', 'transparent'))
        self.refresh_button.setIconSize(QSize(22, 22))
        self.refresh_button.clicked.connect(self.refresh)
        actions.addWidget(self.refresh_button)
        layout.addLayout(actions)
        self.grid = WorkspaceGrid(self)
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.show_context_menu)
        self.grid.delete_requested.connect(self.delete_selected)
        self.grid.duplicate_requested.connect(lambda: None if is_video(self.selected_path() or '') else self.duplicate_selected())
        layout.addWidget(self.grid, 1)
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.count_label = QLabel()
        layout.addWidget(self.count_label)
        self._loader = QTimer(self)
        self._loader.timeout.connect(self.load_thumbnails)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(150)
        self._refresh_timer.timeout.connect(self.refresh)
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(lambda path: self._refresh_timer.start())
        self.watcher.fileChanged.connect(self.file_changed)
        self.set_store(store)

    def file_changed(self, path):
        self._cache = {key: value for key, value in self._cache.items() if key[0] != path}
        self._refresh_timer.start()

    def set_store(self, store):
        paths = self.watcher.directories()+self.watcher.files()
        if paths:
            self.watcher.removePaths(paths)
        self.store = store
        self._cache.clear()
        self._message = None
        self.watcher.addPath(str(store.directory))
        self.refresh()

    def selected_path(self):
        item = self.grid.currentItem()
        return Path(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def context_menu(self, position):
        item = self.grid.itemAt(position)
        if item is None:
            return None
        self.grid.setCurrentItem(item)
        path = self.selected_path()
        menu = QMenu(self)
        if is_video(path):
            play = menu.addAction(tr('Play video'))
            play.setToolTip(tr('Open the recording in the default video player'))
            play.triggered.connect(lambda: self.open_requested.emit(str(path)))
        else:
            duplicate = menu.addAction(tr('Duplicate'))
            duplicate.setToolTip(native_help('Duplicate selected image (Ctrl+D)'))
            duplicate.triggered.connect(lambda: self.duplicate_selected(path))
        delete = menu.addAction(tr('Delete'))
        delete.setToolTip(tr('Move selected image to the system trash (Delete)'))
        delete.triggered.connect(lambda: self.delete_selected(path))
        return menu

    def show_context_menu(self, position):
        menu = self.context_menu(position)
        if menu is not None:
            menu.exec(self.grid.viewport().mapToGlobal(position))
            menu.deleteLater()

    def refresh(self, select=None):
        if self._stopped:
            return
        # clicked(bool) must not be interpreted as a file to select.
        select = select if isinstance(select, (str, Path)) else self.selected_path()
        self._loader.stop()
        self._pending.clear()
        self.grid.clear()
        try:
            entries = self.store.items()
        except OSError as exc:
            self._message = ('Could not read the workspace: {details}', {'details': str(exc)})
            entries = []
        placeholder = icon('▧')
        video_icon = video_placeholder()
        valid_keys = set()
        for path in entries:
            try:
                stat = path.stat()
                key = (str(path), stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
            valid_keys.add(key)
            item = QListWidgetItem(self._cache.get(key, video_icon if is_video(path) else placeholder), path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(escape(path.name))
            self.grid.addItem(item)
            if key not in self._cache:
                self._pending.append((path, key, item))
            if select is not None and path == Path(select):
                self.grid.setCurrentItem(item)
        self._cache = {key: value for key, value in self._cache.items() if key in valid_keys}
        watched = self.watcher.files()
        if watched:
            self.watcher.removePaths(watched)
        if entries:
            self.watcher.addPaths([str(path) for path in entries])
        self.retranslate()
        if self._pending:
            self._loader.start(0)

    def load_thumbnails(self):
        for _ in range(min(8, len(self._pending))):
            path, key, item = self._pending.popleft()
            if is_video(path):
                thumbnail = video_thumbnail(self.store.thumbnail_path(path))
                if thumbnail is not None:
                    self._cache[key] = thumbnail
                    item.setIcon(thumbnail)
                continue
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            size = reader.size()
            if size.isValid():
                size.scale(QSize(240, 180), Qt.AspectRatioMode.KeepAspectRatio)
                reader.setScaledSize(size)
            image = reader.read()
            if not image.isNull():
                thumbnail = QIcon(QPixmap.fromImage(image))
                self._cache[key] = thumbnail
                item.setIcon(thumbnail)
            else:
                item.setData(Qt.ItemDataRole.UserRole+1, True)
                item.setToolTip(escape(path.name)+'\n'+tr('Could not load the thumbnail.'))
        if not self._pending:
            self._loader.stop()

    def duplicate_selected(self, path=None):
        path = path if path is not None else self.selected_path()
        if path is None:
            return
        try:
            result = self.store.duplicate(path)
            self._message = ('Created a copy of {name}.', {'name': path.name})
            self.refresh(select=result)
        except OSError as exc:
            self._message = ('Could not duplicate the image: {details}', {'details': str(exc)})
            self.retranslate()

    def delete_selected(self, path=None):
        path = path if path is not None else self.selected_path()
        if path is None:
            return
        try:
            self.store.trash(path)
            self._message = ('Moved {name} to the system trash.', {'name': path.name})
            self.refresh()
        except OSError as exc:
            self._message = ('Could not delete the image: {details}', {'details': str(exc)})
            self.retranslate()

    def retranslate(self):
        self.refresh_button.setToolTip(tr('Refresh workspace thumbnails'))
        self.refresh_button.setAccessibleName(tr('Refresh'))
        self.grid.setToolTip(tr('Double-click to open an image or play a recording. Drag a thumbnail onto the editor to add it as an editable image.'))
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            if item.data(Qt.ItemDataRole.UserRole+1):
                item.setToolTip(escape(item.text())+'\n'+tr('Could not load the thumbnail.'))
        limit = str(self.store.limit) if self.store.limit else tr('No limit')
        videos = sum(is_video(self.grid.item(index).text()) for index in range(self.grid.count()))
        text = tr('Images: {count} • Limit: {limit}').format(count=self.grid.count()-videos, limit=limit)
        if videos:
            text += ' • '+tr('Recordings: {count}').format(count=videos)
        self.count_label.setText(text)
        if self.store.retention_error:
            message = tr('Could not apply the workspace limit: {details}').format(details=tr(self.store.retention_error))
        elif self._message:
            details = self._message[1].copy()
            if 'details' in details:
                details['details'] = tr(details['details'])
            message = tr(self._message[0]).format(**details)
        elif self.store.limit and self.grid.count()-videos > self.store.limit:
            message = tr('The limit will be applied when an image is saved.')
        else:
            message = ''
        self.status.setText(message)
        self.status.setVisible(bool(message))

    def stop(self):
        self._stopped = True
        self._loader.stop()
        self._refresh_timer.stop()
        paths = self.watcher.files()+self.watcher.directories()
        if paths:
            self.watcher.removePaths(paths)


def play_badge(pixmap):
    """Overlay a round play symbol so recordings stand out from images."""
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    size = min(pixmap.width(), pixmap.height())*.38
    center = QPointF(pixmap.width()/2, pixmap.height()/2)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 150))
    painter.drawEllipse(center, size/2, size/2)
    painter.setBrush(QColor('white'))
    r = size/5
    painter.drawPolygon(QPolygonF([center+QPointF(-r*.8, -r), center+QPointF(-r*.8, r), center+QPointF(r*1.2, 0)]))
    painter.end()
    return pixmap


def video_placeholder():
    pixmap = QPixmap(240, 180)
    pixmap.fill(QColor('#202B37'))
    return QIcon(play_badge(pixmap))


def video_thumbnail(path):
    image = read_image(path)
    if image.isNull():
        return None
    return QIcon(play_badge(QPixmap.fromImage(image)))
