from pathlib import Path
import contextlib
import io
import re
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import claude_port

ALLOWED_STRICT = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}


def keys(skill_md):
    fields = re.match(r'\A---\n(.*?)\n---\n', skill_md, re.S).group(1)
    return {line.split(':', 1)[0] for line in fields.splitlines() if line and not line[0].isspace()}, fields


class ClaudePortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='claude-port-test-')
        cls.out = Path(cls.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            claude_port.main(['--out', str(cls.out), '--zip'])
        cls.skills = sorted(p.name for p in (cls.out / 'skills').iterdir())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_snapshot_skill_is_ported_once(self):
        self.assertEqual(len(self.skills), 50)
        self.assertNotIn('graphify', self.skills)
        self.assertEqual(sorted(p.stem for p in (self.out / 'upload').glob('*.zip')), self.skills)

    def test_frontmatter_is_claude_valid(self):
        for name in self.skills:
            text = (self.out / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
            found, fields = keys(text)
            self.assertIn('name: "%s"' % name, fields, name)
            description = re.search(r'^description: (".*")$', fields, re.M).group(1)
            self.assertLessEqual(len(description), 1026, name)
            self.assertNotRegex(description, '[<>]', name)
            self.assertNotIn('\r', text, name)
            self.assertFalse((self.out / 'skills' / name / 'agents/openai.yaml').exists(), name)

    def test_strict_zip_uses_only_upload_keys(self):
        for archive in (self.out / 'upload').glob('*.zip'):
            with zipfile.ZipFile(archive) as z:
                names = z.namelist()
                self.assertTrue(all(n.startswith(archive.stem + '/') for n in names), archive)
                found, _ = keys(z.read(archive.stem + '/SKILL.md').decode('utf-8'))
                self.assertLessEqual(found, ALLOWED_STRICT, archive.stem)
                self.assertEqual(sum(n.endswith('/SKILL.md') for n in names), 1, archive.stem)

    def test_claude_code_keeps_boolean_invocation_flag(self):
        text = (self.out / 'skills/handoff/SKILL.md').read_text(encoding='utf-8')
        self.assertRegex(text, r'(?m)^disable-model-invocation: true$')

    def test_platform_paths_are_rewritten(self):
        for path in (self.out / 'skills').rglob('*.md'):
            text = path.read_text(encoding='utf-8')
            for old in ('~/.opencode/skills/', '~/.agents/skills/', '~/.config/opencode/skills/'):
                self.assertNotIn(old, text, path)

    def test_parse_handles_folded_lists_and_quotes(self):
        meta = claude_port.parse('name: x\ndescription: >\n  one\n  two\nrequirements:\n  - a\n'
                                 "license: 'it''s'\nflag: true\nmetadata:\n  k: \"v\"")
        self.assertEqual(meta, {'name': 'x', 'description': 'one two', 'requirements': ['a'],
                                'license': "it's", 'flag': True, 'metadata': {'k': 'v'}})


if __name__ == '__main__':
    unittest.main()
