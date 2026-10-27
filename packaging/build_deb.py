"""Build a self-contained Ubuntu 24.04+ amd64 package on Ubuntu 24.04."""
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from screendepresso import __version__


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    if platform.machine() != 'x86_64':
        raise SystemExit('Build must run on x86_64.')
    if not re_version(__version__):
        raise SystemExit('Version must have format X.Y.Z.')
    output = ROOT / 'dist'
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
        '--name', 'screendepresso', '--paths', str(ROOT),
        '--hidden-import', 'Xlib.ext', '--collect-submodules', 'Xlib',
        '--exclude-module', 'PySide6.QtWebEngineCore', '--exclude-module', 'PySide6.QtWebEngineWidgets',
        '--exclude-module', 'PySide6.QtQml', '--exclude-module', 'PySide6.QtQuick',
        str(ROOT / 'packaging/entrypoint.py'))
    stage = ROOT / 'build' / 'deb'
    if stage.exists():
        shutil.rmtree(stage)
    (stage / 'DEBIAN').mkdir(parents=True)
    (stage / 'opt').mkdir()
    shutil.copytree(output / 'screendepresso', stage / 'opt/screendepresso')
    binary = stage / 'usr/bin'
    binary.mkdir(parents=True)
    (binary / 'screendepresso').symlink_to('/opt/screendepresso/screendepresso')
    applications = stage / 'usr/share/applications'
    applications.mkdir(parents=True)
    shutil.copy2(ROOT / 'packaging/screendepresso.desktop', applications)
    icons = stage / 'usr/share/icons/hicolor/scalable/apps'
    icons.mkdir(parents=True)
    shutil.copy2(ROOT / 'packaging/screendepresso.svg', icons)
    docs = stage / 'usr/share/doc/screendepresso'
    docs.mkdir(parents=True)
    shutil.copy2(ROOT / 'README.md', docs)
    (docs / 'THIRD_PARTY.txt').write_text(
        'Contains Python, Qt/PySide6, Shiboken6, Pillow, python-xlib and six.\n'
        'Their license notices are preserved in licenses/. Qt libraries are dynamically linked.\n'
        'Qt/PySide6 upstream sources and license information: https://code.qt.io/ and https://www.qt.io/licensing/\n'
        'Application source and build instructions: https://github.com/NadsonJR/ScreenDepresso\n')
    for name in ('PySide6', 'PySide6-Essentials', 'shiboken6', 'Pillow', 'python-xlib', 'six', 'pyinstaller'):
        dist = importlib.metadata.distribution(name)
        for entry in dist.files or []:
            if any(word in str(entry).lower() for word in ('license', 'copying', 'copyright', 'notice')):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    target = docs / 'licenses' / name / str(entry).replace('..', '_')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    # CPython's distribution notice, including its bundled third-party licenses.
    import sysconfig
    python_license = Path(sysconfig.get_path('stdlib')) / 'LICENSE.txt'
    if python_license.exists():
        shutil.copy2(python_license, docs / 'Python-LICENSE.txt')
    dependencies = ('libc6 (>= 2.39), libstdc++6, libgl1, libegl1, libglib2.0-0t64, '
        'libgssapi-krb5-2, libfontconfig1, libdbus-1-3, libx11-6, libxext6, libxrender1, '
        'libxkbcommon0, libxkbcommon-x11-0, libxcb1, libxcb-cursor0, libxcb-icccm4, '
        'libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-xinerama0, '
        'libxcb-shape0, libxcb-randr0, libxcb-xfixes0, libxcb-sync1, libxcb-xkb1, '
        'libxcb-render0, libxcb-shm0, libxcb-util1, pkexec, ca-certificates')
    size = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file()) // 1024
    (stage / 'DEBIAN/control').write_text(
        f'Package: screendepresso\nVersion: {__version__}\nArchitecture: amd64\n'
        'Maintainer: ScreenDepresso maintainers <noreply@github.com>\nSection: graphics\nPriority: optional\n'
        f'Depends: {dependencies}\nInstalled-Size: {size}\n'
        'Homepage: https://github.com/NadsonJR/ScreenDepresso\n'
        'Description: Screenshot capture and annotation for Linux X11\n'
        ' Includes the Python runtime, editor, history and release updater.\n')
    for directory, subdirs, files in os.walk(stage):
        Path(directory).chmod(0o755)
        for filename in files:
            path = Path(directory) / filename
            if not path.is_symlink():
                path.chmod(0o755 if os.access(path, os.X_OK) else 0o644)
    filename = f'screendepresso_{__version__}_amd64.deb'
    package = output / filename
    run('dpkg-deb', '--root-owner-group', '--build', '-Zxz', str(stage), str(package))
    digest = hashlib.file_digest(package.open('rb'), 'sha256').hexdigest()
    manifest = {'version': __version__, 'linux-amd64': {
        'url': f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v{__version__}/{filename}',
        'sha256': digest, 'size': package.stat().st_size}}
    (output / 'update.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text(f'{digest}  {filename}\n')
    print(package)


def re_version(value):
    import re
    return re.fullmatch(r'\d+\.\d+\.\d+', value)


if __name__ == '__main__':
    main()
