#!/usr/bin/env python3
"""One entry point for capture, preview/apply restore, verify and guarded rollback."""
import argparse
import json
from pathlib import Path
import sys
import os
import subprocess

from backup import capture
from restore import restore, rollback
from verify import verify

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='action', required=True)
    backup = sub.add_parser('backup', help='Capture the real current installation, no reinstalls')
    backup.add_argument('--home', type=Path, default=Path.home())
    target = sub.add_parser('restore', help='Preview by default; --apply writes a rollback-protected plan')
    target.add_argument('--home', type=Path, default=Path.home())
    target.add_argument('--apply', action='store_true')
    target.add_argument('--dry-run', action='store_true')
    target.add_argument('--replace', action='store_true', help='Explicitly replace differing managed files; keep private rollback copies')
    migrate = sub.add_parser('migrate', help='One-command preflight, restore, bootstrap and native verification')
    migrate.add_argument('--home', type=Path, default=Path.home())
    migrate.add_argument('--apply', action='store_true')
    migrate.add_argument('--replace', action='store_true')
    check = sub.add_parser('verify')
    check.add_argument('--home', type=Path)
    check.add_argument('--native', action='store_true')
    run = sub.add_parser('run', help='Run pinned OpenCode with its own data directory, preserving other versions and sessions')
    run.add_argument('--home', type=Path, default=Path.home())
    run.add_argument('arguments', nargs=argparse.REMAINDER)
    undo = sub.add_parser('rollback')
    undo.add_argument('transaction')
    undo.add_argument('--home', type=Path, default=Path.home())
    undo.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'run':
            home = args.home.resolve()
            prefix = home / '.local/share/opencode-portable/tools/node_modules'
            package = json.loads((prefix / 'opencode-ai/package.json').read_text())
            binary = prefix / 'opencode-ai' / package['bin']['opencode']
            env = os.environ.copy()
            env['XDG_DATA_HOME'] = str(home / '.local/share/opencode-portable/data')
            env['PATH'] = str(prefix / '.bin') + os.pathsep + env.get('PATH', '')
            arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
            return subprocess.call([str(binary)] + arguments, env=env)
        if args.action == 'backup':
            report = capture(args.home, args.repo.resolve())
        elif args.action == 'restore':
            if args.apply and args.dry_run:
                parser.error('--apply and --dry-run are mutually exclusive')
            report = restore(args.repo.resolve(), args.home, args.apply, args.replace)
        elif args.action == 'migrate':
            report = restore(args.repo.resolve(), args.home, False, args.replace)
            if args.apply and report['ok']:
                if report['missing_runtime_prerequisites']:
                    report['ok'] = False
                else:
                    report = restore(args.repo.resolve(), args.home, True, args.replace)
                    from bootstrap import bootstrap
                    try:
                        report['bootstrap'] = bootstrap(args.repo.resolve(), args.home, True)
                        report['verification'] = verify(args.repo.resolve(), args.home, True)
                        report['ok'] = report['verification']['ok']
                        report['path_instruction'] = 'Use portable.py run -- <OpenCode arguments> for isolated data; use codex -p portable for the Codex MCP profile. Authenticate providers and trust Codex hooks locally.'
                    except Exception:
                        report['ok'] = False
                        report['error'] = 'Runtime/bootstrap validation failed; the displayed restore transaction remains available for rollback.'
        elif args.action == 'verify':
            report = verify(args.repo.resolve(), args.home, args.native)
        else:
            report = rollback(args.home, args.transaction, args.apply)
    except (ValueError, OSError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report.get('ok', True) else 1

if __name__ == '__main__':
    sys.exit(main())
