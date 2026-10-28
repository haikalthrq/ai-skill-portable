"""Build and check physical Antigravity skill trees from the captured core skills."""
import re
import json
import os
from pathlib import Path

from common import link, private_path, sha, render

ROOT = '.gemini/config/skills'
DEPRECATED = {'caveman', 'officecli'}

def scalar(value):
    """Read the required YAML string fields; reject unsupported or ambiguous values."""
    value = value.strip()
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, str) and decoded.strip() else None
        except ValueError:
            return None
    if value.startswith("'"):
        if len(value) < 3 or not value.endswith("'") or "'" in value[1:-1].replace("''", ''):
            return None
        return value[1:-1].replace("''", "'") if value[1:-1].strip() else None
    value = re.split(r'[ \t]+#', value, maxsplit=1)[0].strip()
    if not value or value[0] in '[{#&*!>|' or ': ' in value or value.lower() in {'null', '~', 'true', 'false', 'yes', 'no', 'on', 'off', '.nan', '.inf', '-.inf', '+.inf'}:
        return None
    try:
        float(value.replace('_', ''))
        return None
    except ValueError:
        if re.fullmatch(r'[-+]?0[xob][0-9a-fA-F_]+', value) or re.match(r'^\d{4}-\d{2}-\d{2}(?:$|[Tt ])', value):
            return None
        return value


def frontmatter(text, expected):
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)', text, re.S)
    if not match or not text[match.end():].strip():
        return False
    fields = match.group(1)
    for line in fields.splitlines():
        if line and not line[0].isspace() and not line.startswith('#') and not re.match(r'^[A-Za-z_][A-Za-z0-9_-]*[ \t]*:(?:[ \t]|$)', line):
            return False
    if len(re.findall(r'^name[ \t]*:', fields, re.M)) != 1 or len(re.findall(r'^description[ \t]*:', fields, re.M)) != 1:
        return False
    name = re.search(r'^name:[ \t]*([^\r\n]+)', fields, re.M)
    description = re.search(r'^description:[ \t]*([^\r\n]*)', fields, re.M)
    if not name or scalar(name.group(1)) != expected or not description:
        return False
    if description.group(1).strip() in {'>', '|', '>-', '|-', '>+', '|+'}:
        block = re.split(r'\n\S', fields[description.end():], maxsplit=1)[0]
        return bool(re.search(r'^[ \t]+\S', block, re.M))
    return scalar(description.group(1)) is not None


def require_physical_tree(home, folder):
    try:
        private_path(home, folder)
    except ValueError as error:
        raise ValueError('Antigravity target is redirected or invalid: ' + folder.relative_to(home).as_posix()) from error
    if not folder.exists():
        return

    def unreadable(error):
        raise ValueError('Unable to inspect Antigravity skill tree') from error

    for directory, directories, filenames in os.walk(folder, followlinks=False, onerror=unreadable):
        for name in directories + filenames:
            if link(Path(directory) / name):
                raise ValueError('Antigravity skill tree contains a symlink or reparse point: ' +
                                 (Path(directory) / name).relative_to(home).as_posix())


def materialize_snapshot(files, blobs, definitions, aliases):
    """Expand core sources into file records, so the normal restore journal owns every byte."""
    sources = {}
    for definition in definitions:
        path = definition['path']
        name = definition['name']
        if name in DEPRECATED or name == 'graphify' or name.startswith('ponytail'):
            continue
        if path.startswith(('.agents/skills/', '.config/opencode/skills/', '.opencode/skills/')):
            sources.setdefault(name, definition['canonical'].rsplit('/', 1)[0])
    for name, source in sorted(sources.items()):
        destination = ROOT + '/' + name
        # Retain an installed Antigravity variant when one exists; expand aliases otherwise.
        if destination + '/SKILL.md' not in files:
            records = [record for path, record in files.items() if path.startswith(source + '/')]
            for record in records:
                path = destination + record['path'][len(source):]
                files[path] = {**record, 'path': path,
                               'transforms': sorted(set(record['transforms']) | {'antigravity-physical-copy'})}
        aliases.pop(destination, None)
    # Remove legacy aliases and superseded definitions from this root.
    definitions[:] = [d for d in definitions if not d['path'].startswith(ROOT + '/')]
    for name in sorted(sources):
        path = ROOT + '/' + name + '/SKILL.md'
        record = files[path]
        if not frontmatter((blobs / record['blob']).read_text(encoding='utf-8-sig'), name):
            raise ValueError('Invalid Antigravity skill frontmatter: ' + name)
        definitions.append({'name': name, 'path': path, 'canonical': path, 'alias': False})
    unexpected = {p.split('/')[3] for p in files if p.startswith(ROOT + '/')} - sources.keys()
    if unexpected:
        raise ValueError('Unmapped Antigravity skills: ' + ', '.join(sorted(unexpected)))
    return {'root': ROOT, 'skills': sorted(sources), 'expected_skills': len(sources),
            'deployment': 'physical-files', 'native_routing_tested': False}


def verify_antigravity(manifest, home, data):
    metadata = manifest.get('antigravity')
    if not metadata:
        return {'ok': False, 'errors': ['Snapshot has no Antigravity target']}
    errors = []
    try:
        private_path(home, home / ROOT)
    except ValueError:
        return {'ok': False, 'errors': ['Antigravity skill root is redirected or invalid']}
    for name in metadata['skills']:
        folder = home / ROOT / name
        try:
            require_physical_tree(home, folder)
            if not folder.is_dir():
                raise ValueError('missing skill directory')
            skill = folder / 'SKILL.md'
            if not skill.is_file() or not frontmatter(skill.read_text(encoding='utf-8-sig'), name):
                raise ValueError('invalid or missing SKILL.md')
            for relative, payload in data.items():
                if relative.startswith(ROOT + '/' + name + '/'):
                    path = home / relative
                    if not path.is_file() or sha(path.read_bytes()) != sha(render(payload, home, relative)):
                        raise ValueError('skill files differ from the snapshot')
        except (OSError, ValueError):
            errors.append(name + ': missing, modified or non-physical skill tree')
    return {'ok': not errors, 'expected_skills': metadata['expected_skills'],
            'physical_skills_verified': metadata['expected_skills'] - len(errors),
            'errors': errors, 'native_routing_tested': False}
