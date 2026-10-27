import hashlib
import io
from pathlib import Path

import pytest

from screendepresso import updater


def manifest(content=b'package', version='0.3.0'):
    filename = f'screendepresso_{version}_amd64.deb'
    return {'version': version, 'linux-amd64': {
        'url': f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v{version}/{filename}',
        'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}}


def test_select_new_version():
    release = updater.Release.parse(manifest(version='0.10.0'), '0.9.0', 'x86_64')
    assert release.version == '0.10.0'
    assert updater.Release.parse(manifest(), '0.3.0', 'x86_64') is None
    assert updater.Release.parse(manifest(), '1.0.0', 'x86_64') is None


@pytest.mark.parametrize('field,value', [('url', 'https://evil.example/app.deb'), ('sha256', 'bad'), ('size', -1), ('size', updater.MAX_PACKAGE_SIZE + 1)])
def test_reject_untrusted_manifest(field, value):
    data = manifest()
    data['linux-amd64'][field] = value
    with pytest.raises(ValueError):
        updater.Release.parse(data, '0.2.0', 'x86_64')


@pytest.mark.parametrize('url', ['http://github.com/file', 'https://evil.example/file', 'https://user:pass@github.com/file', 'https://github.com:444/file'])
def test_reject_unsafe_urls(url):
    with pytest.raises(ValueError):
        updater.safe_url(url)


def test_download_verifies_and_preserves_bytes(monkeypatch, tmp_path):
    monkeypatch.setattr(updater.tempfile, 'mkdtemp', lambda **kwargs: str(tmp_path))
    monkeypatch.setattr(updater, 'open_url', lambda url: io.BytesIO(b'package'))
    release = updater.Release.parse(manifest(), '0.2.0', 'x86_64')
    path = updater.download_release(release)
    assert path.read_bytes() == b'package'


@pytest.mark.parametrize('content', [b'corrupt', b'package-extra', b'short'])
def test_bad_download_removed(monkeypatch, tmp_path, content):
    directory = tmp_path / 'download'
    directory.mkdir()
    monkeypatch.setattr(updater.tempfile, 'mkdtemp', lambda **kwargs: str(directory))
    monkeypatch.setattr(updater, 'open_url', lambda url: io.BytesIO(content))
    release = updater.Release.parse(manifest(), '0.2.0', 'x86_64')
    with pytest.raises(ValueError):
        updater.download_release(release)
    assert not directory.exists()


def test_network_error_removes_partial_download(monkeypatch, tmp_path):
    directory = tmp_path / 'download'
    directory.mkdir()
    monkeypatch.setattr(updater.tempfile, 'mkdtemp', lambda **kwargs: str(directory))
    def failure(url):
        raise OSError('Network unavailable')
    monkeypatch.setattr(updater, 'open_url', failure)
    with pytest.raises(OSError):
        updater.download_release(updater.Release.parse(manifest(), '0.2.0', 'x86_64'))
    assert not directory.exists()


def test_restore_system_environment(monkeypatch):
    monkeypatch.setenv('LD_LIBRARY_PATH', '/opt/app/_internal')
    monkeypatch.setenv('LD_LIBRARY_PATH_ORIG', '/usr/local/lib')
    monkeypatch.setenv('QT_PLUGIN_PATH', '/opt/app/plugins')
    result = updater.system_environment()
    assert result['LD_LIBRARY_PATH'] == '/usr/local/lib'
    assert 'QT_PLUGIN_PATH' not in result


def test_check_update_reads_manifest(monkeypatch):
    import json
    monkeypatch.setattr(updater, 'open_url', lambda url: io.BytesIO(json.dumps(manifest()).encode()))
    assert updater.check_update('0.2.0').version == '0.3.0'


def test_check_update_rejects_oversized_manifest(monkeypatch):
    monkeypatch.setattr(updater, 'open_url', lambda url: io.BytesIO(b'x' * 70000))
    with pytest.raises(ValueError, match='limit'):
        updater.check_update('0.2.0')


def test_unsupported_architecture():
    with pytest.raises(ValueError, match='x86_64'):
        updater.Release.parse(manifest(), '0.2.0', 'aarch64')


def test_redirect_cannot_downgrade_to_http():
    with pytest.raises(ValueError):
        updater.SafeRedirect().redirect_request(None, None, 302, 'Found', {}, 'http://github.com/package')
