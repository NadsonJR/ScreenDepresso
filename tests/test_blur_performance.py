"""Pixel compatibility and cache/worker regression checks; no timing thresholds."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from concurrent.futures import CancelledError
import threading
import time
import pytest
from PIL import Image, ImageFilter
from PySide6.QtCore import Qt, QRect, QCoreApplication, QEvent
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from screendepresso import blur
from screendepresso.editor import Canvas

app = QApplication.instance() or QApplication([])


def pattern(width=160, height=120, alpha=False):
    image=QImage(width,height,QImage.Format.Format_ARGB32)
    p=QPainter(image)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    for x in range(0,width,8):
        p.fillRect(x,0,8,height,QColor((x*7)%256,(x*13)%256,(x*3)%256,(x*3)%256 if alpha else 255))
    p.end()
    if alpha:
        # PNGs can retain nonzero RGB even where alpha is zero. Cover both
        # the restored region and the blurred background in the export oracle.
        image.setPixelColor(12,30,QColor(150,77,201,0))
        image.setPixelColor(140,20,QColor(150,77,201,0))
    return image


def original_filter(image,radius):
    """The 0.7.1 filter, deliberately independent of the new cache/preview path."""
    pixels=image.convertToFormat(QImage.Format.Format_RGBA8888)
    source=Image.frombytes('RGBA',(pixels.width(),pixels.height()),bytes(pixels.bits()),
                           'raw','RGBA',pixels.bytesPerLine())
    data=source.filter(ImageFilter.GaussianBlur(radius)).tobytes()
    return QImage(data,pixels.width(),pixels.height(),pixels.bytesPerLine(),QImage.Format.Format_RGBA8888).copy()


def original_render(canvas, objects):
    result=canvas.base.copy()
    regions=[(canvas.object_rect(obj),obj['radius']) for obj in objects if obj['kind']=='desfoque']
    if canvas.blur_mode=='shared' and regions:
        original=QImage(result)
        result=original_filter(original,max(radius for _,radius in regions))
        p=QPainter(result)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        for rect,_ in regions:p.drawImage(rect.topLeft(),original.copy(rect))
        p.end()
        result=result.convertToFormat(QImage.Format.Format_ARGB32)
    for obj in objects:
        if obj['kind']=='desfoque':
            if canvas.blur_mode=='shared':continue
            rect=canvas.object_rect(obj)
            kept=result.copy(rect)
            filtered=original_filter(result,obj['radius'])
            p=QPainter(result)
            p.drawImage(0,0,filtered)
            p.drawImage(rect.topLeft(),kept)
            p.end()
        else:
            canvas.draw_object(result,obj)
    return result


def wait_until(predicate):
    deadline=time.monotonic()+5
    while not predicate() and time.monotonic()<deadline:
        app.processEvents()
        QTest.qWait(5)
    assert predicate()


@pytest.fixture(autouse=True)
def clean_cache():
    blur.clear_blur_cache()
    yield
    with blur._lock:futures=list(blur._jobs.values())
    for future in futures:
        try:future.result(timeout=5)
        except CancelledError:pass
    app.processEvents()
    blur.clear_blur_cache()


@pytest.mark.parametrize('mode',['shared','sequential'])
@pytest.mark.parametrize('alpha',[False,True])
def test_export_pixels_match_071_with_overlapping_regions_and_annotations(mode,alpha):
    canvas=Canvas();canvas.load(pattern(alpha=alpha));canvas.blur_mode=mode
    canvas.objects=[{'kind':'retângulo','a':[4,4],'b':[140,105],'color':'#2563eb'},
        {'kind':'desfoque','a':[-10,-10],'b':[65,65],'radius':14},
        {'kind':'seta','a':[20,100],'b':[140,100],'color':'#ef233c','style':'classic'},
        {'kind':'desfoque','a':[40,30],'b':[130,105],'radius':5}]
    expected=original_render(canvas,canvas.objects)
    assert canvas.image==expected
    canvas.pending={'kind':'desfoque','a':[0,80],'b':[140,115],'radius':22}
    assert canvas.render_image(True)==original_render(canvas,canvas.objects+[canvas.pending])
    # A caller mutating an exported QImage must not corrupt the cache/base.
    canvas.image.fill(QColor('black'))
    assert canvas.image==expected


@pytest.mark.parametrize('mode',['shared','sequential'])
def test_cached_full_quality_viewport_matches_export_for_opaque_screenshots(mode):
    canvas=Canvas();canvas.load(pattern());canvas.blur_mode=mode
    canvas.objects=[{'kind':'desfoque','a':[20,20],'b':[90,75],'radius':14},
                    {'kind':'retângulo','a':[5,5],'b':[150,110],'color':'#00ff00'}]
    expected=canvas.image
    target=QImage(canvas.base.size(),QImage.Format.Format_ARGB32)
    target.fill(QColor('#202B37'))
    p=QPainter(target);canvas.paint_document(p);p.end()
    assert target==expected


def test_shared_transparent_regions_do_not_apply_alpha_twice():
    canvas=Canvas();canvas.load(pattern(alpha=True))
    canvas.objects=[{'kind':'desfoque','a':[20,20],'b':[100,90],'radius':14}]
    expected=QImage(canvas.base.size(),QImage.Format.Format_ARGB32)
    expected.fill(QColor('#202B37'))
    p=QPainter(expected);p.drawImage(0,0,canvas.image);p.end()
    target=QImage(canvas.base.size(),QImage.Format.Format_ARGB32)
    target.fill(QColor('#202B37'))
    p=QPainter(target);canvas.paint_document(p);p.end()
    assert target==expected


@pytest.mark.parametrize('mode',['shared','sequential'])
def test_painting_and_moving_clear_regions_reuses_one_gaussian_filter(mode,monkeypatch):
    calls=[];original=blur.blurred_image
    def counted(image,radius):
        calls.append((image.cacheKey(),radius));return original(image,radius)
    monkeypatch.setattr(blur,'blurred_image',counted)
    canvas=Canvas();canvas.load(pattern());canvas.blur_mode=mode
    canvas.objects=[{'kind':'desfoque','a':[20,20],'b':[100,80],'radius':14}]
    target=QImage(160,120,QImage.Format.Format_ARGB32)
    for _ in range(5):
        canvas.objects[0]['b'][0]+=2
        p=QPainter(target);canvas.paint_document(p);p.end()
    assert len(calls)==1
    canvas.objects[0]['radius']=30
    p=QPainter(target);canvas.paint_document(p);p.end()
    assert len(calls)==2
    canvas.base.setPixelColor(0,0,QColor('white'))
    p=QPainter(target);canvas.paint_document(p);p.end()
    assert len(calls)==3


def test_base_change_crop_and_undo_never_use_a_stale_blur():
    canvas=Canvas();canvas.load(pattern())
    canvas.objects=[{'kind':'desfoque','a':[20,20],'b':[100,80],'radius':14}]
    before=canvas.snapshot();expected=canvas.image
    canvas.base=canvas.base.copy(QRect(10,10,120,90))
    canvas.commit(before)
    assert canvas.image==original_render(canvas,canvas.objects)
    canvas.undo()
    assert canvas.image==expected
    canvas.redo()
    assert canvas.image==original_render(canvas,canvas.objects)
    canvas.load(pattern(200,130))
    assert canvas.image==canvas.base


def test_cache_is_bounded_across_images_and_protects_cached_pixels(monkeypatch):
    monkeypatch.setattr(blur,'CACHE_BYTES',32*32*4+8)
    a,b=pattern(32,32),pattern(32,32)
    expected=blur.cached_blurred_image(a,14)
    blur.cached_blurred_image(b,14)
    assert len(blur._cache)==1 and blur._cache_bytes<=blur.CACHE_BYTES
    result=blur.cached_blurred_image(a,14)
    assert result==expected
    result.fill(QColor('black'))
    assert blur.cached_blurred_image(a,14)==expected
    blur.cached_blurred_image(pattern(64,64),14)
    assert len(blur._cache)==1  # An oversized layer evicts everything else.


@pytest.mark.parametrize('replace_base',[False,True])
def test_async_preview_rejects_old_results_and_exports_exact_full_resolution(monkeypatch,replace_base):
    monkeypatch.setattr(blur,'ASYNC_PIXELS',1)
    monkeypatch.setattr(blur,'PREVIEW_PIXELS',64)
    first_gate,second_gate,first_started=threading.Event(),threading.Event(),threading.Event()
    calls=[];original=blur.blurred_image
    def gated(image,radius):
        if image.width()==160:
            calls.append(radius)
            if radius==14:first_started.set()
            assert (first_gate if radius==14 else second_gate).wait(4)
        return original(image,radius)
    monkeypatch.setattr(blur,'blurred_image',gated)
    canvas=Canvas();canvas.load(pattern())
    engine=canvas.blur_preview
    try:
        small=engine.preview(canvas.base,14)
        assert small.width()<canvas.base.width() and engine.busy
        first=engine.future
        assert first_started.wait(2)
        if replace_base:
            replacement=pattern()
            replacement.setPixelColor(0,0,QColor('yellow'))
            canvas.load(replacement)
        engine.preview(canvas.base,30)
        second=engine.future
        first_gate.set();first.result(timeout=4)
        app.processEvents()
        assert engine.busy  # Old completion must not clear the current operation.
        second_gate.set();second.result(timeout=4)
        wait_until(lambda:not engine.busy)
        assert engine.future is None  # Completed images belong to the bounded LRU.
        assert engine.preview(canvas.base,30).size()==canvas.base.size()
        canvas.objects=[{'kind':'desfoque','a':[20,20],'b':[90,75],'radius':30}]
        assert canvas.image==original_render(canvas,canvas.objects)
        assert calls.count(30)==1  # Export reuses the already finished full layer.
    finally:
        first_gate.set();second_gate.set()


def test_closing_a_tab_during_background_filter_does_not_touch_deleted_qobjects(monkeypatch):
    monkeypatch.setattr(blur,'ASYNC_PIXELS',1)
    monkeypatch.setattr(blur,'PREVIEW_PIXELS',64)
    gate=threading.Event();original=blur.blurred_image
    def gated(image,radius):
        if image.width()==160:assert gate.wait(4)
        return original(image,radius)
    monkeypatch.setattr(blur,'blurred_image',gated)
    canvas=Canvas();canvas.load(pattern())
    engine=canvas.blur_preview
    try:
        engine.preview(canvas.base,14)
        future=engine.future
        canvas.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        gate.set();future.result(timeout=4)
        app.processEvents()
    finally:gate.set()


def test_returning_to_running_radius_cancels_superseded_queued_work(monkeypatch):
    monkeypatch.setattr(blur,'ASYNC_PIXELS',1)
    monkeypatch.setattr(blur,'PREVIEW_PIXELS',64)
    gate,started=threading.Event(),threading.Event()
    calls=[];original=blur.blurred_image
    def gated(image,radius):
        if image.width()==160:
            calls.append(radius);started.set();assert gate.wait(4)
        return original(image,radius)
    monkeypatch.setattr(blur,'blurred_image',gated)
    canvas=Canvas();canvas.load(pattern());engine=canvas.blur_preview
    try:
        engine.preview(canvas.base,14)
        first=engine.future
        assert started.wait(2)
        engine.preview(canvas.base,30)
        superseded=engine.future
        engine.preview(canvas.base,14)
        assert engine.future is first and superseded.cancelled()
        gate.set();first.result(timeout=4)
        wait_until(lambda:not engine.busy)
        assert calls==[14]
    finally:gate.set()


def test_worker_failure_keeps_preview_without_repeated_retry_on_every_frame(monkeypatch):
    monkeypatch.setattr(blur,'ASYNC_PIXELS',1)
    monkeypatch.setattr(blur,'PREVIEW_PIXELS',64)
    calls=[];original=blur.blurred_image
    def fail_full(image,radius):
        if image.width()==160:
            calls.append(radius);raise OSError('Synthetic worker error')
        return original(image,radius)
    monkeypatch.setattr(blur,'blurred_image',fail_full)
    canvas=Canvas();canvas.load(pattern());engine=canvas.blur_preview
    engine.preview(canvas.base,14)
    wait_until(lambda:engine.failed_key is not None)
    for _ in range(3):assert not engine.preview(canvas.base,14).isNull()
    assert calls==[14] and not engine.busy
