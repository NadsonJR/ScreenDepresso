"""Build a native, ad-hoc signed .app and DMG on Apple Silicon or Intel macOS."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw
from PySide6.QtCore import QLibraryInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from screendepresso import __version__


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    machine = platform.machine().lower()
    if sys.platform != 'darwin' or machine not in ('arm64', 'x86_64'):
        raise SystemExit('Build this disk image on Apple Silicon or Intel macOS.')
    arch = 'arm64' if machine == 'arm64' else 'amd64'
    build = ROOT/'build'
    build.mkdir(exist_ok=True)
    image = Image.new('RGBA', (1024, 1024))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((64, 64, 960, 960), radius=208, fill='#EF4059')
    draw.rounded_rectangle((232, 296, 792, 720), radius=64, outline='#F4F7FB', width=56)
    draw.ellipse((392, 384, 632, 624), outline='#F4F7FB', width=48)
    draw.line([(352,296), (408,200), (616,200), (672,296)], fill='#F4F7FB', width=56)
    image.save(build/'screendepresso.icns')
    translation = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))/'qtbase_pt_BR.qm'
    if not translation.is_file():
        raise SystemExit('Qt Brazilian Portuguese translation is missing.')
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', 'ScreenDepresso', '--paths', str(ROOT), '--icon', str(build/'screendepresso.icns'),
        '--osx-bundle-identifier', 'com.screendepresso.app', '--target-arch', machine,
        '--add-data', str(translation)+os.pathsep+'screendepresso/translations',
        '--exclude-module', 'Xlib', '--exclude-module', 'PySide6.QtWebEngineCore',
        '--exclude-module', 'PySide6.QtWebEngineWidgets', '--exclude-module', 'PySide6.QtQml',
        '--exclude-module', 'PySide6.QtQuick', str(ROOT/'packaging/entrypoint.py'))
    app = ROOT/'dist/ScreenDepresso.app'
    info_path = app/'Contents/Info.plist'
    with info_path.open('rb') as stream:
        info = plistlib.load(stream)
    info.update(CFBundleShortVersionString=__version__, CFBundleVersion=__version__,
                LSMinimumSystemVersion='15.0', NSHighResolutionCapable=True,
                NSScreenCaptureUsageDescription='ScreenDepresso captures screenshots only when you request them.')
    with info_path.open('wb') as stream:
        plistlib.dump(info, stream)
    notices = app/'Contents/Resources/licenses'
    for name in ('PySide6', 'PySide6-Essentials', 'shiboken6', 'Pillow', 'Send2Trash',
                 'pyinstaller', 'pyobjc-core', 'pyobjc-framework-Quartz', 'pyobjc-framework-Cocoa'):
        distribution = importlib.metadata.distribution(name)
        for entry in distribution.files or []:
            if any(word in str(entry).lower() for word in ('license', 'copying', 'notice')):
                source = Path(distribution.locate_file(entry))
                if source.is_file():
                    destination = notices/name/str(entry)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    # No Apple Developer credentials are stored or required. Re-sign after
    # writing our version/permission metadata and third-party notices.
    run('/usr/bin/codesign', '--force', '--deep', '--sign', '-', str(app))
    run('/usr/bin/codesign', '--verify', '--deep', '--strict', str(app))
    staging = build/'macos-dmg'
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    run('/usr/bin/ditto', str(app), str(staging/app.name))
    (staging/'Applications').symlink_to('/Applications', target_is_directory=True)
    (staging/'Install.txt').write_text(
        'Drag ScreenDepresso to Applications, then open it.\n'
        'Requires macOS 15 or later. This build is not notarized by Apple.\n'
        'If macOS blocks the app, use System Settings > Privacy & Security > Open Anyway.\n'
        'Allow Screen & System Audio Recording for ScreenDepresso, then reopen the app.\n'
        'Updates: quit the old app before replacing it in Applications. Your workspace and preferences are preserved.\n', encoding='utf-8')
    filename = f'screendepresso_{__version__}_macos_{arch}.dmg'
    package = ROOT/'dist'/filename
    run('/usr/bin/hdiutil', 'create', '-volname', 'ScreenDepresso', '-srcfolder', str(staging),
        '-ov', '-format', 'UDZO', str(package))
    with package.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'version': __version__, 'macos-'+arch: {
        'url': f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v{__version__}/{filename}',
        'sha256': digest, 'size': package.stat().st_size}}
    (ROOT/'dist/macos-update.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    (ROOT/'dist/MACOS-SHA256SUMS').write_text(f'{digest}  {filename}\n', encoding='utf-8')
    print(package)


if __name__ == '__main__':
    main()
