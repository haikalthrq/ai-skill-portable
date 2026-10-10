#!/usr/bin/env python3
"""Fetch a pinned independent scanner locally and verify its official checksum."""
import hashlib
from pathlib import Path
import platform
import tarfile
import urllib.request
import zipfile

VERSION = '8.30.1'
repo = Path(__file__).resolve().parents[1]
work = repo / '.work/gitleaks'
work.mkdir(parents=True, exist_ok=True)
windows = platform.system() == 'Windows'
arch = 'arm64' if platform.machine().lower() in {'arm64', 'aarch64'} else 'x64'
name = f'gitleaks_{VERSION}_{"windows" if windows else "linux"}_{arch}.{"zip" if windows else "tar.gz"}'
base = f'https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/'
checksums = urllib.request.urlopen(base + f'gitleaks_{VERSION}_checksums.txt', timeout=60).read().decode()
expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1] == name)
archive = work / name
if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    data = urllib.request.urlopen(base + name, timeout=120).read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError('Official scanner checksum mismatch')
    archive.write_bytes(data)
binary = work / ('gitleaks.exe' if windows else 'gitleaks')
if windows:
    with zipfile.ZipFile(archive) as z:
        binary.write_bytes(z.read('gitleaks.exe'))
else:
    with tarfile.open(archive) as t:
        binary.write_bytes(t.extractfile('gitleaks').read())
    binary.chmod(0o755)
print(binary)
