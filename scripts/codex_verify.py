"""Check restored Codex discovery without a model call or provider credentials."""
import json
from queue import Queue, Empty
import subprocess
import shutil
from threading import Thread
import time
import tomllib
import argparse
from pathlib import Path

from common import command, isolated_env


def inline_toml(value):
    if isinstance(value, dict):
        return '{' + ', '.join(json.dumps(k) + ' = ' + inline_toml(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ', '.join(inline_toml(v) for v in value) + ']'
    return json.dumps(value)


def verify_codex(home):
    env = isolated_env(home)
    listed = json.loads(command(['codex', '-p', 'portable', 'mcp', 'list', '--json'], env=env, timeout=60).stdout)
    expected_mcp = {'ecc-memory-vault', 'context7', 'playwright'}
    if not expected_mcp <= {server['name'] for server in listed}:
        raise ValueError('Codex portable profile is missing MCP definitions')
    profile = tomllib.loads((home / '.codex/portable.config.toml').read_text())
    # app-server has no --profile flag; use the exact profile MCP values as supported overrides.
    process = subprocess.Popen([shutil.which('codex') or 'codex', 'app-server', '--stdio', '-c',
        'mcp_servers=' + inline_toml(profile['mcp_servers'])],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        cwd=home, env=env)
    responses = Queue()

    def read_responses():
        for line in process.stdout:
            responses.put(line)
        responses.put(None)

    reader = Thread(target=read_responses, daemon=True)
    reader.start()

    def send(value):
        process.stdin.write((json.dumps(value) + '\n').encode())
        process.stdin.flush()

    def request(identifier, method, params):
        send({'id': identifier, 'method': method, 'params': params})
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                line = responses.get(timeout=max(0, deadline - time.monotonic()))
            except Empty:
                break
            if line is None:
                raise ValueError('Codex verification server exited')
            response = json.loads(line)
            if response.get('id') == identifier:
                if 'error' in response:
                    raise ValueError('Codex verification request failed: ' + method)
                return response['result']
        raise ValueError('Codex verification request timed out: ' + method)

    try:
        request(1, 'initialize', {'clientInfo': {'name': 'portable-verify', 'version': '1.0'},
                                'capabilities': {'experimentalApi': True}})
        send({'method': 'initialized', 'params': {}})
        catalog = request(2, 'skills/list', {'cwds': [str(home)], 'forceReload': True})
        skills = catalog['data'][0]['skills']
        errors = catalog['data'][0].get('errors', [])
        expected = {p.parent.name for root in ['.agents/skills', '.codex/skills']
                    for p in (home / root).glob('*/SKILL.md')}
        expected |= {'ponytail:ponytail' + suffix for suffix in ['', '-audit', '-debt', '-gain', '-help', '-review']}
        found = {skill['name'] for skill in skills if skill.get('enabled', True)}
        missing = sorted(expected - found)
        statuses = request(3, 'mcpServerStatus/list', {'limit': 100})
        tools = {server['name']: len(server.get('tools', {})) for server in statuses['data']}
        mcp_ok = all(tools.get(name, 0) > 0 for name in ['ecc-memory-vault', 'context7', 'playwright'])
        return {'ok': not errors and not missing and mcp_ok, 'expected_portable_skills': len(expected),
                'portable_skills_found': len(expected & found), 'missing': missing,
                'loader_error_count': len(errors),
                'cli_profile_validated': True,
                'mcp_tool_counts': {name: tools.get(name, 0) for name in ['ecc-memory-vault', 'context7', 'playwright']},
                'provider_authentication_used': False, 'hook_trust_granted': False}
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        reader.join(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    args = parser.parse_args()
    result = verify_codex(args.home.resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
