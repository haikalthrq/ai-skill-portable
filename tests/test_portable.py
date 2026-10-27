import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import dump, sanitized_config, sha, strip_jsonc, test_temp_root, session_storage, structured_credentials, structured_asset
from restore import load_snapshot, make_alias, restore, rollback
from secret_scan import scan_bytes
from backup import codex_profile
from common import isolated_env, portable_bytes, render
from codex_verify import inline_toml
from bootstrap import mcp_packages_ready
import tomllib

def fixture(repo, payload=b'# routing\n'):
    record = {'path': '.config/opencode/AGENTS.md', 'blob': sha(payload), 'sha256': sha(payload),
        'bytes': len(payload), 'source_sha256': sha(payload), 'executable': False, 'transforms': []}
    manifest = {'schema': 'opencode-portable/v1', 'created_utc': 'fixture', 'files': [record],
        'aliases': [], 'definitions': [], 'skills': [], 'expected_discovery_count': 0}
    manifest['snapshot_id'] = sha(json.dumps({k: v for k, v in manifest.items() if k != 'created_utc'}, sort_keys=True).encode())
    dump(repo / 'snapshot/manifest.json', manifest)
    blob = repo / 'snapshot/blobs' / sha(payload)
    blob.parent.mkdir(parents=True, exist_ok=True)
    blob.write_bytes(payload)
    return manifest

def republish(repo, manifest):
    manifest['snapshot_id'] = sha(json.dumps({k: v for k, v in manifest.items() if k not in {'snapshot_id', 'created_utc'}}, sort_keys=True).encode())
    dump(repo / 'snapshot/manifest.json', manifest)

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='portable-test-', dir=test_temp_root())
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.home = self.root / 'isolated home with spaces'
        self.repo.mkdir()
        fixture(self.repo)

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_is_read_only_and_repeatable(self):
        first = restore(self.repo, self.home)
        self.assertEqual(first, restore(self.repo, self.home))
        self.assertFalse(self.home.exists())

    def codex_fixture(self, extra_argument=None):
        self.home.mkdir(exist_ok=True)
        source = self.home / '.codex/config.toml'
        source.parent.mkdir(exist_ok=True)
        entries = {'ecc-memory-vault': '.agents/skills/cross-harness-handoff/scripts/memory-mcp.mjs',
                   'context7': '.local/share/codex-mcp/node_modules/@upstash/context7-mcp/dist/index.js',
                   'playwright': '.local/share/codex-mcp/node_modules/@playwright/mcp/cli.js'}
        lines = ['model = "example-model"', '[projects."private-repo"]', 'trust_level = "trusted"',
                 '[hooks]', 'enabled = true']
        for name, entry in entries.items():
            args = [str(self.home / entry)]
            if extra_argument and name == 'context7':
                args.extend(extra_argument)
            lines += ['[mcp_servers.' + name + ']', 'command = "node"', 'args = ' + json.dumps(args)]
        lines += ['[mcp_servers.context7.env]', 'CONTEXT7_API_KEY = "synthetic-private-value"',
                  '[mcp_servers.ecc-memory-vault.env]', 'ECC_MEMORY_HARNESS = "codex"']
        source.write_text('\n'.join(lines) + '\n')
        return source

    def test_codex_profile_excludes_secret_trust_and_private_paths(self):
        source = self.codex_fixture()
        original = source.read_bytes()
        payload, secrets, required, selected = codex_profile(self.home)
        self.assertEqual(selected, source)
        profile = tomllib.loads(payload.decode())
        self.assertEqual(profile['model'], 'example-model')
        self.assertNotIn('synthetic-private-value', payload.decode())
        self.assertEqual(secrets, ['synthetic-private-value'])
        self.assertEqual(required, {'CONTEXT7_API_KEY'})
        self.assertEqual(profile['mcp_servers']['context7']['env_vars'], ['CONTEXT7_API_KEY'])
        self.assertNotIn('projects', profile)
        self.assertNotIn('hooks', profile)
        self.assertNotIn(str(self.home), payload.decode())
        self.assertEqual(source.read_bytes(), original)

    def test_capture_can_read_restored_codex_profile_without_main_mcp(self):
        source = self.codex_fixture()
        restored_profile = source.with_name('portable.config.toml')
        source.rename(restored_profile)
        source.write_text('model = "unrelated-model"\n')
        payload, _, _, selected = codex_profile(self.home)
        self.assertEqual(selected, restored_profile)
        self.assertEqual(tomllib.loads(payload.decode())['model'], 'example-model')

    def test_codex_profile_rejects_secret_command_arguments(self):
        self.codex_fixture(['--api-key', 'synthetic-private-value'])
        with self.assertRaises(ValueError):
            codex_profile(self.home)

    def test_codex_app_server_override_preserves_nested_toml_values(self):
        value = {'ecc-memory-vault': {'command': 'node', 'args': ['path with spaces', 'quote"here'],
                                     'env': {'ECC_MEMORY_HARNESS': 'codex'}, 'enabled': True}}
        self.assertEqual(tomllib.loads('mcp_servers = ' + inline_toml(value))['mcp_servers'], value)

    def test_disposable_environment_does_not_reuse_caller_codex_or_database(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {'CODEX_HOME': '/caller-private-config'}):
            env = isolated_env(self.home)
        self.assertEqual(env['CODEX_HOME'], str(self.home / '.codex'))
        self.assertEqual(env['XDG_DATA_HOME'], str(self.home / '.local/share/opencode-portable/data'))

    def test_partial_mcp_installation_is_not_reported_ready(self):
        package = self.home / 'node_modules/@playwright/mcp'
        package.mkdir(parents=True)
        (package / 'package.json').write_text('{"version":"0.0.83"}')
        self.assertFalse(mcp_packages_ready(self.home / 'node_modules', {'@playwright/mcp': '0.0.83'}, {}))

    def test_missing_mcp_transitive_dependency_triggers_repair(self):
        from unittest.mock import patch
        import subprocess
        package = self.home / 'node_modules/@playwright/mcp'
        package.mkdir(parents=True)
        (package / 'package.json').write_text('{"version":"0.0.83"}')
        (package / 'cli.js').write_text('// fixture')
        with patch('bootstrap.command', side_effect=subprocess.CalledProcessError(1, ['node'])):
            self.assertFalse(mcp_packages_ready(self.home / 'node_modules', {'@playwright/mcp': '0.0.83'}, {}))

    def test_codex_command_resolves_platform_executable(self):
        from unittest.mock import patch
        from common import command
        with patch('common.shutil.which', return_value='/tools/codex.cmd'), patch('common.subprocess.run') as run:
            command(['codex', 'plugin', 'list'])
        self.assertEqual(run.call_args.args[0][0], '/tools/codex.cmd')

    def test_posix_file_url_capture_renders_valid_windows_file_url(self):
        from pathlib import PureWindowsPath
        source = self.home.as_uri() + '/.local/share/ponytail/.opencode/plugins/ponytail.mjs'
        payload, _ = portable_bytes(source.encode(), self.home)
        self.assertTrue(payload.startswith(b'file:///__PORTABLE_HOME__/'))
        windows = PureWindowsPath('C:/Restored Home')
        expected = windows.as_uri() + '/.local/share/ponytail/.opencode/plugins/ponytail.mjs'
        self.assertEqual(render(payload, windows, '.config/opencode/opencode.jsonc').decode(), expected)
        self.assertEqual(render(payload.replace(b'file:///', b'file://'), windows,
                                '.config/opencode/opencode.jsonc').decode(), expected)

    def test_codex_profile_accepts_portable_slash_paths(self):
        source = self.codex_fixture()
        config = source.read_text()
        source.write_text(config.replace(str(self.home), self.home.as_posix()))
        payload, _, _, _ = codex_profile(self.home)
        self.assertIn(b'__PORTABLE_HOME__/.agents/skills', payload)

    def test_apply_twice_and_rollback_twice(self):
        first = restore(self.repo, self.home, apply=True)
        self.assertTrue(first['ok'])
        self.assertEqual(restore(self.repo, self.home, apply=True)['changes'], 0)
        self.assertTrue(rollback(self.home, first['transaction'], apply=True)['ok'])
        self.assertFalse((self.home / '.config/opencode/AGENTS.md').exists())
        self.assertEqual(rollback(self.home, first['transaction'], apply=True)['changes'], 0)

    def test_conflict_preserves_existing_data(self):
        path = self.home / '.config/opencode/AGENTS.md'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'user work')
        report = restore(self.repo, self.home, apply=True)
        self.assertFalse(report['ok'])
        self.assertEqual(path.read_bytes(), b'user work')
        self.assertFalse((self.home / '.local/state/opencode-portable').exists())

    def test_explicit_replace_keeps_exact_private_rollback(self):
        path = self.home / '.config/opencode/AGENTS.md'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'user work\r\n')
        report = restore(self.repo, self.home, apply=True, replace=True)
        rollback(self.home, report['transaction'], apply=True)
        self.assertEqual(path.read_bytes(), b'user work\r\n')

    def test_rollback_refuses_newer_user_changes(self):
        report = restore(self.repo, self.home, apply=True)
        path = self.home / '.config/opencode/AGENTS.md'
        path.write_bytes(b'newer work')
        result = rollback(self.home, report['transaction'], apply=True)
        self.assertFalse(result['ok'])
        self.assertEqual(path.read_bytes(), b'newer work')

    def test_corrupt_blob_rejected_before_writes(self):
        manifest = json.loads((self.repo / 'snapshot/manifest.json').read_text())
        (self.repo / 'snapshot/blobs' / manifest['files'][0]['blob']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            restore(self.repo, self.home, apply=True)
        self.assertFalse(self.home.exists())

    def test_forged_traversal_rejected(self):
        manifest = json.loads((self.repo / 'snapshot/manifest.json').read_text())
        manifest['files'][0]['path'] = '.config/opencode/../../escape'
        republish(self.repo, manifest)
        with self.assertRaises(ValueError):
            restore(self.repo, self.home, apply=True)
        self.assertFalse(self.home.exists())

    def test_redirected_parent_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.home.mkdir()
        make_alias(self.home / '.config', outside)
        with self.assertRaises(ValueError):
            restore(self.repo, self.home, apply=True)
        self.assertEqual(list(outside.iterdir()), [])
        from restore import remove
        remove(self.home / '.config')

    def test_redirected_transaction_state_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        state = self.home / '.local/state/opencode-portable'
        state.mkdir(parents=True)
        make_alias(state / 'transactions', outside)
        with self.assertRaises(ValueError):
            restore(self.repo, self.home, apply=True)
        self.assertEqual(list(outside.iterdir()), [])
        from restore import remove
        remove(state / 'transactions')

    def test_config_sanitization_does_not_publish_secret(self):
        secret = 'ctx7' + 'sk-' + '12345678-1234-1234-1234-123456789012'
        config, env = sanitized_config({'mcp': {'context7': {'headers': {'CONTEXT7_API_KEY': secret}}}})
        self.assertNotIn(secret, json.dumps(config))
        self.assertEqual(env, ['CONTEXT7_API_KEY'])
        self.assertTrue(scan_bytes(secret.encode(), 'fixture'))

    def test_jsonc_preserves_url_and_comment_like_strings(self):
        self.assertEqual(strip_jsonc('{"url":"https://example.test/a//b", /* note */ "value":"/*text*/",}'),
                         {'url': 'https://example.test/a//b', 'value': '/*text*/'})

    def test_manifest_duplicate_destination_rejected(self):
        manifest = json.loads((self.repo / 'snapshot/manifest.json').read_text())
        manifest['files'].append(dict(manifest['files'][0]))
        republish(self.repo, manifest)
        with self.assertRaises(ValueError):
            load_snapshot(self.repo)

    def test_credentials_in_command_are_rejected(self):
        with self.assertRaises(ValueError):
            sanitized_config({'mcp': {'service': {'command': ['service', '--password', 'opaque-value']}}})

    def test_arbitrary_auth_headers_and_environment_are_referenced(self):
        config, env = sanitized_config({'mcp': {'service': {'headers': {'X-Custom': 'opaque-value'}, 'environment': {'SERVICE_AUTH': 'another-value'}}}})
        self.assertNotIn('opaque-value', json.dumps(config))
        self.assertNotIn('another-value', json.dumps(config))
        self.assertEqual(len(env), 2)

    def test_existing_environment_references_are_reported(self):
        _, env = sanitized_config({'provider': {'options': {'apiKey': '{env:EXISTING_PROVIDER_KEY}'}}})
        self.assertEqual(env, ['EXISTING_PROVIDER_KEY'])

    def test_ambiguous_secret_structures_are_rejected(self):
        with self.assertRaises(ValueError):
            sanitized_config({'secret': ['opaque-value']})

    def test_file_occupying_parent_rejected_before_write(self):
        self.home.mkdir()
        (self.home / '.config').write_bytes(b'user work')
        with self.assertRaises(ValueError):
            restore(self.repo, self.home, apply=True)
        self.assertEqual((self.home / '.config').read_bytes(), b'user work')

    def test_removed_opaque_header_values_feed_cross_file_detection(self):
        values = []
        sanitized_config({'mcp': {'service': {'headers': {'X-Custom': 'opaque-private-credential'}}}}, values)
        self.assertEqual(values, ['opaque-private-credential'])
        self.assertTrue(scan_bytes(b'opaque-private-credential', 'plugin', values))

    def test_bearer_argument_and_compound_secret_flags_rejected(self):
        for arguments in [['service', '--client-secret', 'opaque-value'], ['service', '--header', 'Authorization: Bearer opaque-value'],
                          ['service', '--auth', 'opaque-value'], ['service', '--auth=opaque-value']]:
            with self.assertRaises(ValueError):
                sanitized_config({'mcp': {'service': {'command': arguments}}})

    def test_nested_session_and_generic_json_credentials_detected(self):
        self.assertTrue(session_storage({'nested': {'cookies': [{'domain': 'example.test', 'value': 'live-cookie'}]}}))
        self.assertTrue(structured_credentials({'apiKey': 'opaque-private-value'}))
        self.assertFalse(structured_credentials({'author': {'name': 'Public contributor'}}))

    @unittest.skipIf(os.name == 'nt', 'POSIX permission mode check')
    def test_rollback_refuses_changed_permissions(self):
        result = restore(self.repo, self.home, apply=True)
        path = self.home / '.config/opencode/AGENTS.md'
        path.chmod(0o600)
        self.assertFalse(rollback(self.home, result['transaction'], apply=True)['ok'])

    def test_alias_metacharacters_have_no_shell_semantics(self):
        target = self.root / 'alias-target'
        target.mkdir()
        path = self.root / 'alias&literal%name'
        make_alias(path, target)
        self.assertEqual(path.resolve(), target.resolve())
        from restore import remove
        remove(path)

    def test_failed_alias_rename_recovers_deleted_original(self):
        from unittest.mock import patch
        manifest = json.loads((self.repo / 'snapshot/manifest.json').read_text())
        payload = b'---\nname: sample\ndescription: sample\n---\nBody\n'
        canonical = '.agents/skills/sample/SKILL.md'
        manifest['files'].append({'path': canonical, 'blob': sha(payload), 'sha256': sha(payload),
            'bytes': len(payload), 'source_sha256': sha(payload), 'executable': False, 'transforms': []})
        (self.repo / 'snapshot/blobs' / sha(payload)).write_bytes(payload)
        manifest['aliases'] = [{'path': '.claude/skills/sample', 'target': '.agents/skills/sample', 'source_kind': 'symlink'}]
        republish(self.repo, manifest)
        path = self.home / '.claude/skills/sample'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'original user work')
        original_replace = os.replace
        def fail_alias(source, target):
            if '.portable-link-' in str(source):
                raise OSError('Synthetic alias rename failure')
            return original_replace(source, target)
        with patch('restore.os.replace', side_effect=fail_alias):
            with self.assertRaises(OSError):
                restore(self.repo, self.home, apply=True, replace=True)
        self.assertEqual(path.read_bytes(), b'original user work')

    def test_leading_comment_jsonc_does_not_bypass_credential_detection(self):
        value = structured_asset(b'// local config\n{"apiKey":"opaque-private-value"}', '.jsonc')
        self.assertTrue(structured_credentials(value))
        with self.assertRaises(ValueError):
            structured_asset(b'// malformed\n{"apiKey":', '.jsonc')

    def test_interrupted_file_rollback_keeps_current_file_and_resumes(self):
        from unittest.mock import patch
        path = self.home / '.config/opencode/AGENTS.md'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'old user work')
        path = path.resolve()
        result = restore(self.repo, self.home, apply=True, replace=True)
        from restore import atomic_write
        def fail_file(destination, payload, mode=0o600):
            if destination == path:
                raise OSError('Synthetic rollback I/O failure')
            return atomic_write(destination, payload, mode)
        with patch('restore.atomic_write', side_effect=fail_file):
            with self.assertRaises(OSError):
                rollback(self.home, result['transaction'], apply=True)
        self.assertTrue(path.is_file())
        self.assertTrue(rollback(self.home, result['transaction'], apply=True)['ok'])
        self.assertEqual(path.read_bytes(), b'old user work')

if __name__ == '__main__':
    unittest.main()
