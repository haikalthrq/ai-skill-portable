"""Build Claude-compatible skills from the published snapshot.

    python3 scripts/claude_port.py                 # writes .work/claude/skills/<name>/
    python3 scripts/claude_port.py --zip           # also writes .work/claude/upload/<name>.zip
    python3 scripts/claude_port.py --out DIR

`skills/` targets Claude Code (copy into ~/.claude/skills). `upload/` holds one zip per
skill with strict frontmatter for claude.ai (Settings > Capabilities > Skills).
Reads only snapshot/manifest.json and snapshot/blobs; never touches a home directory.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile

from common import sha

REPO = Path(__file__).resolve().parents[1]
STRICT_KEYS = ('license', 'compatibility', 'allowed-tools')
CODE_KEYS = ('disable-model-invocation', 'argument-hint')  # Claude Code only
DROP_FILES = {'agents/openai.yaml'}  # Codex UI metadata
PLATFORM = re.compile(r'codex|opencode|antigravity|gemini|spawn_agent|apply_patch|update_plan|'
                      r'request_user_input|\$ponytail:|active-skill-base|~/\.agents/', re.I)
NOTE = """> **Running in Claude.** This skill was ported from a Codex / OpenCode / Antigravity setup. When the text below names another platform's tools, use the Claude equivalent:
> subagent, `spawn_agent`, OpenCode `general` → the **Agent** tool · `apply_patch` → **Edit/Write** · `update_plan`, todo lists → the task list · asking the user (`request_user_input`) → **AskUserQuestion** · "native browser" → Claude in Chrome or the built-in browser · image generation → not available in Claude: say so instead of faking an image.
> `<active-skill-base>` and paths under `~/.agents/skills`, `~/.opencode/skills` or `~/.config/opencode/skills` mean this skill's own folder. Ignore Codex-, Gemini- or OpenCode-only setup (profiles, `~/.codex/config.toml`, `$plugin:skill` syntax); in Claude a skill is invoked as `/skill-name`.
"""
TEXT = [(r'~/\.opencode/skills/', '~/.claude/skills/'), (r'~/\.agents/skills/', '~/.claude/skills/'),
        (r'~/\.config/opencode/skills/', '~/.claude/skills/'),
        (r"OpenCode's built-in `general` subagent", "Claude's Agent tool (general-purpose subagent)"),
        (r'^## OpenCode scope and compatibility$', '## Scope and compatibility'),
        (r'^## OpenCode authorization$', '## Authorization'), (r'^## OpenCode evidence scope$', '## Evidence scope'),
        (r'^## OpenCode scope$', '## Scope'), (r'\(OpenCode unprefixed dependency\)', '(companion skill in this pack)')]
DESC = [(r'native Antigravity/Codex tools take precedence',
         "Claude's native browser tools (Claude in Chrome, built-in browser) take precedence"),
        (r'between Claude, Codex, Hermes, Cursor, OpenCode, and other agents', 'between Claude and other coding agents')]


def description(text):
    text = ' '.join(str(text).split())
    for old, new in DESC:
        text = re.sub(old, new, text)
    text = re.sub(r'<([^<>]{1,40})>', r'\1', text).replace('<', '').replace('>', '')
    return text if len(text) <= 1024 else text[:1020].rsplit(' ', 1)[0] + ' ...'


def scalar(raw):
    """Value of a one-line YAML scalar as used in these skills (plain, 'single' or "double" quoted)."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return json.loads(raw)
    return {'true': True, 'false': False}.get(raw.lower(), raw)


def value(lines):
    """Value of one top-level key: scalar, block scalar, list or one-level map."""
    head = lines[0].split(':', 1)[1].strip()
    rest = [line.strip() for line in lines[1:] if line.strip()]
    if head in {'>', '>-', '>+'}:
        return ' '.join(rest)
    if head in {'|', '|-', '|+'}:
        return '\n'.join(rest)
    if head:
        return scalar(head)
    if rest and all(line.startswith('- ') for line in rest):
        return [scalar(line[2:]) for line in rest]
    return {k.strip(): scalar(v) for k, v in (line.split(':', 1) for line in rest)}


def parse(fields):
    """Top-level frontmatter keys in order; continuation lines belong to the preceding key."""
    blocks = {}
    for line in fields.splitlines():
        if line and not line[0].isspace() and not line.startswith('#'):
            blocks[line.split(':', 1)[0].strip()] = [line]
        elif blocks and line.strip():
            blocks[next(reversed(blocks))].append(line)
    return {key: value(lines) for key, lines in blocks.items()}


def frontmatter(meta, strict):
    quote = lambda v: json.dumps(v if isinstance(v, (str, bool, int)) else
                                 ', '.join(map(str, v)) if isinstance(v, list) else json.dumps(v), ensure_ascii=False)
    out = ['name: ' + quote(str(meta['name']).strip()), 'description: ' + quote(description(meta['description']))]
    out += [key + ': ' + quote(meta[key]) for key in STRICT_KEYS if key in meta]
    extra = dict(meta.get('metadata') or {})
    extra.update({k: meta[k] for k in ('version', 'tags', 'requirements') if k in meta})
    for key in CODE_KEYS:
        if key in meta:
            if strict:
                extra[key] = meta[key]
            else:
                out.append(key + ': ' + quote(meta[key]))
    extra['ported-from'] = 'ai-skill-portable'
    out.append('metadata:')
    out += ['  ' + key + ': ' + quote(item if isinstance(item, str) else
                                      ', '.join(map(str, item)) if isinstance(item, list) else json.dumps(item))
            for key, item in extra.items()]
    return '---\n' + '\n'.join(out) + '\n---\n'


def skill_files(manifest, blobs):
    """Map skill name -> {relative path: bytes}, one canonical copy per non-builtin skill."""
    by_path = {f['path']: f for f in manifest['files']}
    skills = {}
    for definition in manifest['definitions']:
        if definition['alias'] or definition['name'] in skills:
            continue
        root = definition['canonical'].rsplit('/', 1)[0] + '/'
        files = {}
        for path, record in by_path.items():
            if path.startswith(root) and path[len(root):] not in DROP_FILES:
                data = (blobs / record['blob']).read_bytes()
                if sha(data) != record['sha256']:
                    raise ValueError('Corrupt snapshot blob: ' + path)
                files[path[len(root):]] = data
        if 'SKILL.md' in files:
            skills[definition['name']] = files
    return skills


def convert(files, strict):
    out, platform_text = {}, False
    for rel, data in files.items():
        if rel.endswith('.md'):
            # Normalize to LF for the Claude copy only; snapshot blobs keep their original bytes.
            text = data.decode('utf-8-sig').replace('\r\n', '\n')
            for old, new in TEXT:
                text = re.sub(old, new, text, flags=re.M)
            platform_text = platform_text or bool(PLATFORM.search(text))
            data = text.encode('utf-8')
        out[rel] = data
    text = out['SKILL.md'].decode('utf-8')
    match = re.match(r'^---\n(.*?)\n---\n?', text, re.S)
    body = text[match.end():]
    if platform_text:
        body = '\n' + NOTE + ('' if body.startswith('\n') else '\n') + body
    out['SKILL.md'] = (frontmatter(parse(match.group(1)), strict) + body).encode('utf-8')
    return out


def write_tree(directory, files):
    for rel, data in files.items():
        target = directory / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', type=Path, default=REPO)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--zip', action='store_true', help='also build strict per-skill zips for claude.ai')
    args = parser.parse_args(argv)
    out = (args.out or args.repo / '.work/claude').resolve()
    manifest = json.loads((args.repo / 'snapshot/manifest.json').read_text(encoding='utf-8'))
    skills = skill_files(manifest, args.repo / 'snapshot/blobs')
    for sub in ('skills', 'upload'):
        shutil.rmtree(out / sub, ignore_errors=True)
    report = {}
    for name, files in sorted(skills.items()):
        code = convert(files, strict=False)
        write_tree(out / 'skills' / name, code)
        if args.zip:
            (out / 'upload').mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(out / 'upload' / (name + '.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
                for rel, data in sorted(convert(files, strict=True).items()):
                    archive.writestr(name + '/' + rel, data)
        report[name] = {'files': len(code), 'claude_note': NOTE.encode() in code['SKILL.md']}
    json.dump({'snapshot_id': manifest['snapshot_id'], 'skills': report}, sys.stdout, indent=2)
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
