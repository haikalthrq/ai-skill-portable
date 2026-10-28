"""Produce a publishable inventory; no original absolute paths or auth values."""
from collections import Counter
import json
from pathlib import Path

from common import dump
from restore import load_snapshot

repo = Path(__file__).resolve().parents[1]
manifest, data = load_snapshot(repo)
report = {'snapshot_id': manifest['snapshot_id'], 'created_utc': manifest['created_utc'],
    'codex': manifest.get('codex'),
    'antigravity': manifest.get('antigravity'),
    'supported_targets': ['codex', 'opencode', 'antigravity'],
    'active_core_skills': manifest.get('active_core_skills'),
    'discoverable_skills': manifest['expected_discovery_count'], 'builtin_skills': [s['name'] for s in manifest['skills'] if s['builtin']],
    'skills': [{'name': s['name'], 'description': s['description'], 'definition_paths': s['definition_candidates']} for s in manifest['skills']],
    'definition_paths': len(manifest['definitions']), 'directory_aliases': len(manifest['aliases']),
    'logical_files': len(manifest['files']), 'unique_content_blobs': len({f['blob'] for f in manifest['files']}),
    'logical_bytes': sum(f['bytes'] for f in manifest['files']),
    'stored_blob_bytes': sum(p.stat().st_size for p in (repo / 'snapshot/blobs').iterdir()),
    'portability_transform_counts': dict(Counter(t for f in manifest['files'] for t in f['transforms'])),
    'dependencies': manifest['dependencies'], 'observed_prerequisites': manifest['observed_prerequisites'],
    'required_environment': manifest['required_environment'], 'optional_projects': manifest['optional_project_checkouts'],
    'excluded': manifest['excluded'], 'aliases': manifest['aliases']}
dump(repo / 'reports/inventory.json', report)
print(json.dumps({k: report[k] for k in ['discoverable_skills', 'definition_paths', 'directory_aliases', 'logical_files',
    'unique_content_blobs', 'logical_bytes', 'stored_blob_bytes', 'required_environment']}, indent=2))
