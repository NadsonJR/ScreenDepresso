import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import json
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from screendepresso.recorder import ScreenRecorder, default_recording, normalize_recording, region_crop
from screendepresso.workspace import WorkspaceStore, WorkspaceView
from screendepresso.recording_ui import RecordingBar, format_duration
from screendepresso.settings import DEFAULT_HOTKEYS, Settings, SettingsDialog

app = QApplication.instance() or QApplication([])


def test_recording_options_keep_valid_values_and_reject_invalid_ones(tmp_path):
    options = normalize_recording({'directory': str(tmp_path), 'fps': 60, 'quality': 'high', 'countdown': 0,
                                   'microphone': True, 'microphone_device': 'mic-1'})
    assert options == {'fps': 60, 'quality': 'high', 'countdown': 0, 'microphone': True, 'microphone_device': 'mic-1'}
    fallback = normalize_recording({'fps': 31, 'quality': 'ultra', 'countdown': True,
                                    'microphone': 'yes'})
    assert fallback == default_recording()
    assert normalize_recording(None) == default_recording()


def test_region_crop_scales_to_frame_pixels_with_even_size():
    screen = QRect(1920, 0, 1280, 720)
    crop = region_crop(QRect(2020, 50, 301, 201), screen, QSize(2560, 1440))
    assert crop == QRect(200, 100, 602, 402)
    clipped = region_crop(QRect(3100, 600, 400, 400), screen, QSize(1280, 720))
    assert clipped.right() < 1280 and clipped.bottom() < 720
    assert clipped.width() % 2 == 0 and clipped.height() % 2 == 0


def test_recordings_join_the_workspace_without_counting_toward_the_image_limit(tmp_path):
    store = WorkspaceStore(tmp_path, 25)
    temporary, final = store.recording_target()
    assert temporary.parent.name == '.recording' and final.parent == tmp_path
    temporary.write_bytes(b'video')
    assert store.items() == []  # In-progress recordings stay hidden.
    poster = QImage(240, 135, QImage.Format.Format_ARGB32)
    poster.fill(QColor('red'))
    saved = store.add_video(temporary, final, poster)
    assert saved == final and final.read_bytes() == b'video' and not temporary.parent.exists()
    assert store.thumbnail_path(final).is_file()
    image = store.save(poster)
    assert store.videos() == [final] and store.entries() == [image] and set(store.items()) == {final, image}
    store.limit = 25
    for _ in range(26):
        store.save(poster)
    assert final.exists()  # The limit trims images only.
    view = WorkspaceView(store)
    view.load_thumbnails()
    assert 'Recordings: 1' in view.count_label.text()
    item = next(view.grid.item(i) for i in range(view.grid.count()) if view.grid.item(i).text() == final.name)
    view.grid.setCurrentItem(item)
    menu = view.context_menu(view.grid.visualItemRect(item).center())
    assert [a.text() for a in menu.actions()] == ['Play video', 'Delete']
    view.delete_selected(final)
    assert not final.exists() and not store.thumbnail_path(final).exists()
    view.stop()


def test_legacy_settings_gain_recording_hotkey_and_keep_capture_keys(tmp_path):
    path = tmp_path/'settings.json'
    legacy = {'tela': 'Alt+Print', 'janela': 'Ctrl+Shift+2', 'região': 'Ctrl+Shift+3'}
    path.write_text(json.dumps({'directory': str(tmp_path), 'hotkeys': legacy}), encoding='utf-8')
    settings = Settings(path)
    assert settings.hotkeys == dict(legacy, gravação=DEFAULT_HOTKEYS['gravação'])
    assert settings.recording == default_recording()


def test_legacy_recording_hotkey_avoids_existing_shortcut_and_keeps_preferences(tmp_path):
    path = tmp_path/'settings.json'
    legacy = {'tela': 'Ctrl+Alt+R', 'janela': 'Ctrl+Shift+2', 'região': 'Ctrl+Shift+3'}
    path.write_text(json.dumps({'directory': str(tmp_path/'captures'), 'hotkeys': legacy,
                                'language': 'pt_BR', 'workspace_limit': 50}), encoding='utf-8')
    settings = Settings(path)
    assert settings.directory == str(tmp_path/'captures')
    assert settings.language == 'pt_BR' and settings.workspace_limit == 50
    assert {k: settings.hotkeys[k] for k in legacy} == legacy
    assert settings.hotkeys['gravação'] not in legacy.values()


def test_recording_settings_roundtrip(tmp_path):
    path = tmp_path/'settings.json'
    settings = Settings(path)
    options = dict(default_recording(), fps=15, quality='low', microphone=True)
    settings.save(str(tmp_path), DEFAULT_HOTKEYS, recording=options)
    assert Settings(path).recording == options
    settings.save(str(tmp_path), DEFAULT_HOTKEYS, 'pt_BR')
    assert Settings(path).recording == options


def test_duration_label_and_bar_stays_outside_region():
    assert format_duration(0) == '00:00'
    assert format_duration(75_400) == '01:15'
    assert format_duration(3_725_000) == '1:02:05'
    bar = RecordingBar()
    screen = QRect(0, 0, 1920, 1080)
    region = QRect(400, 200, 800, 400)
    bar.place(screen, region)
    assert not bar.geometry().intersects(region)
    assert screen.contains(bar.geometry())
    bar.set_state('paused')
    assert bar.pause.text() == '▶'
    bar.set_microphone(False)
    assert bar.mute.isHidden()
    bar.close()


def test_idle_recorder_ignores_stop_and_pause():
    recorder = ScreenRecorder()
    recorder.stop()
    recorder.pause()
    recorder.resume()
    assert recorder.state == 'idle' and not recorder.active


def test_record_menu_hotkey_and_settings_tab(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    from screendepresso.app import MainWindow
    window = MainWindow()
    try:
        window.refresh_record_menu()
        labels = [action.text() for action in window.record_menu.actions()]
        assert {'Record full screen', 'Record window…', 'Record region…', 'Open last recording'} <= set(labels)
        calls = []
        monkeypatch.setattr(window, 'record', lambda mode, screen_name=None: calls.append(mode))
        window.capture('gravação')
        assert calls == ['tela']
        microphone = next(a for a in window.record_menu.actions() if a.text() == 'Record microphone audio')
        microphone.setChecked(True)
        assert window.settings.recording['microphone'] and Settings().recording['microphone']
        # The ribbon button and tray follow the recorder state.
        window.recorder.state = 'recording'
        window.recording_state_changed('recording')
        assert window.record_action.text() == 'Stop' and window.tray_stop_action.isVisible()
        window.recorder.state = 'idle'
        window.recording_state_changed('idle')
        assert window.record_action.text() == 'Record' and not window.tray_stop_action.isVisible()
        dialog = SettingsDialog(window)
        dialog.recording_fps.setCurrentIndex(dialog.recording_fps.findData(60))
        dialog.recording_countdown.setCurrentIndex(dialog.recording_countdown.findData(0))
        dialog.save()
        assert window.settings.recording['fps'] == 60 and window.settings.recording['countdown'] == 0
        # A finished recording moves into the workspace and is selected there.
        temporary, final = window.history.recording_target()
        temporary.write_bytes(b'video')
        window._recording_target = (window.history, final, None)
        played = []
        monkeypatch.setattr(window, 'play_video', lambda path: played.append(str(path)))
        window.recording_saved(str(temporary))
        assert final.exists() and window.last_recording == str(final)
        assert window.workspace.selected_path() == final
        window.open_history(window.list.currentItem())
        assert played == [str(final)]
    finally:
        window.close()


def test_h264_failure_before_any_frame_restarts_with_mpeg4(tmp_path, monkeypatch):
    recorder = ScreenRecorder()
    calls = []
    monkeypatch.setattr(recorder, '_begin', lambda target, options, path, codec: calls.append((path, codec)))
    monkeypatch.setattr('screendepresso.recorder.remove_later', lambda path, delay=1500: None)
    recorder.state, recorder.codec, recorder._duration = 'starting', 'h264', 0
    recorder.path = tmp_path/'clip.mp4'
    recorder._request = (('screen', None), default_recording(), tmp_path/'clip.mp4')
    recorder._fail('Encoder not found')
    assert calls == [(tmp_path/'clip-mpeg4.mp4', 'mpeg4')]
    # Once frames were written, a failure is reported instead of retried.
    failures = []
    recorder.failed.connect(failures.append)
    class Stopped:
        name = 'StoppedState'

    class Encoder:
        def stop(self): pass
        def recorderState(self): return Stopped()
    recorder.codec, recorder._duration, recorder.state = 'h264', 1200, 'recording'
    recorder._recorder = Encoder()
    recorder._fail('Disk full')
    assert failures == ['Disk full'] and len(calls) == 1


def test_discarded_recording_restores_the_editor(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    from screendepresso.app import MainWindow
    window = MainWindow()
    try:
        opened, failures = [], []
        monkeypatch.setattr(window, 'open_editor', lambda: opened.append(True))
        window.recorder.failed.connect(failures.append)
        window._restore_after_recording = window._capture_pending = True
        window.recorder.state, window.recorder._discard = 'stopping', True
        window.recorder.path = tmp_path/'clip.mp4'
        window.recorder._finish()
        assert opened == [True] and failures == [] and not window._capture_pending
    finally:
        window.close()


def test_macos_microphone_permission_is_settled_before_recording(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path/'data'))
    from PySide6.QtWidgets import QMessageBox
    import screendepresso.app as module
    window = module.MainWindow()
    try:
        window.settings.recording['microphone'] = True
        requests, warnings, prepared = [], [], []
        monkeypatch.setattr(module, 'microphone_permission', lambda: 'undetermined')
        monkeypatch.setattr(module, 'request_microphone_permission', lambda context, callback: requests.append(callback))
        monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args[2]))
        monkeypatch.setattr(window, 'prepare_recording', lambda mode, screen_name=None: prepared.append(mode))
        # A pending permission asks first and does not hide the editor yet.
        window.record('tela')
        assert len(requests) == 1 and window._capture_pending and not warnings
        # A denial is explained once, then the video is recorded without audio.
        requests[0]('denied')
        assert len(warnings) == 1 and window._capture_pending and len(requests) == 1
        window._capture_pending = False
        monkeypatch.setattr(module, 'microphone_permission', lambda: 'granted')
        window.record('tela')
        assert len(requests) == 1 and len(warnings) == 1 and window._capture_pending
    finally:
        window._capture_pending = False
        window.close()
