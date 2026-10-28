#!/usr/bin/env python3
"""Install pinned tool runtimes into the TARGET home; never run skill installers."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess

from common import command, dump, isolated_env, link, private_path
from restore import load_snapshot

MCP_ENTRY_POINTS = {'@playwright/mcp': 'cli.js', '@upstash/context7-mcp': 'dist/index.js'}

def mcp_packages_ready(dependencies, expected, env):
    try:
        for name, version in expected.items():
            root = dependencies / name
            entry = root / MCP_ENTRY_POINTS[name]
            if not entry.is_file() or json.loads((root / 'package.json').read_text())['version'] != version:
                return False
            # Import the CLI to detect an interrupted/missing transitive dependency tree too.
            command(['node', str(entry), '--help'], env=env, timeout=30)
        return True
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return False

def install_plugin_dependencies(home):
    env = isolated_env(home)
    targets = [home / p for p in ['.config/opencode', '.opencode']]
    for target in targets:
        private_path(home, target)
        dependencies = private_path(home, target / 'node_modules')
        if dependencies.exists():
            for path in dependencies.rglob('*'):
                if link(path) and not path.resolve().is_relative_to(home):
                    raise ValueError('Dependency tree redirects outside target home')
    for target in targets:
        if (target / 'package-lock.json').is_file() and not (target / 'node_modules/@opencode-ai/plugin/package.json').is_file():
            command(['npm', 'ci', '--prefix', str(target), '--ignore-scripts', '--no-audit', '--no-fund'],
                    env=env, timeout=300)

def bootstrap(repo, home, apply=False, antigravity=False):
    manifest, _ = load_snapshot(repo)
    versions = manifest['dependencies']['installed_tools']
    if link(home):
        raise ValueError('Target home is redirected')
    home = home.resolve()
    prefix = home / '.local/share/opencode-portable/tools'
    current = prefix
    while current != home:
        if link(current):
            raise ValueError('Tool prefix is redirected')
        current = current.parent
    packages = [f'{name}@{version}' for name, version in sorted(versions.items())]
    import re
    if set(versions) - {'opencode-ai', 'ecc-universal', 'agent-browser', 'ui-ux-pro-max-cli'} or any(not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?', v) for v in versions.values()):
        raise ValueError('Unexpected runtime package or version')
    report = {'ok': True, 'apply': apply, 'packages': packages,
        'prefix': '$HOME/.local/share/opencode-portable/tools',
        'skills_installed_or_updated': 0, 'required_commands': ['node', 'npm', 'git', 'python']}
    if antigravity and not manifest.get('antigravity'):
        raise ValueError('Snapshot has no Antigravity target; recapture it before installation')
    if manifest.get('antigravity'):
        report['antigravity'] = {'deployment': 'physical-files restored by the snapshot journal',
            'expected_skills': manifest['antigravity']['expected_skills']}
    if not apply:
        return report
    from verify import verify
    if not verify(repo, home)['ok']:
        raise ValueError('Restore and verify the snapshot before bootstrapping runtimes')
    for executable in ['node', 'npm', 'git']:
        if not shutil.which(executable):
            raise ValueError('Install prerequisite first: ' + executable)
    env = isolated_env(home)
    prefix.mkdir(parents=True, exist_ok=True)
    installed = prefix / 'node_modules'
    private_path(home, installed)
    if installed.exists():
        for path in installed.rglob('*'):
            if link(path) and not path.resolve().is_relative_to(home):
                raise ValueError('Runtime package tree redirects outside target home')
    up_to_date = all((installed / name / 'package.json').is_file() and
        json.loads((installed / name / 'package.json').read_text())['version'] == version for name, version in versions.items())
    if not up_to_date:
        command(['npm', 'install', '--prefix', str(prefix), '--save-exact', '--ignore-scripts',
                 '--no-audit', '--no-fund'] + packages, env=env, timeout=600)
        # OpenCode's own pinned postinstall chooses/copies its platform binary.
        # All other lifecycle scripts (including ECC lifecycle setup) remain disabled.
    package = json.loads((installed / 'opencode-ai/package.json').read_text())
    binary_path = installed / 'opencode-ai' / package['bin']['opencode']
    if not up_to_date or not binary_path.is_file():
        command(['npm', 'rebuild', '--prefix', str(prefix), 'opencode-ai'], env=env, timeout=180)
    install_plugin_dependencies(home)
    mcp_prefix = private_path(home, home / '.local/share/codex-mcp')
    expected_mcp = manifest['dependencies'].get('codex_mcp', {})
    if expected_mcp:
        if set(expected_mcp) != {'@playwright/mcp', '@upstash/context7-mcp'}:
            raise ValueError('Unexpected Codex MCP runtime package')
        dependencies = private_path(home, mcp_prefix / 'node_modules')
        if dependencies.exists():
            for path in dependencies.rglob('*'):
                if link(path) and not path.resolve().is_relative_to(home):
                    raise ValueError('MCP dependency tree redirects outside target home')
        current_mcp = mcp_packages_ready(dependencies, expected_mcp, env)
        if not current_mcp:
            command(['npm', 'ci', '--prefix', str(mcp_prefix), '--ignore-scripts', '--no-audit', '--no-fund'],
                    env=env, timeout=600)
            if not mcp_packages_ready(dependencies, expected_mcp, env):
                raise ValueError('MCP runtimes did not initialize after installation')
        report['mcp_changed'] = not current_mcp
        report['browser_setup'] = 'Install Chromium with Playwright CLI; Linux browser system libraries require OS package installation.'
    if manifest.get('codex'):
        if shutil.which('codex'):
            # Only this isolated target's Codex config/cache may be changed; never the caller's.
            codex_home = private_path(home, home / '.codex')
            private_path(home, codex_home / 'plugins')
            config_file = codex_home / 'config.toml'
            if link(config_file):
                raise ValueError('Codex configuration is redirected')
            for path in codex_home.rglob('*'):
                if link(path) and not path.resolve().is_relative_to(home):
                    raise ValueError('Codex tree redirects outside target home')
            command(['codex', 'plugin', 'marketplace', 'add', str(home / '.local/share/ponytail')], env=env, timeout=120)
            command(['codex', 'plugin', 'add', 'ponytail@ponytail'], env=env, timeout=120)
            report['codex_plugin_installed'] = True
        else:
            report['codex_plugin_installed'] = False
            report['codex_setup'] = 'Install Codex, then run bootstrap again to register the captured local Ponytail marketplace.'
    report['changed'] = not up_to_date
    report['path_directory'] = str(installed / '.bin')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--antigravity', action='store_true', help='Require physical Antigravity skills in the restored target')
    args = parser.parse_args()
    try:
        print(json.dumps(bootstrap(args.repo, args.home, args.apply, args.antigravity), indent=2))
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        sys.exit(1)
