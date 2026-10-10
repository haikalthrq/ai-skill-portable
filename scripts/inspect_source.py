"""Read-only, value-redacted inventory of the installed environment."""
import json
import os
from pathlib import Path
import subprocess

home = Path.home()
repo = Path(__file__).resolve().parents[1]
roots = ['.agents/skills', '.claude/skills', '.config/opencode/skills', '.opencode/skills',
         '.codex/skills', '.gemini/skills', '.gemini/config/skills', '.config/omp/skills']
report = {'roots': {}, 'configs': {}, 'packages': {}, 'tools': {}}
for relative in roots:
    root = home / relative
    entries = []
    if root.exists():
        for p in sorted(root.iterdir()):
            if not (p / 'SKILL.md').is_file():
                continue
            target = p.resolve()
            try:
                logical = target.relative_to(home).as_posix()
            except ValueError:
                logical = 'OUTSIDE_HOME:' + target.name
            files = [f for f in target.rglob('*') if f.is_file() and 'node_modules' not in f.parts and '.git' not in f.parts]
            entries.append({'name': p.name, 'link': p.is_symlink() or p.is_junction(), 'target': logical,
                            'files': len(files), 'bytes': sum(f.stat().st_size for f in files)})
    report['roots'][relative] = entries
for relative in ['.config/opencode/opencode.jsonc', '.opencode/opencode.json']:
    path = home / relative
    text = path.read_text(encoding='utf-8')
    # Current installed files contain ordinary JSON despite their JSONC extension.
    config = json.loads(text)
    report['configs'][relative] = {'keys': list(config), 'plugins': config.get('plugin', []),
        'skill_paths': config.get('skills', {}).get('paths', []),
        'providers': {k: {'keys': list(v), 'option_keys': list(v.get('options', {})), 'models': list(v.get('models', {}))}
                      for k, v in config.get('provider', {}).items()},
        'mcp': {k: {'type': v.get('type'), 'enabled': v.get('enabled'), 'header_names': list(v.get('headers', {})),
                       'environment_names': list(v.get('environment', {}))} for k, v in config.get('mcp', {}).items()}}
for name in ['opencode-ai', 'ecc-universal', 'agent-browser', 'ui-ux-pro-max-cli']:
    root = home / 'AppData/Roaming/npm/node_modules' / name
    path = root / 'package.json'
    if path.exists():
        package = json.loads(path.read_text())
        report['packages'][name] = {'version': package['version'], 'dependencies': package.get('dependencies', {}),
                                   'optionalDependencies': package.get('optionalDependencies', {})}
for command in [['opencode', '--version'], ['node', '--version'], ['python', '--version'], ['dcg', '--version'],
                ['graphify', '--version'], ['officecli', '--version']]:
    try:
        p = subprocess.run(command, shell=os.name == 'nt', capture_output=True, text=True, encoding='utf-8', timeout=30)
        report['tools'][command[0]] = (p.stdout + p.stderr).strip()[:200]
    except (OSError, subprocess.TimeoutExpired):
        report['tools'][command[0]] = 'unavailable'
work = repo / '.work'
work.mkdir(exist_ok=True)
(work / 'source-inventory.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
