from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from antigravity import DEPRECATED
from backup import retired_plugin, strip_retired_sections


class RetiredToolTests(unittest.TestCase):
    def test_graphify_is_retired(self):
        self.assertIn('graphify', DEPRECATED)

    def test_retired_plugin_paths(self):
        self.assertTrue(retired_plugin('.opencode/.opencode/plugins/graphify.js'))
        self.assertTrue(retired_plugin('file:///__PORTABLE_HOME__/.opencode/.opencode/plugins/graphify.js'))
        self.assertTrue(retired_plugin('C:\\Users\\me\\.opencode\\plugins\\graphify.js'))
        self.assertFalse(retired_plugin('.opencode/plugins/dcg-guard.js'))
        self.assertFalse(retired_plugin('.codex/skills/graphify/SKILL.md'))

    def test_strip_keeps_neighbours_and_line_endings(self):
        text = ('intro\r\nlast line.\r\n# graphify\r\n- **graphify** trigger\r\n'
                'When the user types `/graphify` do it.\n\n## Next section\n\nbody\n')
        self.assertEqual(strip_retired_sections(text), 'intro\r\nlast line.\r\n\n## Next section\n\nbody\n')

    def test_strip_is_noop_without_retired_section(self):
        text = '# Title\n\n## Graphify-like words in prose stay\n\ntext about graphs\n'
        self.assertEqual(strip_retired_sections(text), text)

    def test_strip_retired_section_at_end_of_file(self):
        self.assertEqual(strip_retired_sections('# keep\nbody\n\n# graphify\n- x\n'), '# keep\nbody\n\n')

    def test_published_snapshot_has_no_retired_content(self):
        manifest = json.loads((ROOT / 'snapshot/manifest.json').read_text(encoding='utf-8'))
        for record in manifest['files']:
            self.assertFalse(any(name in record['path'].lower().split('/') or
                                 record['path'].lower().endswith('/' + name + '.js') for name in DEPRECATED),
                             record['path'])
        names = {d['name'] for d in manifest['definitions']}
        self.assertFalse(names & DEPRECATED)
        self.assertNotIn('graphify', manifest['dependencies']['optional_tools'])


if __name__ == '__main__':
    unittest.main()
