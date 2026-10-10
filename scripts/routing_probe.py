#!/usr/bin/env python3
"""Fresh model-driven routing tests; authentication is local, never exported."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from common import command, dump, isolated_env, test_temp_root
from restore import restore
from bootstrap import install_plugin_dependencies
from verify import verify

CASES = {
    'frontend': ('Build a VPS monitoring dashboard.', {'impeccable'}),
    'debugging': ('Investigate an unexplained backend regression in helpers.js using disciplined root-cause debugging.', {'systematic-debugging'}),
    'handoff': ('Prepare a durable cross-harness handoff for this repository to another harness. This is a dry run: inspect and propose the handoff, but do not save memory.', {'cross-harness-handoff', 'unified-memory'}),
    'backend': ('Plan a small backend-only numeric input validation change in helpers.js. This has no UI implications.', set()),
}
FRONTEND = {'impeccable', 'design-taste-frontend', 'ui-ux-pro-max', 'animate', 'emil-design-eng',
            'gpt-taste', 'image-to-code', 'redesign-existing-projects', 'agent-browser'}

def probes(home, model):
    workspace = home / 'routing-probe-workspace'
    workspace.mkdir(exist_ok=True)
    (workspace / 'helpers.js').write_text('export const total = xs => xs.reduce((sum, x) => sum + x, 0);\n')
    (workspace / 'index.html').write_text('<!doctype html><html lang="en"><title>Monitoring</title><main><h1>VPS status</h1></main></html>')
    command(['git', 'init', '--quiet', str(workspace)])
    env = isolated_env(home)
    env['OPENCODE_CONFIG_CONTENT'] = json.dumps({'share': 'disabled', 'mcp': {'context7': {'enabled': False}},
        'permission': {'edit': 'deny', 'task': 'deny', 'question': 'deny', 'skill': 'allow',
            'read': {'*': 'allow', '*auth.json': 'deny'}, 'ecc-memory-vault_memory_save': 'deny',
            'bash': {'*': 'deny', 'git status*': 'allow', 'git diff*': 'allow', 'git log*': 'allow',
                'git rev-parse*': 'allow', 'node *context.mjs*': 'allow'}}})
    def run(name):
        prompt, expected = CASES[name]
        prompt += ' This is a read-only routing/planning test. Use applicable installed guidance, inspect fixture context, then give a short plan. Do not edit files, install tools, launch browsers, read authentication files or make unrelated network calls. Infer demo assumptions.'
        result = command(['opencode', 'run', '--format', 'json', '--model', model,
            '--title', 'Portable restored routing ' + name, prompt], cwd=workspace, env=env, input='', timeout=300)
        skills, sessions, errors = [], set(), []
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get('sessionID'):
                sessions.add(event['sessionID'])
            part = event.get('part', {})
            state = part.get('state', {})
            if event.get('type') == 'tool_use':
                if part.get('tool') == 'skill':
                    skills.append(state.get('input', {}).get('name'))
                if state.get('status') == 'error':
                    errors.append(part.get('tool'))
            elif event.get('type') == 'error':
                errors.append('model/runtime error')
        selected = set(skills)
        passed = expected <= selected and not errors
        if name == 'backend':
            passed = passed and not selected.intersection(FRONTEND)
        return {'scenario': name, 'passed': bool(passed), 'skills': skills,
                'session_count': len(sessions), 'tool_error_names': errors}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, CASES))
    return {'ok': all(r['passed'] for r in results), 'model': model, 'results': results,
            'authentication_exported': False, 'source_skills_modified': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--model', default='openai/gpt-6.1-sol')
    parser.add_argument('--isolated-local-auth', action='store_true', help='For original-device QA only: temporarily borrow provider auth into a private disposable HOME, never snapshot it')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.isolated_local_auth:
        with tempfile.TemporaryDirectory(prefix='portable-routing-', dir=test_temp_root()) as temp:
            target = Path(temp).resolve()
            restore(args.repo, target, apply=True)
            install_plugin_dependencies(target)
            assert verify(args.repo, target, native=True)['ok']
            source_auth = args.home / '.local/share/opencode/auth.json'
            if not source_auth.is_file():
                raise ValueError('Authenticate locally before running model-driven probes')
            destination = target / '.local/share/opencode/auth.json'
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_auth.read_bytes())
            if os.name == 'nt':
                import csv
                identity = command(['whoami.exe', '/user', '/fo', 'csv', '/nh']).stdout.strip()
                sid = next(csv.reader([identity]))[1]
                command(['icacls.exe', str(destination), '/inheritance:r', '/grant:r', '*' + sid + ':F'])
            else:
                destination.chmod(0o600)
            try:
                report = probes(target, args.model)
            finally:
                destination.unlink(missing_ok=True)
                # Remove managed junctions before TemporaryDirectory cleans the sandbox.
                from restore import remove, load_snapshot
                for alias in load_snapshot(args.repo)[0]['aliases']:
                    remove(target / alias['path'])
    else:
        report = probes(args.home.resolve(), args.model)
    if args.report:
        dump(args.report, report)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ok'] else 1)
