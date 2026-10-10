"""Verify payloads, restored references, source immutability and native discovery."""
import json
import os
from pathlib import Path
import re
import urllib.parse
import tempfile

from common import command, isolated_env, link, render, sha, native_catalog, test_temp_root
from restore import load_snapshot, plan_restore

def verify(repo, home=None, native=False):
    manifest, data = load_snapshot(repo)
    report = {'ok': True, 'snapshot_id': manifest['snapshot_id'], 'files': len(data),
        'aliases': len(manifest['aliases']), 'expected_skills': manifest['expected_discovery_count'],
        'unique_blobs': len({r['blob'] for r in manifest['files']}), 'errors': []}
    if home is None:
        return report
    home = home.resolve()
    _, changes, conflicts = plan_restore(repo, home)
    if changes or conflicts:
        report['errors'].append({'restored_drift': [c['path'] for c in changes], 'conflicts': conflicts})
    for record in manifest['definitions']:
        path = home / record['path']
        if not path.is_file():
            report['errors'].append({'missing_definition': record['path']})
    # All Markdown links that were local and resolvable in the captured installation.
    broken = []
    for relative, payload in data.items():
        if not relative.endswith('.md'):
            continue
        text = re.sub(r'```[\s\S]*?```', '', render(payload, home, relative).decode('utf-8'))
        for target in re.findall(r'\]\(([^)\n]+)\)', text):
            target = target.split('#', 1)[0]
            if not target or target.startswith(('http:', 'https:', 'mailto:')) or any(c in target for c in '<>*'):
                continue
            if target.startswith('file:'):
                parsed = urllib.parse.urlparse(target)
                filename = urllib.parse.unquote(parsed.path)
                if os.name == 'nt':
                    filename = filename.lstrip('/')
                destination = Path(filename)
            else:
                destination = (home / relative).parent / urllib.parse.unquote(target)
            if not destination.exists():
                broken.append({'file': relative, 'link': target.replace(home.as_posix(), '$HOME')})
    report['broken_local_links'] = [b for b in broken if not b['file'].startswith('.local/share/opencode-portable/ecc-runtime/') and '/Projects/RINGKAS/' not in b['link']]
    report['optional_external_or_package_doc_links'] = [b for b in broken if b not in report['broken_local_links']]
    # Existing platform/project-only links are listed; new corruption is a hash failure.
    report['ok'] = not report['errors'] and not report['broken_local_links']
    if native:
        env = isolated_env(home)
        with tempfile.TemporaryDirectory(prefix='portable-native-verify-', dir=test_temp_root()) as temp:
            fixture = Path(temp)
            command(['git', 'init', '--quiet', str(fixture)], env=env, timeout=30)
            catalog = native_catalog(cwd=fixture, env=env, timeout=120)
        expected = {s['name']: s for s in manifest['skills']}
        actual = {s['name']: s for s in catalog}
        report['native_discovery_count'] = len(actual)
        report['native_names_match'] = set(expected) == set(actual)
        report['native_descriptions_match'] = all(expected[name]['description'] == item['description'] for name, item in actual.items() if name in expected)
        report['native_all_bodies_loaded'] = all(isinstance(item.get('content'), str) and item['content'].strip() for item in catalog)
        bodies_match = True
        for item in catalog:
            if item['location'] == '<built-in>':
                continue
            relative = Path(item['location']).resolve().relative_to(home).as_posix()
            captured = render(data[relative], home, relative).decode('utf-8')
            body = re.sub(r'^---\r?\n[\s\S]*?\r?\n---\r?\n', '', captured, count=1)
            bodies_match = bodies_match and body.replace('\r\n', '\n').strip() == item['content'].replace('\r\n', '\n').strip()
        report['native_bodies_match_snapshot'] = bodies_match
        # Native paths must resolve inside the restored home, not the original profile.
        report['native_paths_isolated'] = all(item['location'] == '<built-in>' or Path(item['location']).resolve().is_relative_to(home) for item in catalog)
        report['ok'] = report['ok'] and all(report[k] for k in ['native_names_match', 'native_descriptions_match', 'native_all_bodies_loaded', 'native_paths_isolated', 'native_bodies_match_snapshot'])
    return report
