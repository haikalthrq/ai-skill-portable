"""Fail-closed local scanning. Findings never print credential values."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

PATTERNS = {
    'context7-key': re.compile(r'ctx7sk-[a-fA-F0-9-]{30,}'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'openai-key': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}'),
    'aws-access-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'credential-url': re.compile(r'https?://[^\s/:]+:[^\s/@]+@'),
}

def scan_bytes(data, label, known=()):
    text = data.decode('utf-8', errors='ignore')
    findings = [{'path': label, 'rule': name} for name, pattern in PATTERNS.items() if pattern.search(text)]
    for secret in known:
        if secret and len(secret) >= 8 and secret in text:
            findings.append({'path': label, 'rule': 'source-credential-exact-match'})
    return findings

def scan(root, known=()):
    findings = []
    count = 0
    for path in sorted(root.rglob('*')):
        if any(part in {'.git', '.work', 'node_modules', '__pycache__'} for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            findings.append({'path': path.relative_to(root).as_posix(), 'rule': 'unexpected-symlink'})
        elif path.is_file():
            count += 1
            findings.extend(scan_bytes(path.read_bytes(), path.relative_to(root).as_posix(), known))
    return {'ok': not findings, 'files_scanned': count, 'findings': findings}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--gitleaks', help='Require independent Gitleaks executable, not just local patterns')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = scan(args.root)
    if args.gitleaks:
        binary = shutil.which(args.gitleaks) or args.gitleaks
        result = subprocess.run([binary, 'dir', str(args.root), '--redact', '--no-banner', '--no-color',
            '--config', str(args.root / '.gitleaks.toml'), '--report-format', 'json',
            '--report-path', str(args.root / '.work/gitleaks-findings.json')], capture_output=True, text=True)
        report['gitleaks_exit_code'] = result.returncode
        report['gitleaks_ok'] = result.returncode == 0
        report['ok'] = report['ok'] and report['gitleaks_ok']
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    sys.exit(main())
