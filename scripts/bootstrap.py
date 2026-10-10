#!/usr/bin/env python3
"""Install pinned tool runtimes into the TARGET home; never run skill installers."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from common import command, dump, isolated_env, link, private_path
from restore import load_snapshot

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

def bootstrap(repo, home, apply=False):
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
    report['changed'] = not up_to_date
    report['path_directory'] = str(installed / '.bin')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(bootstrap(args.repo, args.home, args.apply), indent=2))
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        sys.exit(1)
