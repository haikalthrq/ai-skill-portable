# ai-skill-portable

Portable, reproducible backup for an **OpenCode-first AI coding environment**.

> **Status:** Repository scaffold only. No machine-specific skill snapshot has been uploaded yet. Run the migration brief from the original laptop to export and verify the real installation.

## Goal

Move to another Windows computer without manually reinstalling dozens of AI agent skills. Preserve the actual customized skill bodies, references, scripts, aliases, global instructions, and routing decisions rather than merely recording upstream GitHub URLs.

Current known baseline (reported, **not independently inspected from this repo**): 45 discoverable skills, optimized frontend intent routing, Context7 MCP, and ECC Memory.

## Operating model

1. **Export** from the original computer: inventory all relevant OpenCode and other discoverable global skill roots, copy approved files, capture hash manifest, safe rule/config templates, dependencies and source provenance.
2. **Review** changes locally before committing. GitHub being private is **not** permission to upload passwords, session files, API tokens, cookies, Git credentials, or personal data.
3. **Push** the sanitized backup to this repository.
4. **Restore** on a new computer: install the OpenCode runtime and prerequisites, clone, preview changes, restore idempotently, resolve portable paths, then authenticate MCP/providers locally.
5. **Verify** skill discovery, native calls, routing behavior, references, scripts and checksums.

## What belongs in the backup

- Global skill directories actually discovered on the original computer (including supporting `SKILL.md` references, binaries/scripts only when appropriate, and databases).
- Global `AGENTS.md` rules and frontend/engineering routing policy.
- Native variants, explicitly documented aliases and symlink targets.
- Non-secret configuration templates, plugin/package manifests and prerequisites.
- Original upstream repository URLs and pinned revisions, where available.
- Backup, restore and verification scripts.

## Never commit

- API keys, credentials, OAuth tokens, refresh tokens, .env files, session data, cookies, SSH keys, browser profiles, package registry credentials.
- Raw auth/provider configuration or `~/.local/share/opencode/auth.json`.
- Entire home directories, project source trees, browser caches, package caches, session logs, or `node_modules`.
- Absolute machine paths without a relocatable mapping.

Secret scanning is required **before** any `git add` or `git push`. If a secret is accidentally committed, simply deleting it later is insufficient: rotate/revoke the credential and clean Git history.

## Canonical migration instructions

See [MIGRATION-BRIEF.md](./MIGRATION-BRIEF.md). It specifies the complete task for an OpenCode agent running locally on the original computer.

Expected generated deliverables include `scripts/backup`, `scripts/restore`, `scripts/verify`, `manifest` and `snapshot` directories, but implementation and paths must follow a verified live inventory, not assumptions from this README.

## Important limitations

- A repository snapshot does **not** automatically transfer an authenticated MCP/provider session. Reauthorize on the new computer.
- OpenCode and external CLIs must still be installed on the target machine; they should be handled by the restore/bootstrap routine.
- A successful file copy is not proof of working skill routing. Test fresh OpenCode sessions.
- Never apply a destructive restore over existing configurations without a preview and rollback backup.
