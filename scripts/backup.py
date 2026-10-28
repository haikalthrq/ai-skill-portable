"""Capture installed bytes into a content-addressed, sanitized snapshot."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import tomllib

from common import (SKILL_ROOTS, TREE_ROOTS, SAFE_FILES, SKIP_DIRS, TOKEN, blocked, command, native_catalog,
                    dump, link, logical, portable_bytes, sanitized_config, sha, strip_jsonc, session_storage, structured_credentials, structured_asset,
                    isolated_env)
from secret_scan import scan_bytes
from antigravity import DEPRECATED, materialize_snapshot

RUNTIME = '.local/share/opencode-portable/ecc-runtime'

def codex_profile(home):
    """Publish only model preferences and the three reviewed MCP definitions."""
    source = home / '.codex/config.toml'
    config = tomllib.loads(source.read_text(encoding='utf-8')) if source.is_file() else {}
    if not {'ecc-memory-vault', 'context7', 'playwright'} <= set(config.get('mcp_servers', {})):
        source = home / '.codex/portable.config.toml'
        config = tomllib.loads(source.read_text(encoding='utf-8'))
    lines, secrets, required = [], [], set()
    for key in ['model', 'model_reasoning_effort']:
        if key in config:
            if not isinstance(config[key], str):
                raise ValueError('Unexpected Codex model preference')
            lines.append(key + ' = ' + json.dumps(config[key]))
    for name in ['ecc-memory-vault', 'context7', 'playwright']:
        server = config.get('mcp_servers', {}).get(name)
        if not isinstance(server, dict):
            raise ValueError('Missing required Codex MCP: ' + name)
        command_path = server.get('command', '')
        if Path(command_path).name not in {'node', 'node.exe'}:
            raise ValueError('Unexpected Codex MCP executable: ' + name)
        args = server.get('args', [])
        expected = {'ecc-memory-vault': '.agents/skills/cross-harness-handoff/scripts/memory-mcp.mjs',
                    'context7': '.local/share/codex-mcp/node_modules/@upstash/context7-mcp/dist/index.js',
                    'playwright': '.local/share/codex-mcp/node_modules/@playwright/mcp/cli.js'}[name]
        if not isinstance(args, list) or not args or not isinstance(args[0], str) or not Path(args[0]).is_absolute() or Path(args[0]).resolve() != (home / expected).resolve():
            raise ValueError('Unexpected Codex MCP entry point: ' + name)
        normalized = [TOKEN + '/' + expected] + args[1:]
        # Reject credentials in arguments before rendering a TOML document.
        sanitized_config({'command': ['node'] + normalized}, secrets)
        lines += ['', '[mcp_servers.' + name + ']', 'command = "node"',
                  'args = ' + json.dumps(normalized)]
        if name == 'context7':
            required.add('CONTEXT7_API_KEY')
            lines.append('env_vars = ["CONTEXT7_API_KEY"]')
        environment = server.get('env', {})
        for key, value in environment.items():
            if key == 'ECC_MEMORY_HARNESS' and name == 'ecc-memory-vault' and value == 'codex':
                continue
            if key != 'CONTEXT7_API_KEY' or name != 'context7' or not isinstance(value, str):
                raise ValueError('Unreviewed Codex MCP environment variable')
            if value:
                secrets.append(value)
        if name == 'ecc-memory-vault':
            lines += ['', '[mcp_servers.ecc-memory-vault.env]', 'ECC_MEMORY_HARNESS = "codex"']
    # Bootstrap installs this local, captured marketplace; no moving upstream HEAD.
    lines += ['', '[marketplaces.ponytail]', 'source_type = "local"',
              'source = "' + TOKEN + '/.local/share/ponytail"',
              '', '[plugins."ponytail@ponytail"]', 'enabled = true']
    text = '\n'.join(lines) + '\n'
    tomllib.loads(text)
    return text.encode(), secrets, required, source

def capture(home, repo):
    home = home.resolve()
    work = repo / '.work'
    work.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='capture-', dir=work))
    blobs = staging / 'blobs'
    blobs.mkdir()
    files, aliases, definitions, excluded, credentials = {}, {}, [], [], []
    source_hashes = {}
    required_env = set()

    def add(source, destination, override=None, extra=()):
        logical(destination)
        if blocked(source):
            excluded.append({'path': destination, 'reason': 'credential-bearing filename'})
            return
        original = source.read_bytes() if source else override
        if source:
            source_hashes[str(source.resolve())] = sha(original)
        data, transforms = portable_bytes(override if override is not None else original, home)
        structured = structured_asset(data, source.suffix if source else '')
        if session_storage(structured):
            raise ValueError('Auth/session storage is not a publishable asset: ' + destination)
        if extra and 'sanitized-config' in extra:
            pass
        elif structured_credentials(structured):
            raise ValueError('Credential-bearing structured asset requires explicit mapping: ' + destination)
        if b'Netscape HTTP Cookie File' in data or re.search(rb'(?m)^(?:#HttpOnly_)?[^\t\r\n]+\t(?:TRUE|FALSE)\t[^\t]+\t(?:TRUE|FALSE)\t\d+\t[^\t]+\t[^\t\r\n]+$', data):
            raise ValueError('Cookie jar is not a publishable asset: ' + destination)
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            if not data.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'RIFF', b'GIF8')):
                raise ValueError('Unclassified binary requires explicit review: ' + destination)
        findings = scan_bytes(data, destination, credentials)
        if findings:
            raise ValueError('Snapshot rejected: ' + json.dumps(findings))
        digest = sha(data)
        target = blobs / digest
        if not target.exists():
            target.write_bytes(data)
        files[destination] = {'path': destination, 'blob': digest, 'sha256': digest,
            'source_sha256': sha(original), 'bytes': len(data),
            'executable': bool(source and source.stat().st_mode & 0o111) or destination.endswith(('.sh', '.py', '.mjs')),
            'transforms': sorted(set(transforms) | set(extra))}

    def tree(source, destination, runtime=False):
        if link(source):
            resolved = source.resolve(strict=True)
            try:
                target = resolved.relative_to(home).as_posix()
            except ValueError:
                raise ValueError('Unapproved external alias: ' + destination) from None
            logical(target + '/SKILL.md')
            if not any(target.startswith(root + '/') for root in SKILL_ROOTS):
                raise ValueError('Alias target is not an approved skill tree: ' + destination)
            aliases[destination] = {'path': destination, 'target': target, 'source_kind': 'junction' if getattr(source, 'is_junction', lambda: False)() else 'symlink'}
            return
        for child in sorted(source.iterdir()):
            relative = destination + '/' + child.name
            if child.is_dir() or link(child):
                if runtime and child.name.lower() in {'test', 'tests', 'fixtures', 'examples', 'benchmarks', '.github', 'docs'}:
                    excluded.append({'path': relative, 'reason': 'non-runtime package tests/examples'})
                elif child.name in SKIP_DIRS and not (runtime and child.name == 'node_modules'):
                    excluded.append({'path': relative, 'reason': 'cache or unrelated dependency tree'})
                else:
                    tree(child, relative, runtime)
            elif child.is_file():
                add(child, relative)
            else:
                raise ValueError('Unsupported filesystem entry: ' + relative)

    # Read Codex secrets before any tree so cross-file detection covers the entire payload.
    profile, codex_secrets, codex_required, codex_source = codex_profile(home)
    credentials.extend(codex_secrets)
    required_env.update(codex_required)

    # Secret values remain in this process only, never in inventory/report files.
    configs = {}
    for relative in ['.config/opencode/opencode.json', '.config/opencode/opencode.jsonc', '.opencode/opencode.json']:
        source = home / relative
        if not source.exists():
            continue
        config = strip_jsonc(source.read_text(encoding='utf-8'))
        def collect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if re.search(r'(api.?key|token|password|secret|authorization|credential)', key, re.I) and isinstance(item, str) and not item.startswith('{env:'):
                        credentials.append(item)
                    collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
        collect(config)
        config, variables = sanitized_config(config, credentials)
        required_env.update(variables)
        if 'plugin' in config:
            plugins = []
            for plugin in config['plugin']:
                if not isinstance(plugin, str):
                    raise ValueError('Plugin tuple requires an explicit migration mapping')
                if plugin.startswith('.'):
                    actual = (source.parent / plugin).resolve(strict=True)
                    relative_plugin = actual.relative_to(home).as_posix()
                    plugins.append('file:///' + TOKEN + '/' + relative_plugin)
                else:
                    plugins.append(plugin)
            config['plugin'] = plugins
        configs[relative] = config

    for root in SKILL_ROOTS:
        source_root = home / root
        if not source_root.exists():
            continue
        if link(source_root):
            raise ValueError('Redirected skill root requires an explicit mapping: ' + root)
        for directory in sorted(source_root.iterdir()):
            if directory.name in DEPRECATED:
                continue
            if (directory / 'SKILL.md').is_file():
                resolved = directory.resolve(strict=True)
                canonical = resolved.relative_to(home).as_posix()
                definitions.append({'name': directory.name, 'path': root + '/' + directory.name + '/SKILL.md',
                    'canonical': canonical + '/SKILL.md', 'alias': link(directory)})
                tree(directory, root + '/' + directory.name)
    for root in TREE_ROOTS:
        if root in SKILL_ROOTS or root == RUNTIME:
            continue
        source = home / root
        if source.is_dir():
            if root == '.local/share/ponytail':
                # Only Codex/OpenCode runtime assets; no upstream tests, other adapters or moving Git marketplace.
                for folder in ['skills', 'hooks', '.opencode', '.codex-plugin']:
                    tree(source / folder, root + '/' + folder)
                for filename in ['LICENSE', 'AGENTS.md', 'package.json', '.claude-plugin/marketplace.json',
                                 'assets/codex-icon.png', 'assets/logo.png']:
                    add(source / filename, root + '/' + filename)
            else:
                tree(source, root)
    for relative in SAFE_FILES:
        source = home / relative
        if not source.is_file() or relative in configs or relative in {'.config/cross-harness-memory/runtime.json', '.codex/portable.config.toml'}:
            continue
        if relative == '.agents/.skill-lock.json':
            metadata = json.loads(source.read_text())
            metadata['skills'] = {k: v for k, v in metadata['skills'].items() if k not in DEPRECATED}
            add(source, relative, (json.dumps(metadata, indent=2) + '\n').encode(), ['retired-skills-removed'])
        else:
            add(source, relative)
    add(codex_source, '.codex/portable.config.toml', profile,
        ['sanitized-config', 'codex-portable-profile', 'portable-mcp-command'])
    # The preserved upstream copy links to this companion relative to references/.
    # Keep both original files intact, and supply its missing companion on restore.
    recipe = home / '.agents/skills/animate/RECIPES.md'
    if recipe.exists() and not (recipe.parent / 'references/RECIPES.md').exists():
        add(recipe, '.agents/skills/animate/references/RECIPES.md', extra=['reference-companion'])

    # Exact installed ECC memory code and its pure-JS Ajv dependency closure.
    runtime_config = json.loads((home / '.config/cross-harness-memory/runtime.json').read_text())
    ecc = Path(runtime_config['runtimeRoot']).resolve(strict=True)
    package = json.loads((ecc / 'package.json').read_text())
    pending = [ecc / 'scripts/memory.js', ecc / 'scripts/memory-mcp.mjs']
    visited = set()
    while pending:
        source = pending.pop()
        if source in visited:
            continue
        if not source.is_relative_to(ecc):
            raise ValueError('ECC module escaped installed package')
        visited.add(source)
        add(source, RUNTIME + '/' + source.relative_to(ecc).as_posix())
        for module in re.findall(r"require\(['\"](\.[^'\"]+)['\"]\)", source.read_text(encoding='utf-8')):
            candidate = (source.parent / module).resolve()
            if not candidate.is_file():
                candidate = candidate.with_suffix('.js')
            if not candidate.is_file():
                raise ValueError('Missing installed ECC module: ' + candidate.name)
            pending.append(candidate)
    add(ecc / 'package.json', RUNTIME + '/package.json')
    if (ecc / 'LICENSE').is_file():
        add(ecc / 'LICENSE', RUNTIME + '/LICENSE')
    packages, pending_names = {}, ['ajv']
    while pending_names:
        name = pending_names.pop()
        if name in packages:
            continue
        source = ecc / 'node_modules' / name
        metadata = json.loads((source / 'package.json').read_text())
        packages[name] = metadata['version']
        tree(source, RUNTIME + '/node_modules/' + name, runtime=True)
        pending_names.extend(metadata.get('dependencies', {}))
    runtime_template = {**runtime_config, 'runtimeRoot': TOKEN + '/' + RUNTIME}
    add(home / '.config/cross-harness-memory/runtime.json', '.config/cross-harness-memory/runtime.json',
        (json.dumps(runtime_template, indent=2) + '\n').encode(), ['vendored-runtime-path'])

    # Consolidate global settings while retaining native configuration/definition files.
    merged = {}
    def merge(a, b):
        for key, value in b.items():
            if isinstance(value, dict) and isinstance(a.get(key), dict):
                merge(a[key], value)
            elif key == 'plugin' and key in a:
                a[key] = list(dict.fromkeys(a[key] + value))
            else:
                a[key] = value
    for config in configs.values():
        merge(merged, config)
    merged['$schema'] = 'https://opencode.ai/config.json'
    paths = [TOKEN + '/' + p for p in SKILL_ROOTS[:4]]
    merged.setdefault('skills', {})['paths'] = sorted(set(merged.get('skills', {}).get('paths', []) + paths))
    if 'ecc-memory-vault' in merged.get('mcp', {}):
        merged['mcp']['ecc-memory-vault']['command'] = ['node', TOKEN + '/.agents/skills/cross-harness-handoff/scripts/memory-mcp.mjs']
    for relative, config in configs.items():
        # One authoritative generated global JSONC avoids competing global config files.
        if relative.startswith('.config/opencode/'):
            continue
        add(home / relative, relative, (json.dumps(config, indent=2) + '\n').encode(), ['sanitized-config', 'portable-plugin-paths'])
    global_source = home / '.config/opencode/opencode.jsonc'
    if not global_source.exists():
        global_source = home / '.config/opencode/opencode.json'
    add(global_source, '.config/opencode/opencode.jsonc', (json.dumps(merged, indent=2) + '\n').encode(),
        ['sanitized-config', 'portable-mcp-command', 'explicit-global-discovery', 'merged-native-plugins'])

    antigravity = materialize_snapshot(files, blobs, definitions, aliases)
    native = [skill for skill in native_catalog(cwd=home, env=isolated_env(home)) if skill['name'] not in DEPRECATED]
    inventory = [{'name': item['name'], 'description': item['description'],
        'builtin': item['location'] == '<built-in>',
        'definition_candidates': sorted(d['path'] for d in definitions if d['name'] == item['name'])}
        for item in sorted(native, key=lambda x: x['name'])]
    for item in inventory:
        if not item['builtin'] and not item['definition_candidates']:
            raise ValueError('Discovered skill outside approved roots: ' + item['name'])
    tool_versions = {}
    npm_root = Path(command(['npm', 'root', '--global']).stdout.strip())
    for name in ['opencode-ai', 'agent-browser', 'ui-ux-pro-max-cli']:
        candidates = [home / '.local/share/opencode-portable/tools/node_modules' / name, npm_root / name]
        root = next((p for p in candidates if (p / 'package.json').is_file()), None)
        if root:
            tool_versions[name] = json.loads((root / 'package.json').read_text())['version']
    tool_versions.setdefault('opencode-ai', command(['opencode', '--version']).stdout.strip())
    tool_versions['ecc-universal'] = package['version']
    manifest = {'schema': 'opencode-portable/v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_platform': os.name, 'opencode_version': command(['opencode', '--version']).stdout.strip(),
        'expected_discovery_count': len(inventory), 'skills': inventory, 'definitions': definitions,
        'aliases': sorted(aliases.values(), key=lambda x: x['path']), 'files': sorted(files.values(), key=lambda x: x['path']),
        'excluded': excluded, 'required_environment': sorted(required_env),
        'dependencies': {'installed_tools': tool_versions, 'vendored_ecc_dependencies': packages,
            'codex_mcp': json.loads((home / '.local/share/codex-mcp/package.json').read_text())['dependencies'],
            'ponytail': json.loads((home / '.local/share/ponytail/package.json').read_text())['version'],
            'plugin_api': '1.17.11', 'python': '>=3.11', 'node': '>=22',
            'optional_tools': {'dcg': '0.6.7', 'graphify': '0.9.5'}},
        'portability_adaptations': ['home prefixes rebased at restore', 'ECC memory code/dependencies vendored without full pack registration',
            'MCP credentials replaced by environment references', 'native plugin paths resolved',
            'Linux DCG PATH delimiter corrected only in restored copy'],
        'authentication': 'Provider and remote MCP credentials/sessions must be created locally; ECC itself uses local harness identity and repository binding.'}
    manifest['codex'] = {'profile': 'portable', 'mcp_servers': ['ecc-memory-vault', 'context7', 'playwright'],
        'expected_portable_skills': len({d['name'] for d in definitions if d['path'].startswith(('.agents/skills/', '.codex/skills/', '.local/share/ponytail/skills/'))}),
        'ponytail_skills': 6, 'hooks_trust': 'Review and trust locally in Codex /hooks; trust decisions are not backed up.'}
    manifest['antigravity'] = antigravity
    manifest['active_core_skills'] = antigravity['expected_skills']
    manifest['definition_paths'] = sorted(d['path'] for d in definitions)
    referenced_blobs = {record['blob'] for record in files.values()}
    for path in blobs.iterdir():
        if path.name not in referenced_blobs:
            path.unlink()
    manifest['observed_prerequisites'] = {'node': command(['node', '--version']).stdout.strip(),
        'python': __import__('platform').python_version(), 'git': command(['git', '--version']).stdout.strip()}
    manifest['optional_project_checkouts'] = {'ringkas': '$HOME/Projects/RINGKAS; project source/data are not included'}
    content = dict(manifest)
    content.pop('created_utc')
    manifest['snapshot_id'] = sha(json.dumps(content, sort_keys=True).encode())
    dump(work / 'source-hashes.json', source_hashes)
    old = repo / 'snapshot/manifest.json'
    if old.exists() and json.loads(old.read_text())['snapshot_id'] == manifest['snapshot_id']:
        shutil.rmtree(staging)
        return {'changed': False, 'snapshot_id': manifest['snapshot_id'], 'files': len(files), 'skills': len(inventory)}
    dump(staging / 'manifest.json', manifest)
    current = repo / 'snapshot'
    previous = work / 'previous-snapshot'
    if previous.exists():
        shutil.rmtree(previous)
    if current.exists():
        current.rename(previous)
    try:
        staging.rename(current)
    except BaseException:
        if previous.exists():
            previous.rename(current)
        raise
    return {'changed': True, 'snapshot_id': manifest['snapshot_id'], 'files': len(files), 'skills': len(inventory),
        'aliases': len(aliases), 'unique_blobs': len(list((current / 'blobs').iterdir())),
        'logical_bytes': sum(f['bytes'] for f in files.values()), 'stored_bytes': sum(p.stat().st_size for p in (current / 'blobs').iterdir())}
