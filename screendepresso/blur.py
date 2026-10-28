"""Exact reverse blur, a bounded shared cache and responsive canvas previews."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import math
import threading
import weakref
from PIL import Image, ImageFilter
from PySide6.QtCore import QObject, Signal, Qt, QSize
from PySide6.QtGui import QImage, QPainter
from .i18n import tr

# Across all tabs, rather than a full-size cache per document/radius.
# A single image larger than this budget is allowed; it evicts every other entry.
CACHE_BYTES = 256 * 1024 * 1024
PREVIEW_PIXELS = 256 * 1024
ASYNC_PIXELS = 2 * 1024 * 1024
_cache = OrderedDict()
_cache_bytes = 0
_lock = threading.RLock()
_jobs = {}
_executor = None


def blurred_image(image, radius):
    pixels = image.convertToFormat(QImage.Format.Format_RGBA8888)
    # Pillow maps this read-only Qt buffer. Keep pixels alive until filter/tobytes
    # finish; avoid the former bytes(bits()) and Image.frombytes() full copies.
    source = Image.frombuffer('RGBA', (pixels.width(), pixels.height()),
                             pixels.constBits(), 'raw', 'RGBA', pixels.bytesPerLine(), 1)
    data = source.filter(ImageFilter.GaussianBlur(radius)).tobytes()
    return QImage(data, pixels.width(), pixels.height(), pixels.bytesPerLine(),
                  QImage.Format.Format_RGBA8888).copy()


def _key(image, radius):
    return image.cacheKey(), float(radius)


def _get(key):
    with _lock:
        image = _cache.get(key)
        if image is not None:
            _cache.move_to_end(key)
            return QImage(image)  # Copy on write; callers cannot mutate the cache.


def _compute(image, radius):
    global _cache_bytes
    result = blurred_image(image, radius).convertToFormat(QImage.Format.Format_ARGB32)
    key = _key(image, radius)
    with _lock:
        previous = _cache.pop(key, None)
        if previous is not None:
            _cache_bytes -= previous.sizeInBytes()
        _cache[key] = QImage(result)
        _cache_bytes += result.sizeInBytes()
        while len(_cache) > 1 and _cache_bytes > CACHE_BYTES:
            _, oldest = _cache.popitem(last=False)
            _cache_bytes -= oldest.sizeInBytes()
    return result


def cached_blurred_image(image, radius):
    key = _key(image, radius)
    result = _get(key)
    if result is not None:
        return result
    with _lock:
        future = _jobs.get(key)
    if future is not None:
        try:
            return QImage(future.result())
        except Exception:
            # A superseded queued preview can be cancelled; an explicit export
            # still computes the requested image exactly.
            pass
    return _compute(image, radius)


def _request(image, radius):
    global _executor
    key = _key(image, radius)
    with _lock:
        # One running job plus the most recent queued request, even when the
        # user scrubs intensity or switches quickly between large-image tabs.
        for previous_key, future in list(_jobs.items()):
            if previous_key != key and not future.running():
                future.cancel()
        existing = _jobs.get(key)
        if existing is not None:
            return existing
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='screendepresso-blur')
        future = _executor.submit(_compute, QImage(image), radius)
        _jobs[key] = future
        def finished(completed):
            with _lock:
                if _jobs.get(key) is completed:
                    _jobs.pop(key, None)
        future.add_done_callback(finished)
        return future


def clear_blur_cache():
    """Release completed cached layers (existing returned QImages stay valid)."""
    global _cache_bytes
    with _lock:
        _cache.clear()
        _cache_bytes = 0


def shared_blur(image, regions):
    """Exact export: blur once and restore the union of clear regions."""
    if not regions:
        return QImage(image)
    result = cached_blurred_image(image, max(radius for rect, radius in regions))
    painter = QPainter(result)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    for rect, radius in regions:
        painter.drawImage(rect, image, rect)
    painter.end()
    return result


def sequential_blur(image, rect, radius):
    """Preserve the original legacy compositing order, including annotations."""
    original = image.copy(rect)
    blurred = cached_blurred_image(image, radius)
    painter = QPainter(image)
    painter.drawImage(0, 0, blurred)
    painter.drawImage(rect.topLeft(), original)
    painter.end()


class BlurPreview(QObject):
    ready = Signal(object)
    busy_changed = Signal(bool)
    failed = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.wanted = None
        self.future = None
        self.scaled_key = None
        self.scaled = QImage()
        self.small_key = None
        self.small = QImage()
        self.failed_key = None
        self.busy = False
        self.ready.connect(self.completed)

    def set_busy(self, value):
        if value != self.busy:
            self.busy = value
            self.busy_changed.emit(value)

    def reset(self):
        self.wanted = None
        self.future = None
        self.scaled_key = self.small_key = self.failed_key = None
        self.scaled = self.small = QImage()
        self.set_busy(False)

    def preview(self, image, radius):
        key = _key(image, radius)
        result = _get(key)
        if result is not None:
            self.wanted = key
            self.future = None
            self.failed_key = None
            self.set_busy(False)
            return result
        if image.width()*image.height() <= ASYNC_PIXELS:
            self.wanted = key
            self.future = None
            self.set_busy(False)
            return cached_blurred_image(image, radius)
        if key != self.failed_key and (key != self.wanted or self.future is None or self.future.cancelled()):
            self.wanted = key
            self.failed_key = None
            self.future = _request(image, radius)
            self.set_busy(True)
            weak = weakref.ref(self)
            def done(future):
                owner = weak()
                if owner is not None:
                    try:
                        owner.ready.emit((key, future))
                    except RuntimeError:
                        pass  # The tab/application was closed while filtering.
            self.future.add_done_callback(done)
        # During the background calculation only: bounded, approximate preview.
        # Clear regions and all annotations are still drawn at original resolution.
        if self.scaled_key != image.cacheKey():
            factor = min(1.0, math.sqrt(PREVIEW_PIXELS/(image.width()*image.height())))
            width, height = max(1, int(image.width()*factor)), max(1, int(image.height()*factor))
            if width*height > PREVIEW_PIXELS:
                if width >= height:
                    width = max(1, PREVIEW_PIXELS//height)
                else:
                    height = max(1, PREVIEW_PIXELS//width)
            size = QSize(width, height)
            # This is only the temporary preview. Nearest-neighbour sampling
            # avoids scanning every source pixel in a 96+ MP image on the UI
            # thread; the exact Gaussian layer replaces it when ready.
            self.scaled = image.scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.FastTransformation)
            self.scaled_key = image.cacheKey()
            self.small_key = None
        small_key = key, self.scaled.size()
        if self.small_key != small_key:
            factor = self.scaled.width()/image.width()
            self.small = blurred_image(self.scaled, radius*factor)
            self.small_key = small_key
        return QImage(self.small)

    def completed(self, result):
        key, future = result
        if key != self.wanted or future is not self.future:
            return
        if future.cancelled():
            # A different visible document superseded this queued request.
            self.future = None
            self.set_busy(False)
            return
        # The shared LRU owns the completed bitmap. Do not also pin it through
        # a finished Future in every tab after that LRU evicts it.
        self.future = None
        self.set_busy(False)
        if future.exception() is not None:
            self.failed_key = key
            self.failed.emit(tr('Could not render the full-resolution blur preview.'))
            return
        self.parent().update()
