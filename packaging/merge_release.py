"""Verify both build artifacts before publishing one cross-platform update manifest."""
import hashlib
import json
from pathlib import Path


def merge(linux_directory, windows_directory, output_directory):
    linux_directory, windows_directory = Path(linux_directory), Path(windows_directory)
    output = Path(output_directory)
    linux = json.loads((linux_directory/'update.json').read_text(encoding='utf-8'))
    windows = json.loads((windows_directory/'windows-update.json').read_text(encoding='utf-8'))
    if linux['version'] != windows['version']:
        raise ValueError('Installer versions differ.')
    version = linux['version']
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid version.')
    combined = {'version': version}
    checksums = []
    for directory, manifest, key, filename in (
        (linux_directory, linux, 'linux-amd64', f'screendepresso_{version}_amd64.deb'),
        (windows_directory, windows, 'windows-amd64', f'screendepresso_{version}_windows_amd64_setup.exe'),
    ):
        metadata = manifest[key]
        package = directory/filename
        with package.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        url = f'https://github.com/NadsonJR/ScreenDepresso/releases/download/v{version}/{filename}'
        if metadata['sha256'] != digest or metadata['size'] != package.stat().st_size or metadata['url'] != url:
            raise ValueError('Installer does not match its update manifest.')
        combined[key] = metadata
        checksums.append(f'{digest}  {filename}\n')
    output.mkdir(parents=True, exist_ok=True)
    (output/'update.json').write_text(json.dumps(combined, indent=2)+'\n', encoding='utf-8')
    (output/'SHA256SUMS').write_text(''.join(checksums), encoding='utf-8')
    return combined


if __name__ == '__main__':
    import sys
    merge(*sys.argv[1:])
