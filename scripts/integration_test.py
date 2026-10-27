#!/usr/bin/env python3
"""Complete real-snapshot restore in a disposable HOME, with optional native discovery."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile

from common import command, dump, isolated_env, sha, test_temp_root
from restore import restore, rollback, load_snapshot
from verify import verify

def integration(repo, native=False, tools=False):
    report = {'platform': platform.system(), 'python': platform.python_version(),
        'snapshot_id': load_snapshot(repo)[0]['snapshot_id'], 'checks': {}, 'ok': False}
    with tempfile.TemporaryDirectory(prefix='opencode-portable-', dir=test_temp_root()) as temp:
        home = Path(temp).resolve() / 'isolated HOME with spaces'
        home.mkdir()
        preview = restore(repo, home)
        assert preview['ok'] and preview['changes'] > 0
        assert preview == restore(repo, home)
        assert list(home.iterdir()) == []
        report['checks']['two_read_only_previews'] = True
        applied = restore(repo, home, apply=True)
        assert applied['ok']
        initial = verify(repo, home)
        assert initial['ok'], initial
        report['restore'] = {key: initial[key] for key in ['files', 'aliases', 'expected_skills', 'unique_blobs', 'broken_local_links']}
        assert restore(repo, home, apply=True)['changes'] == 0
        report['checks']['idempotent_apply'] = True
        env = isolated_env(home)
        search = home / '.opencode/skills/ui-ux-pro-max/scripts/search.py'
        result = json.loads(command([sys.executable, '-B', str(search), 'fintech professional', '--domain', 'typography', '--json'], env=env, timeout=60).stdout)
        assert result['count'] > 0 and any('IBM Plex' in json.dumps(row) for row in result['results'])
        report['checks']['real_dataset_search'] = True
        workspace = home / 'memory-workspace'
        workspace.mkdir()
        command(['git', 'init', '--quiet', str(workspace)], env=env)
        memory = home / '.local/share/opencode-portable/ecc-runtime/scripts/memory.js'
        saved = json.loads(command(['node', str(memory), 'save', '--title', 'Isolated restore verification',
            '--scope', 'project', '--kind', 'note', '--source-harness', 'opencode', '--target', 'opencode',
            '--stdin', '--json'], input='Synthetic integration test data only.', cwd=workspace, env=env, timeout=60).stdout)
        record_id = saved['memory']['id']
        read = json.loads(command(['node', str(memory), 'read', record_id, '--scope', 'project', '--json'], cwd=workspace, env=env, timeout=60).stdout)
        assert read['memory']['body'] == 'Synthetic integration test data only.'
        doctor = json.loads(command(['node', str(memory), 'doctor', '--scope', 'project', '--json'], cwd=workspace, env=env, timeout=60).stdout)
        assert doctor['ok']
        report['checks']['vendored_ecc_save_read_doctor'] = True
        adapter = home / '.agents/skills/cross-harness-handoff/scripts/memory-mcp.mjs'
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'portable-test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'memory_search', 'arguments': {'workspaceRoot': str(workspace), 'scopes': ['project'], 'query': 'restore'}}}]
        responses = command(['node', str(adapter)], input=''.join(json.dumps(m) + '\n' for m in messages), cwd=workspace, env=env, timeout=60)
        events = {r['id']: r for r in map(json.loads, responses.stdout.splitlines())}
        assert 'result' in events[2], events[2]
        tools = events[2]['result']['tools']
        assert len(tools) == 4 and all('workspaceRoot' in t['inputSchema']['properties'] for t in tools)
        assert not events[3]['result'].get('isError')
        report['checks']['restored_custom_mcp_adapter'] = True
        helper = home / '.agents/skills/cross-harness-handoff/scripts/workflow.mjs'
        resumed = json.loads(command(['node', str(helper), 'mode=resume', 'source=opencode', '--repo', str(workspace)], env=env, timeout=60).stdout)
        assert resumed['mode'] == 'resume' and resumed['candidates'] == []
        report['checks']['restored_handoff_helper'] = True
        if native:
            from bootstrap import bootstrap, install_plugin_dependencies
            if tools:
                installed = bootstrap(repo, home, apply=True)
                assert installed['ok']
                repeated = bootstrap(repo, home, apply=True)
                assert repeated['changed'] is False and repeated.get('mcp_changed', False) is False
                runtime_env = isolated_env(home)
                report['runtime_versions'] = {name: command([name, '--version'], env=runtime_env, timeout=60).stdout.strip()
                    for name in ['opencode', 'agent-browser', 'uipro']}
                assert report['runtime_versions']['opencode'] == '1.18.35'
                assert '0.38.2' in report['runtime_versions']['agent-browser']
                assert '2.15.0' in report['runtime_versions']['uipro']
                runner = command([sys.executable, str(repo / 'scripts/portable.py'), 'run',
                    '--home', str(home), '--', '--version'], env=runtime_env, timeout=60).stdout.strip()
                assert runner == report['runtime_versions']['opencode']
                report['checks']['isolated_portable_runner'] = True
                report['checks']['pinned_runtime_bootstrap_idempotence'] = True
            else:
                install_plugin_dependencies(home)
            assert verify(repo, home)['ok']
            runtime = verify(repo, home, native=True)
            assert runtime['ok'], runtime
            report['native'] = {k: v for k, v in runtime.items() if k.startswith('native_')}
            report['checks']['fresh_native_discovery_and_bodies'] = True
            if tools:
                orchestrated = json.loads(command([sys.executable, str(repo / 'scripts/portable.py'),
                    'migrate', '--home', str(home), '--apply'], env=isolated_env(home), timeout=600).stdout)
                assert orchestrated['ok'] and orchestrated['changes'] == 0
                report['checks']['one_command_migration'] = True
                if shutil.which('codex'):
                    report['codex'] = json.loads(command([sys.executable,
                        str(repo / 'scripts/codex_verify.py'), '--home', str(home)],
                        env=runtime_env, timeout=300).stdout)
                    assert report['codex']['ok'], report['codex']
                    report['checks']['codex_profile_skills_and_mcp_discovery'] = True
                else:
                    report['codex'] = {'checked': False, 'reason': 'Codex CLI is not installed on this host'}
                from backup import capture
                captured_repo = Path(temp) / 'recaptured-repo'
                captured_repo.mkdir()
                recaptured = capture(home, captured_repo)
                assert recaptured['skills'] == runtime['native_discovery_count']
                assert capture(home, captured_repo)['changed'] is False
                report['checks']['restored_environment_can_be_backed_up_idempotently'] = True
        planned_rollback = rollback(home, applied['transaction'])
        assert planned_rollback['ok'], planned_rollback
        undone = rollback(home, applied['transaction'], apply=True)
        assert undone['ok'] and undone['changes'] == applied['changes']
        assert not (home / '.config/opencode/AGENTS.md').exists()
        assert rollback(home, applied['transaction'], apply=True)['changes'] == 0
        report['checks']['full_snapshot_rollback_idempotence'] = True
    source = repo / '.work/source-hashes.json'
    if source.exists():
        originals = json.loads(source.read_text())
        assert all(Path(path).is_file() and sha(Path(path).read_bytes()) == digest for path, digest in originals.items()), 'Source environment changed'
        report['checks']['original_source_files_unchanged'] = len(originals)
    report['ok'] = True
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--bootstrap', action='store_true', help='Also test all pinned runtime installations in the disposable home')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = integration(args.repo.resolve(), args.native, args.bootstrap)
    if args.report:
        dump(args.report, result)
    print(json.dumps(result, indent=2))
