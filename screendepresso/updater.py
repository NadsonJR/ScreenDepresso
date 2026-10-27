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

REPOSITORY = 'NadsonJR/ScreenDepresso-releases'
LATEST_MANIFEST = f'https://github.com/{REPOSITORY}/releases/latest/download/update.json'
MAX_PACKAGE_SIZE = 600 * 1024 * 1024


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('Versão de atualização inválida.')
    return tuple(int(part) for part in value.split('.'))


def safe_url(url):
    parsed = urllib.parse.urlsplit(url)
    hosts = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
    if parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Destino de download não permitido.')
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
    def parse(cls, data, current_version, machine=None):
        version = data.get('version')
        if version_tuple(version) <= version_tuple(current_version):
            return None
        if (machine or platform.machine()) not in ('x86_64', 'amd64'):
            raise ValueError('Atualização disponível somente para Linux x86_64.')
        filename = f'screendepresso_{version}_amd64.deb'
        package = data.get('linux-amd64', {})
        url = f'https://github.com/{REPOSITORY}/releases/download/v{version}/{filename}'
        if package.get('url') != url:
            raise ValueError('Origem do pacote inválida.')
        digest = package.get('sha256', '')
        size = package.get('size')
        if not re.fullmatch(r'[0-9a-f]{64}', digest) or type(size) is not int or not 0 < size <= MAX_PACKAGE_SIZE:
            raise ValueError('Metadados do pacote inválidos.')
        return cls(version, filename, url, digest, size)


def check_update(current_version):
    with open_url(LATEST_MANIFEST) as response:
        content = response.read(64 * 1024 + 1)
    if len(content) > 64 * 1024:
        raise ValueError('Manifesto de atualização excede o limite.')
    return Release.parse(json.loads(content), current_version)


def download_release(release):
    directory = Path(tempfile.mkdtemp(prefix='screendepresso-update-'))
    path = directory / release.filename
    try:
        digest = hashlib.sha256()
        count = 0
        with open_url(release.url) as response, path.open('xb') as output:
            while chunk := response.read(1024 * 1024):
                count += len(chunk)
                if count > release.size:
                    raise ValueError('Download maior que o pacote anunciado.')
                digest.update(chunk)
                output.write(chunk)
        if count != release.size or digest.hexdigest() != release.sha256:
            raise ValueError('Falha na verificação SHA-256. O pacote foi descartado.')
        # apt's unprivileged download user must be able to read the verified file.
        directory.chmod(0o755)
        path.chmod(0o644)
        return path
    except Exception:
        shutil.rmtree(directory)
        raise


def system_environment():
    """Undo PyInstaller's library overrides before launching system binaries."""
    env = os.environ.copy()
    original = env.pop('LD_LIBRARY_PATH_ORIG', None)
    if original:
        env['LD_LIBRARY_PATH'] = original
    else:
        env.pop('LD_LIBRARY_PATH', None)
    for name in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
        env.pop(name, None)
    return env
