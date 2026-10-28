from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from antigravity import ROOT, frontmatter, materialize_snapshot, verify_antigravity
from common import link, sha
from restore import load_snapshot, make_alias, restore, rollback, remove
from test_portable import fixture, republish


class AntigravityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='antigravity-test-')
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.home = self.base / 'home with spaces'
        self.repo.mkdir()
        self.manifest = fixture(self.repo)
        self.blobs = self.repo / 'snapshot/blobs'
        self.files = {r['path']: r for r in self.manifest['files']}
        self.definitions = [{'name': 'sample', 'path': '.agents/skills/sample/SKILL.md',
                             'canonical': '.agents/skills/sample/SKILL.md', 'alias': False}]
        self.aliases = {ROOT + '/sample': {'path': ROOT + '/sample',
                       'target': '.agents/skills/sample', 'source_kind': 'junction'}}
        self.add('.agents/skills/sample/SKILL.md', b'---\nname: sample\ndescription: Sample task guidance\n---\n# Shared body\n')
        self.add('.agents/skills/sample/references/help.md', b'# Supporting reference\n')

    def tearDown(self):
        self.temp.cleanup()

    def add(self, path, payload):
        digest = sha(payload)
        (self.blobs / digest).write_bytes(payload)
        self.files[path] = {'path': path, 'blob': digest, 'sha256': digest, 'bytes': len(payload),
                            'source_sha256': digest, 'executable': False, 'transforms': []}

    def publish(self):
        metadata = materialize_snapshot(self.files, self.blobs, self.definitions, self.aliases)
        self.manifest.update({'files': list(self.files.values()), 'definitions': self.definitions,
                              'aliases': list(self.aliases.values()), 'antigravity': metadata})
        republish(self.repo, self.manifest)
        return load_snapshot(self.repo)

    def test_restore_materializes_alias_and_support_files_with_rollback(self):
        manifest, data = self.publish()
        preview = restore(self.repo, self.home)
        self.assertTrue(preview['ok'])
        self.assertFalse(self.home.exists())
        applied = restore(self.repo, self.home, apply=True)
        self.assertTrue(applied['ok'])
        folder = self.home / ROOT / 'sample'
        self.assertFalse(link(folder))
        self.assertEqual((folder / 'references/help.md').read_bytes(), b'# Supporting reference\n')
        self.assertTrue(verify_antigravity(manifest, self.home, data)['ok'])
        self.assertEqual(restore(self.repo, self.home, apply=True)['changes'], 0)
        self.assertTrue(rollback(self.home, applied['transaction'], apply=True)['ok'])
        self.assertFalse((folder / 'SKILL.md').exists())
        self.assertEqual(rollback(self.home, applied['transaction'], apply=True)['changes'], 0)

    def test_existing_native_variant_keeps_its_own_files(self):
        native = b'---\nname: sample\ndescription: Antigravity-specific task\n---\n# Native body\n'
        self.add(ROOT + '/sample/SKILL.md', native)
        self.add(ROOT + '/sample/references/native.md', b'# Native help\n')
        manifest, data = self.publish()
        self.assertEqual(data[ROOT + '/sample/SKILL.md'], native)
        self.assertFalse(manifest['aliases'])
        self.assertTrue(all(not d['alias'] for d in manifest['definitions']))

    def test_existing_junction_is_rejected_without_touching_its_target(self):
        self.publish()
        target = self.base / 'existing skill'
        target.mkdir()
        (target / 'SKILL.md').write_text('existing user bytes')
        folder = self.home / ROOT / 'sample'
        make_alias(folder, target)
        try:
            with self.assertRaises(ValueError):
                restore(self.repo, self.home, apply=True, replace=True)
            self.assertEqual((target / 'SKILL.md').read_text(), 'existing user bytes')
            self.assertFalse((self.home / '.config/opencode/AGENTS.md').exists())
        finally:
            remove(folder)
        self.assertFalse(link(folder))

    def test_unmanaged_nested_link_blocks_whole_restore_before_writes(self):
        self.publish()
        folder = self.home / ROOT / 'sample'
        folder.mkdir(parents=True)
        target = self.base / 'user assets'
        target.mkdir()
        (target / 'notes.txt').write_text('keep user data')
        make_alias(folder / 'unmanaged-link', target)
        try:
            with self.assertRaisesRegex(ValueError, 'symlink or reparse'):
                restore(self.repo, self.home, apply=True, replace=True)
            self.assertEqual((target / 'notes.txt').read_text(), 'keep user data')
            self.assertFalse((folder / 'SKILL.md').exists())
            self.assertFalse((self.home / '.config/opencode/AGENTS.md').exists())
        finally:
            remove(folder / 'unmanaged-link')

    def test_verifier_rejects_linked_or_broken_skill_directory(self):
        manifest, data = self.publish()
        source = self.base / 'source'
        source.mkdir()
        (source / 'SKILL.md').write_text('source')
        folder = self.home / ROOT / 'sample'
        make_alias(folder, source)
        try:
            self.assertFalse(verify_antigravity(manifest, self.home, data)['ok'])
            (source / 'SKILL.md').unlink()
            source.rmdir()
            self.assertFalse(verify_antigravity(manifest, self.home, data)['ok'])
        finally:
            remove(folder)

    def test_verifier_rejects_nested_links_and_modified_references(self):
        manifest, data = self.publish()
        restore(self.repo, self.home, apply=True)
        folder = self.home / ROOT / 'sample'
        (folder / 'references/help.md').write_text('changed')
        self.assertFalse(verify_antigravity(manifest, self.home, data)['ok'])
        (folder / 'references/help.md').write_bytes(b'# Supporting reference\n')
        target = self.base / 'nested-target'
        target.mkdir()
        make_alias(folder / 'linked-assets', target)
        try:
            self.assertFalse(verify_antigravity(manifest, self.home, data)['ok'])
        finally:
            remove(folder / 'linked-assets')

    def test_snapshot_rejects_antigravity_alias_records(self):
        self.publish()
        self.manifest['aliases'] = [{'path': ROOT + '/other', 'target': '.agents/skills/sample'}]
        republish(self.repo, self.manifest)
        with self.assertRaisesRegex(ValueError, 'physical directories'):
            load_snapshot(self.repo)

    def test_snapshot_rejects_inventory_mismatch_and_invalid_frontmatter(self):
        self.publish()
        self.manifest['antigravity']['skills'] = ['missing']
        republish(self.repo, self.manifest)
        with self.assertRaises(ValueError):
            load_snapshot(self.repo)

        self.manifest['antigravity']['skills'] = ['sample']
        self.add(ROOT + '/sample/SKILL.md', b'---\nname: sample\ndescription:\n---\nBody\n')
        self.manifest['files'] = list(self.files.values())
        republish(self.repo, self.manifest)
        with self.assertRaisesRegex(ValueError, 'frontmatter'):
            load_snapshot(self.repo)

    def test_snapshot_requires_physical_definition_path_index(self):
        self.publish()
        self.manifest['definitions'] = self.manifest['definitions'][:1]
        republish(self.repo, self.manifest)
        with self.assertRaisesRegex(ValueError, 'definition paths'):
            load_snapshot(self.repo)
        self.manifest['definitions'] = self.definitions
        self.manifest['definition_paths'] = []
        republish(self.repo, self.manifest)
        with self.assertRaisesRegex(ValueError, 'index is out of sync'):
            load_snapshot(self.repo)

    def test_frontmatter_rejects_empty_or_mismatched_fields(self):
        descriptions = ['', '# comment only', '""', '"unfinished', 'null', '[]', '{}', '123', '[not, a, string]', '>\nlicense:\n  nested: value']
        for description in descriptions:
            text = '---\nname: sample\ndescription: ' + description + '\n---\nBody\n'
            self.assertFalse(frontmatter(text, 'sample'), description)
        self.assertFalse(frontmatter('---\nname: other\ndescription: text\n---\nBody', 'sample'))
        self.assertFalse(frontmatter('---\nname: sample\nname: other\ndescription: text\n---\nBody', 'sample'))
        self.assertFalse(frontmatter('---\nname: sample\ndescription: text\ndescription: other\n---\nBody', 'sample'))
        self.assertFalse(frontmatter("---\nname: 'sample\ndescription: text\n---\nBody", 'sample'))
        self.assertFalse(frontmatter('---\nname:sample\ndescription: text\n---\nBody', 'sample'))
        self.assertFalse(frontmatter('---\nname: sample\ndescription:text\n---\nBody', 'sample'))
        for extra in ['"name": other', "'description': []", 'name : other', r'"\u006eame": other', '? name\n: other']:
            text = '---\nname: sample\ndescription: text\n' + extra + '\n---\nBody'
            self.assertFalse(frontmatter(text, 'sample'), extra)
        self.assertTrue(frontmatter('---\nname: sample\ndescription: >\n  A folded description\nlicense: MIT\n---\nBody', 'sample'))


if __name__ == '__main__':
    unittest.main()
