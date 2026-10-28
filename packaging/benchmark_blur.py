"""Reproducible offscreen blur benchmark; each resolution gets a fresh process.

Use --source to compare a previous checkout without changing the working tree.
This measures editor paints/exports, not capture, disk I/O or monitor refresh.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


def measure(args, size):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    sys.path.insert(0, str(Path(args.source).resolve()))
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QPainter, QColor
    from PySide6.QtWidgets import QApplication
    from screendepresso.editor import Canvas
    from screendepresso import __version__
    app = QApplication([])
    width, height = map(int, size.lower().split('x'))
    source = QImage(width, height, QImage.Format.Format_ARGB32)
    painter = QPainter(source)
    for x in range(0, width, 32):
        painter.fillRect(x, 0, 32, height, QColor((x*7)%256, (x*13)%256, (x*3)%256))
    painter.end()
    canvas = Canvas()
    canvas.load(source)
    canvas.blur_mode = args.mode
    canvas.objects = [{'kind':'desfoque', 'a':[width//4,height//4],
                       'b':[width//2,height//2], 'radius':14}]
    target = QImage(1280, 720, QImage.Format.Format_ARGB32)
    target.fill(QColor('#202B37'))
    def frame():
        painter = QPainter(target)
        if hasattr(canvas, 'paint_document'):
            canvas.paint_document(painter)
        else:
            painter.drawImage(0, 0, canvas.render_image(True))
        painter.end()
    def timed(function, count=args.repeat):
        samples = []
        for _ in range(count):
            start = time.perf_counter()
            function()
            samples.append((time.perf_counter()-start)*1000)
        return round(statistics.median(samples), 3)
    start = time.perf_counter()
    first = timed(frame, 1)
    engine = getattr(canvas, 'blur_preview', None)
    if engine is not None and engine.future is not None:
        engine.future.result(timeout=180)
        app.processEvents()
    full_ready = round((time.perf_counter()-start)*1000, 3)
    idle = timed(frame)
    canvas.pending = {'kind':'desfoque', 'a':[80,80], 'b':[640,480], 'radius':14}
    def drag():
        canvas.pending['b'][0] += 7
        frame()
    moving = timed(drag)
    canvas.pending = None
    export = timed(lambda: canvas.image, 1)
    try:
        import resource
        divisor = 1024*1024 if sys.platform == 'darwin' else 1024
        memory = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/divisor, 1)
    except ImportError:
        memory = None
    return {'version':__version__, 'resolution':size, 'mode':args.mode, 'samples':args.repeat,
            'first_paint_ms':first, 'full_ready_ms':full_ready, 'idle_paint_ms':idle,
            'drag_paint_ms':moving, 'warm_export_ms':export, 'peak_rss_mib':memory}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--sizes', nargs='+', default=['3840x2160','7680x4320','12000x8000'])
    parser.add_argument('--repeat', type=int, default=3)
    parser.add_argument('--mode', choices=['shared','sequential'], default='shared')
    parser.add_argument('--one', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat must be positive')
    if args.one:
        print(json.dumps(measure(args,args.one)), flush=True)
        return
    for size in args.sizes:
        command = [sys.executable, str(Path(__file__).resolve()), '--source', args.source,
                   '--mode', args.mode, '--repeat', str(args.repeat), '--one', size]
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        if result.returncode:
            raise RuntimeError(result.stderr)
        print(result.stdout.strip(), flush=True)


if __name__ == '__main__':
    main()
