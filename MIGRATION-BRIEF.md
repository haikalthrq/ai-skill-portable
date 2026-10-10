# OpenCode global environment: migration / portability implementation brief

Implement this **on the original Windows laptop with actual filesystem access**, using this repository as the private backup target:
`https://github.com/haikalthrq/ai-skill-portable.git`

**Do the work**, rather than merely writing instructions. The owner wants a reproducible one-command backup and one-command restore that preserve the existing OpenCode skill environment. This document is a specification, not evidence that a backup exists.

## Priorities

- OpenCode is the primary daily harness.
- Preserve the installed, customized, optimized skill sources as they exist; **do not reinstall, rename, simplify, upgrade, or modify** protected skill bodies in the process.
- Preserve 45 discovered skills as a baseline, but determine the actual current count from the system; include out-of-home definitions and aliases as necessary.
- Preserve optimized routing, source references, scripts/data, global `AGENTS.md`, dependencies and native variants without introducing duplicate definitions.
- Context7 and ECC Memory are already configured: capture **non-secret templates and setup instructions only**. Never export their tokens.
- Do not run a broad refactor of the current OpenCode setup.

## Inventory first

Detect actual global discovery roots and effective configuration for installed OpenCode version; do not assume a directory is active solely because it exists.

Inspect candidates (only if present): `~/.agents/skills`, `~/.opencode/skills`, `~/.config/opencode/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.gemini/skills`, `~/.config/opencode/AGENTS.md`, and applicable global routing/agent/command definitions.

Inspect the existing optimization manifests and references, e.g. `~/.config/skills-optimization/`, for alias relationships, native variants, and known customizations. Avoid copying large historical backups needlessly.

Record every discovered skill (canonical name, definition path, dependencies, origin repo + revision if known, hashes, alias/symlink relationship, route priority). Follow supported symlinks carefully; do not traverse arbitrary targets or include unrelated private files. Handle user-created skills outside the usual home paths explicitly and safely.

## Design the portable layout

Use a snapshot layout that mirrors the actual installed locations via logical `$HOME`-relative paths, plus an explicit mapping for approved external locations. Never hard-code an old `C:\\Users\\...` path in restore logic.

Keep a machine-readable manifest with at least:
- snapshot/schema version
- timestamp (UTC)
- OS/harness/tool versions
- source/destination logical path for each backed-up subtree
- skill inventory and alias relationships
- hashes/file counts for integrity
- provenance and dependency/runtime requirements
- expected native discovery count
- relative references that must resolve post-restore

Store optional sanitized config examples separately from live auth/config files.

## Security: fail closed

Default-deny credential-bearing paths and data:
- `.env*`, `*.pem`, `*.key`, SSH/GPG and cloud credentials
- `auth.json`, token/session/cookie caches, browser profiles, `.npmrc`, `.pypirc`, Git credentials
- raw OpenCode/provider/MCP configuration unless individually reviewed and sanitized
- user projects, logs, build caches and `node_modules`

Use an allowlist for snapshot roots and file classes, inspect files for embedded secrets and absolute private paths, and run an available secret scanner (e.g. gitleaks) as a separate pre-commit check. Stop with a clear report on suspicious material; do not silently scrub executable instructions. A private GitHub repo is not an acceptable secret vault.

Respect licenses and file size limitations for bundled third-party assets; retain origin information, notices and existing licenses where applicable.

## Implement scripts

Choose the simplest tested approach for Windows (PowerShell plus Python are available), and support portability where practical.

1. `backup`: scan actual environment; stage into a temporary directory; generate snapshot, manifest, hash report; validate; atomically update repo working tree; display diff/summary; scan secrets; only then commit/push. Never push before user-readable verification.
2. `restore --dry-run`: inspect source backup and destination environment, verify hashes and path mappings, list modifications/conflicts, check dependencies, confirm no secrets; **never** modify current config.
3. `restore --apply`: idempotently restore files, preserving content; back up existing destination files with a clear rollback plan; protect conflicts (no destructive overwrites by default); re-create aliases or safely materialize them on Windows if symlink permission is unavailable; report required local authentications and missing runtimes.
4. `verify`: compare recorded hashes, resolve reference/dependency paths, check OpenCode discovery count, run read-only native skill routing probes (including frontend, debugging, handoff and backend-only), report failures.

Do a simulated restore to a **temporary clean HOME** or disposable profile before touching any existing real destination.

Create a concise README explaining:
- what is and isn't backed up
- exact commands for daily backup
- exact commands for first-time new-device restore
- how to update skill snapshots
- how to authenticate GitHub, Context7, ECC Memory and other external services safely
- how to roll back
- limitations such as Windows/Linux differences

## Done means tested

- Verify the exported snapshot contains **all actual discoverable skills**, not just first-party definitions or top-level `SKILL.md` files.
- Verify aliases, optimized references, scripts and data files have not been lost.
- Verify routing/global rules don't duplicate or conflict.
- Verify restore idempotence, with two clean dry-runs and one sandbox restore.
- Confirm backup files committed/pushed to `main` only after secret scanning and review.
- Show final remote commit URL, backed-up skills count, total size, paths, excluded paths, dependencies, verification evidence and any manual login steps.
- If an essential step can't be verified, report the exact blocker rather than claiming success.
