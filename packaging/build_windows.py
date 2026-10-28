"""Build the native Windows x64 bundle and per-user Inno Setup installer."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import os
from PySide6.QtCore import QLibraryInfo
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from screendepresso import __version__


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('Build this installer on Windows x64.')
    build = ROOT/'build'
    build.mkdir(exist_ok=True)
    icon = Image.new('RGBA', (256, 256))
    draw = ImageDraw.Draw(icon)
    draw.rounded_rectangle((16,16,240,240), radius=52, fill='#EF4059')
    draw.rounded_rectangle((58,74,198,180), radius=16, outline='#F4F7FB', width=14)
    draw.ellipse((98,96,158,156), outline='#F4F7FB', width=12)
    draw.line([(88,74),(102,50),(154,50),(168,74)], fill='#F4F7FB', width=14)
    icon.save(build/'screendepresso.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    translation = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))/'qtbase_pt_BR.qm'
    if not translation.is_file():
        raise SystemExit('Qt Brazilian Portuguese translation is missing.')
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', 'screendepresso', '--paths', str(ROOT), '--icon', str(build/'screendepresso.ico'),
        '--add-data', str(translation)+os.pathsep+'screendepresso/translations',
        '--exclude-module', 'Xlib', '--exclude-module', 'PySide6.QtWebEngineCore',
        '--exclude-module', 'PySide6.QtWebEngineWidgets', '--exclude-module', 'PySide6.QtQml',
        '--exclude-module', 'PySide6.QtQuick', str(ROOT/'packaging/entrypoint.py'))
    bundle = ROOT/'dist/screendepresso'
    notices = bundle/'licenses'
    for name in ('PySide6', 'PySide6-Essentials', 'shiboken6', 'Pillow', 'Send2Trash', 'pyinstaller'):
        distribution = importlib.metadata.distribution(name)
        for entry in distribution.files or []:
            if any(word in str(entry).lower() for word in ('license','copying','copyright','notice')):
                source = Path(distribution.locate_file(entry))
                if source.is_file():
                    target = notices/name/str(entry).replace('..','_')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.exists():
        notices.mkdir(exist_ok=True)
        shutil.copy2(python_license, notices/'Python-LICENSE.txt')
    (bundle/'THIRD_PARTY.txt').write_text(
        'Includes Python, Qt/PySide6, Shiboken6, Pillow and Send2Trash. License notices are in licenses/.\n'
        'Qt libraries are dynamically linked. Qt sources and licensing: https://code.qt.io/ and https://www.qt.io/licensing/\n'
        'Application source: https://github.com/NadsonJR/ScreenDepresso\n', encoding='utf-8')
    compiler = shutil.which('ISCC.exe') or str(Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'))/'Inno Setup 6/ISCC.exe')
    if not Path(compiler).is_file():
        raise SystemExit('Inno Setup 6 is required on the build machine.')
    run(compiler, f'/DAppVersion={__version__}', str(ROOT/'packaging/windows.iss'))
    filename = f'screendepresso_{__version__}_windows_amd64_setup.exe'
    package = ROOT/'dist'/filename
    with package.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'version': __version__, 'windows-amd64': {
        'url': f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v{__version__}/{filename}',
        'sha256': digest, 'size': package.stat().st_size}}
    (ROOT/'dist/windows-update.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    (ROOT/'dist/WINDOWS-SHA256SUMS').write_text(f'{digest}  {filename}\n', encoding='utf-8')
    print(package)


if __name__ == '__main__':
    main()
