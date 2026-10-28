from .i18n import tr
"""Download verified public GitHub release packages; never build on the client."""
import hashlib
import json
import os
import platform
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
REPOSITORY = 'NadsonJR/ScreenDepresso'
LATEST_MANIFEST = f'https://github.com/{REPOSITORY}/releases/latest/download/update.json'
MAX_PACKAGE_SIZE = 600 * 1024 * 1024

def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch('\\d+\\.\\d+\\.\\d+', value):
        raise ValueError(tr('Invalid update version.'))
    return tuple((int(part) for part in value.split('.')))

def safe_url(url):
    parsed = urllib.parse.urlsplit(url)
    hosts = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
    if parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password or (parsed.port not in (None, 443)):
        raise ValueError(tr('Download destination is not allowed.'))
    return url

class SafeRedirect(urllib.request.HTTPRedirectHandler):

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def open_url(url):
    request = urllib.request.Request(safe_url(url), headers={'User-Agent': 'ScreenDepresso-Updater', 'Accept': 'application/octet-stream'})
    return urllib.request.build_opener(SafeRedirect()).open(request, timeout=30)

@dataclass(frozen=True)
class Release:
    version: str
    filename: str
    url: str
    sha256: str
    size: int

    @classmethod
    def parse(cls, data, current_version, machine=None, system=None):
        version = data.get('version')
        if version_tuple(version) <= version_tuple(current_version):
            return None
        system = system or platform.system()
        if (machine or platform.machine()).lower() not in ('x86_64', 'amd64') or system not in ('Linux', 'Windows'):
            raise ValueError(tr('Updates are only available for Windows and Linux x86_64.'))
        windows = system == 'Windows'
        filename = f'screendepresso_{version}_windows_amd64_setup.exe' if windows else f'screendepresso_{version}_amd64.deb'
        package = data.get('windows-amd64' if windows else 'linux-amd64', {})
        url = f'https://github.com/{REPOSITORY}/releases/download/v{version}/{filename}'
        if package.get('url') != url:
            raise ValueError(tr('Invalid package source.'))
        digest = package.get('sha256', '')
        size = package.get('size')
        if not re.fullmatch('[0-9a-f]{64}', digest) or type(size) is not int or (not 0 < size <= MAX_PACKAGE_SIZE):
            raise ValueError(tr('Invalid package metadata.'))
        return cls(version, filename, url, digest, size)

def check_update(current_version):
    with open_url(LATEST_MANIFEST) as response:
        content = response.read(64 * 1024 + 1)
    if len(content) > 64 * 1024:
        raise ValueError(tr('Update manifest exceeds the size limit.'))
    return Release.parse(json.loads(content), current_version)

def download_release(release, progress=None):
    directory = Path(tempfile.mkdtemp(prefix='screendepresso-update-'))
    path = directory / release.filename
    try:
        digest = hashlib.sha256()
        count = 0
        if progress:
            progress(0, release.size)
        with open_url(release.url) as response, path.open('xb') as output:
            while (chunk := response.read(1024 * 1024)):
                count += len(chunk)
                if count > release.size:
                    raise ValueError(tr('Download is larger than the announced package.'))
                digest.update(chunk)
                output.write(chunk)
                if progress:
                    progress(count, release.size)
        if count != release.size or digest.hexdigest() != release.sha256:
            raise ValueError(tr('SHA-256 verification failed. The package was discarded.'))
        directory.chmod(493)
        path.chmod(420)
        return path
    except Exception:
        shutil.rmtree(directory)
        raise

def system_environment():
    """Undo PyInstaller's library overrides before launching system binaries."""
    env = os.environ.copy()
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    original = env.pop('LD_LIBRARY_PATH_ORIG', None)
    if original:
        env['LD_LIBRARY_PATH'] = original
    else:
        env.pop('LD_LIBRARY_PATH', None)
    for name in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
        env.pop(name, None)
    return env


def start_windows_installer(path, restart=False):
    """Detach the verified installer; it outlives the current app during upgrade."""
    import ctypes
    import subprocess
    import sys
    bundled = getattr(sys, 'frozen', False)
    kernel = None
    if bundled and sys.platform == 'win32':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        kernel.SetDllDirectoryW(None)
    try:
        options = ['/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS']
        if restart:
            options = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
                       '/CLOSEAPPLICATIONS', '/NORESTARTAPPLICATIONS', '/SCREENDEPRESSO_RESTART=1']
        return subprocess.Popen([str(path), *options], env=system_environment())
    finally:
        if kernel is not None:
            kernel.SetDllDirectoryW(getattr(sys, '_MEIPASS', None))


def start_restarted_application():
    """Start the new installation; it waits for the current instance to exit."""
    import subprocess
    import sys
    command = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'screendepresso.app']
    return subprocess.Popen([*command, '--restart-after-update'], env=system_environment(),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
