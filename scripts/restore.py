"""Idempotent restore with whole-plan conflict checks and guarded rollback journals."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
import csv
import shutil

from common import blocked, contained, dump, link, logical, private_path, render, sha
from secret_scan import scan_bytes

def load_snapshot(repo):
    root = repo / 'snapshot'
    if link(root) or link(root / 'blobs') or link(root / 'manifest.json'):
        raise ValueError('Snapshot directories/manifest must not be links')
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 'opencode-portable/v1':
        raise ValueError('Unsupported snapshot schema')
    content = {k: v for k, v in manifest.items() if k not in {'created_utc', 'snapshot_id'}}
    if manifest['snapshot_id'] != sha(json.dumps(content, sort_keys=True).encode()):
        raise ValueError('Manifest content identity mismatch')
    paths, data = set(), {}
    for record in manifest['files']:
        relative = logical(record['path'])
        if relative.casefold() in paths or blocked(Path(relative)):
            raise ValueError('Duplicate or denied snapshot path: ' + relative)
        paths.add(relative.casefold())
        digest = record['blob']
        if not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('Invalid content address')
        path = root / 'blobs' / digest
        if link(path) or not path.is_file():
            raise ValueError('Blob is missing or redirected')
        payload = path.read_bytes()
        if len(payload) != record['bytes'] or sha(payload) != digest or record['sha256'] != digest:
            raise ValueError('Snapshot integrity failure: ' + relative)
        if scan_bytes(payload, relative):
            raise ValueError('Credential detected in snapshot: ' + relative)
        data[relative] = payload
    aliases = set()
    for record in manifest['aliases']:
        relative, target = record['path'], record['target']
        logical(relative + '/SKILL.md')
        logical(target + '/SKILL.md')
        if relative.casefold() in aliases or relative.casefold() in paths:
            raise ValueError('Duplicate alias')
        aliases.add(relative.casefold())
        if target + '/SKILL.md' not in data:
            raise ValueError('Alias must point directly to a captured canonical skill')
        if any(p.startswith(relative + '/') for p in data):
            raise ValueError('Alias overlaps physical payload files')
    for path in data:
        if any(parent.as_posix() in data for parent in Path(path).parents if parent.as_posix() != '.'):
            raise ValueError('File/directory prefix collision: ' + path)
    return manifest, data

def state(path):
    if link(path):
        return {'kind': 'alias', 'target': str(path.resolve(strict=False))}
    if not path.exists():
        return {'kind': 'absent'}
    if path.is_file():
        return {'kind': 'file', 'sha256': sha(path.read_bytes()), 'mode': path.stat().st_mode & 0o777}
    return {'kind': 'directory'}

def comparable(value):
    # File mode is stored for rollback but byte identity defines idempotency.
    return {k: v for k, v in value.items() if k != 'mode'}

def rollback_state(value):
    return dict(value)

def state_root(home):
    root = home / '.local/state/opencode-portable'
    current = root
    while current != home:
        if link(current):
            raise ValueError('Restore state directory is redirected')
        current = current.parent
    return root

def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.portable-' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if os.name != 'nt':
            temp.chmod(mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

def make_alias(path, target):
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        # Direct Win32 API: no CMD parsing, expansion, shell quoting or elevation.
        import ctypes
        from ctypes import wintypes
        import struct
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                           wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        control = kernel.DeviceIoControl
        control.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        control.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        normal = str(target.resolve())
        substitute = ('\\??\\UNC\\' + normal[2:] if normal.startswith('\\\\') else '\\??\\' + normal).encode('utf-16-le')
        printable = normal.encode('utf-16-le')
        names = substitute + b'\0\0' + printable + b'\0\0'
        payload = struct.pack('<LHHHHHH', 0xA0000003, len(names) + 8, 0, 0, len(substitute), len(substitute) + 2, len(printable)) + names
        if len(payload) > 16384:
            raise ValueError('Junction target is too long')
        path.mkdir()
        handle = create(str(path), 0x40000000, 7, None, 3, 0x02200000, None)
        try:
            if handle == wintypes.HANDLE(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            buffer = ctypes.create_string_buffer(payload)
            returned = wintypes.DWORD()
            if not control(handle, 0x000900A4, buffer, len(payload), None, 0, ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            if handle != wintypes.HANDLE(-1).value:
                kernel.CloseHandle(handle)
                handle = wintypes.HANDLE(-1).value
            path.rmdir()
            raise
        finally:
            if handle != wintypes.HANDLE(-1).value:
                kernel.CloseHandle(handle)
    else:
        path.symlink_to(os.path.relpath(target, path.parent), target_is_directory=True)

def remove(path):
    if path.is_symlink():
        path.unlink()
    elif link(path) and path.is_dir():
        path.rmdir()
    elif path.is_file():
        path.unlink()
    elif path.exists():
        raise ValueError('Refusing to remove a real directory')

def plan_restore(repo, home, replace=False):
    home = home.absolute()
    if link(home):
        raise ValueError('Target home must be a real directory')
    home = home.resolve()
    manifest, data = load_snapshot(repo)
    changes, conflicts = [], []
    for record in manifest['files']:
        relative = record['path']
        path = contained(home, relative)
        before = state(path)
        payload = render(data[relative], home, relative)
        after = {'kind': 'file', 'sha256': sha(payload)}
        if comparable(before) == after:
            continue
        if before['kind'] not in {'absent', 'file'}:
            conflicts.append(relative + ': redirected file or directory')
        elif before['kind'] != 'absent' and not replace:
            conflicts.append(relative + ': differing existing file')
        mode = 0o755 if record['executable'] else 0o644
        after['mode'] = mode if os.name != 'nt' else 0o666
        changes.append({'path': relative, 'before': before, 'after': after, 'payload': payload, 'mode': mode})
    for record in manifest['aliases']:
        relative = record['path']
        path = contained(home, relative)
        target = contained(home, record['target'])
        before = state(path)
        after = {'kind': 'alias', 'target': str(target)}
        if comparable(before) == after:
            continue
        if before['kind'] == 'directory':
            conflicts.append(relative + ': alias would replace a real directory')
        elif before['kind'] == 'alias' and not Path(before['target']).is_relative_to(home):
            conflicts.append(relative + ': existing alias points outside target home')
        elif before['kind'] != 'absent' and not replace:
            conflicts.append(relative + ': differing existing alias/file')
        changes.append({'path': relative, 'before': before, 'after': after, 'alias_target': record['target']})
    competing = home / '.config/opencode/opencode.json'
    if '.config/opencode/opencode.json' not in data and competing.exists():
        before = state(competing)
        if before['kind'] != 'file' or not replace:
            conflicts.append('.config/opencode/opencode.json: competing global config')
        changes.append({'path': '.config/opencode/opencode.json', 'before': before, 'after': {'kind': 'absent'}})
    state_root(home)
    return manifest, changes, conflicts

def restore(repo, home, apply=False, replace=False):
    if link(home):
        raise ValueError('Target home must be a real directory')
    home = home.resolve()
    manifest, changes, conflicts = plan_restore(repo, home, replace)
    report = {'ok': not conflicts, 'apply': apply, 'changes': len(changes), 'conflicts': conflicts,
        'snapshot_id': manifest['snapshot_id'], 'paths': [c['path'] for c in changes]}
    report['prerequisites'] = {name: bool(shutil.which(name)) for name in ['node', 'npm', 'git']}
    report['missing_runtime_prerequisites'] = [name for name, found in report['prerequisites'].items() if not found]
    report['required_environment'] = manifest.get('required_environment', [])
    report['environment_not_set'] = [name for name in report['required_environment'] if not os.environ.get(name)]
    report['local_authentication'] = manifest.get('authentication', 'Create provider and remote MCP authentication locally')
    report['optional_tools'] = manifest.get('dependencies', {}).get('optional_tools', {})
    if conflicts or not apply or not changes:
        return report
    root = state_root(home)
    transaction = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:12]
    directory = private_path(home, root / 'transactions' / transaction)
    directory.mkdir(parents=True, mode=0o700)
    if os.name == 'nt':
        identity = subprocess.run(['whoami.exe', '/user', '/fo', 'csv', '/nh'], check=True,
                                  capture_output=True, text=True).stdout.strip()
        sid = next(csv.reader([identity]))[1]
        subprocess.run(['icacls.exe', str(directory), '/inheritance:r', '/grant:r',
                        '*' + sid + ':(OI)(CI)F'], check=True, capture_output=True, text=True)
    else:
        directory.chmod(0o700)
    journal = {'schema': 'opencode-portable-transaction/v1', 'id': transaction,
        'home': str(home), 'snapshot_id': manifest['snapshot_id'], 'status': 'prepared', 'changes': []}
    for change in changes:
        record = {k: v for k, v in change.items() if k not in {'payload', 'mode'}}
        path = home / change['path']
        if record['before']['kind'] == 'file':
            digest = record['before']['sha256']
            original_bytes = path.read_bytes()
            if sha(original_bytes) != digest:
                raise ValueError('Destination changed during journal backup: ' + change['path'])
            atomic_write(directory / digest, original_bytes)
            record['backup_blob'] = digest
        journal['changes'].append(record)
    journal_path = directory / 'journal.json'
    atomic_write(journal_path, (json.dumps(journal, indent=2) + '\n').encode())
    try:
        for change in changes:
            # Recheck parents and pre-change state immediately before writing.
            relative = change['path']
            if 'alias_target' in change:
                path = contained(home, relative)
            else:
                path = contained(home, relative)
            if comparable(state(path)) != comparable(change['before']):
                raise ValueError('Destination changed during restore: ' + relative)
            if change['after']['kind'] == 'absent':
                remove(path)
            elif 'alias_target' in change:
                temporary = path.with_name(path.name + '.portable-link-' + uuid.uuid4().hex)
                make_alias(temporary, home / change['alias_target'])
                try:
                    # Journal owns the absent state only while this replacement is in flight.
                    stored = next(r for r in journal['changes'] if r['path'] == relative)
                    stored['owned_intermediate'] = {'kind': 'absent'}
                    atomic_write(journal_path, (json.dumps(journal, indent=2) + '\n').encode())
                    remove(path)
                    os.replace(temporary, path)
                finally:
                    if link(temporary):
                        remove(temporary)
            else:
                atomic_write(path, change['payload'], change['mode'])
        journal['status'] = 'complete'
        atomic_write(journal_path, (json.dumps(journal, indent=2) + '\n').encode())
    except BaseException:
        # The prepared journal can also recover interruption between write and status update.
        rollback(home, transaction, apply=True)
        raise
    report['transaction'] = transaction
    return report

def rollback(home, transaction, apply=False):
    if link(home):
        raise ValueError('Target home must be a real directory')
    home = home.resolve()
    if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{12}', transaction):
        raise ValueError('Invalid transaction ID')
    directory = private_path(home, state_root(home) / 'transactions' / transaction)
    if link(directory) or link(directory / 'journal.json'):
        raise ValueError('Redirected rollback journal')
    journal = json.loads((directory / 'journal.json').read_text())
    if journal.get('schema') != 'opencode-portable-transaction/v1' or journal['home'] != str(home):
        raise ValueError('Rollback journal does not belong to this home')
    pending, conflicts = [], []
    for record in journal['changes']:
        relative = record['path']
        logical(relative if record['after']['kind'] != 'alias' else relative + '/SKILL.md')
        path = home / relative
        contained(home, relative)
        current = rollback_state(state(path))
        if current == rollback_state(record['before']):
            continue
        intermediate = ((journal['status'] == 'prepared' or journal.get('recovering_restore')) and current == record.get('owned_intermediate')) or (journal['status'] == 'rolling_back' and current == record.get('owned_rollback_intermediate'))
        if current != rollback_state(record['after']) and not intermediate:
            conflicts.append(relative)
            continue
        if record['before']['kind'] == 'file':
            if not re.fullmatch('[a-f0-9]{64}', record['backup_blob']):
                raise ValueError('Invalid rollback backup address')
            backup = directory / record['backup_blob']
            if link(backup) or sha(backup.read_bytes()) != record['before']['sha256']:
                raise ValueError('Rollback backup integrity failure')
        elif record['before']['kind'] == 'alias':
            target = Path(record['before']['target'])
            if not target.is_relative_to(home):
                raise ValueError('Rollback alias escapes target home')
            contained(home, target.relative_to(home).as_posix(), follow_leaf=True)
        pending.append(record)
    report = {'ok': not conflicts, 'changes': len(pending), 'conflicts': conflicts, 'apply': apply, 'transaction': transaction}
    if conflicts or not apply:
        return report
    if journal['status'] != 'rolling_back':
        journal['recovering_restore'] = journal['status'] == 'prepared'
    journal['status'] = 'rolling_back'
    atomic_write(directory / 'journal.json', (json.dumps(journal, indent=2) + '\n').encode())
    for record in reversed(pending):
        path = home / record['path']
        # Check parent containment without following the managed alias leaf.
        contained(home, record['path'])
        current = state(path)
        if current == record.get('owned_rollback_intermediate'):
            expected_current = record['owned_rollback_intermediate']
        elif journal.get('recovering_restore') and current == record.get('owned_intermediate'):
            expected_current = record['owned_intermediate']
        else:
            expected_current = record['after']
        if rollback_state(state(path)) != rollback_state(expected_current):
            raise ValueError('Destination changed during rollback: ' + record['path'])
        before = record['before']
        if before['kind'] == 'file':
            old_bytes = (directory / record['backup_blob']).read_bytes()
            if not link(path):
                atomic_write(path, old_bytes, before['mode'])
            else:
                temporary = path.with_name(path.name + '.portable-rollback-' + uuid.uuid4().hex)
                atomic_write(temporary, old_bytes, before['mode'])
                record['owned_rollback_intermediate'] = {'kind': 'absent'}
                atomic_write(directory / 'journal.json', (json.dumps(journal, indent=2) + '\n').encode())
                try:
                    remove(path)
                    os.replace(temporary, path)
                finally:
                    if temporary.exists():
                        remove(temporary)
        elif before['kind'] == 'alias':
            target = Path(before['target'])
            if not target.is_relative_to(home):
                raise ValueError('Rollback alias escapes target home')
            contained(home, target.relative_to(home).as_posix(), follow_leaf=True)
            temporary = path.with_name(path.name + '.portable-rollback-' + uuid.uuid4().hex)
            make_alias(temporary, target)
            record['owned_rollback_intermediate'] = {'kind': 'absent'}
            atomic_write(directory / 'journal.json', (json.dumps(journal, indent=2) + '\n').encode())
            try:
                remove(path)
                os.replace(temporary, path)
            finally:
                if link(temporary):
                    remove(temporary)
        else:
            remove(path)
    journal['status'] = 'rolled_back'
    atomic_write(directory / 'journal.json', (json.dumps(journal, indent=2) + '\n').encode())
    return report
