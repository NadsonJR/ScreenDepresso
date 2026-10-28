"""Independent shared-layer and legacy sequential reverse-blur renderers."""
from PIL import Image, ImageFilter
from PySide6.QtGui import QImage, QPainter


def blurred_image(image, radius):
    pixels = image.convertToFormat(QImage.Format.Format_RGBA8888)
    source = Image.frombytes('RGBA', (pixels.width(), pixels.height()),
                             bytes(pixels.bits()), 'raw', 'RGBA', pixels.bytesPerLine())
    data = source.filter(ImageFilter.GaussianBlur(radius)).tobytes()
    return QImage(data, pixels.width(), pixels.height(), pixels.bytesPerLine(),
                  QImage.Format.Format_RGBA8888).copy()


def shared_blur(image, regions):
    """Blur once, restoring the union of clear regions from the original layer."""
    if not regions:
        return image.copy()
    result = blurred_image(image, max(radius for rect, radius in regions))
    painter = QPainter(result)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    for rect, radius in regions:
        painter.drawImage(rect.topLeft(), image.copy(rect))
    painter.end()
    return result.convertToFormat(QImage.Format.Format_ARGB32)


def sequential_blur(image, rect, radius):
    """Preserve the pre-0.6.2 behavior for one effect, including prior annotations."""
    original = image.copy(rect)
    blurred = blurred_image(image, radius)
    painter = QPainter(image)
    painter.drawImage(0, 0, blurred)
    painter.drawImage(rect.topLeft(), original)
    painter.end()
