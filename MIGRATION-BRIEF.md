# Implemented migration contract

This repository contains the real sanitized snapshot and a working migration system. It is an OpenCode-first **environment** backup, not a project/transcript/authentication backup and not an upstream skill installer.

## Authoritative artifacts

| Artifact | Purpose |
|---|---|
| `snapshot/manifest.json` | Schema/version, content identity, source hashes, installed tool pins, all skill definitions, aliases, declared path adaptations and authentication requirements |
| `snapshot/blobs/<sha256>` | Deduplicated actual installed content; plain files, not opaque archives hiding scan results |
| `scripts/portable.py` | Idempotent capture, preview/apply restore, one-command migrate/bootstrap/verify, and guarded rollback |
| `scripts/bootstrap.py` | Target-home runtime/package setup; no skill installation/update |
| `scripts/secret_scan.py`, `fetch_gitleaks.py` | Fail-closed local checks plus pinned independent scanner |
| `scripts/integration_test.py`, `tests/` | Disposable full restore/rollback and adversarial path/credential tests |
| `scripts/routing_probe.py` | Fresh authenticated native skill calls after restore |
| `reports/` | Publishable inventory, Windows/Linux validation, routing and secret-scan results |

## Preservation rules

1. Read the installed files. Preserve their descriptions, bodies, references, scripts, datasets, licenses, local adapters and custom plugins. Never replace them with current upstream downloads merely because upstream exists.
2. Keep physical variants distinct. Deduplicate identical file content only; reconstruct original directory destinations and explicit aliases from the manifest.
3. Snapshot all 45 native discovery names, including the built-in supplied by the pinned OpenCode runtime. Retain Graphify and non-primary-harness variants as auxiliary preserved files without adding them to OpenCode's discovery set.
4. Keep Context7/ECC integration instructions and host-identity/repository-binding behavior. Exclude all authentication, browser/session data, memory vault records and unrelated home/project content.
5. Never change the original skill installation during backup/testing. The Windows integration evidence rehashes the captured source files to detect mutation.

## Portable path contract

- Destinations are home-relative, allowlisted logical paths. Absolute paths, traversal, duplicate destinations, file/directory collisions and unapproved redirected parents are rejected before mutation.
- Actual home prefixes become `__PORTABLE_HOME__` in stored text and expand on restore. Source and transformed hashes distinguish intentional portability from accidental content changes.
- The ECC memory/runtime configuration points to the captured installed memory implementation under `$HOME/.local/share/opencode-portable/ecc-runtime`, rather than the old Windows roaming npm path.
- MCP uses `node` from PATH; native plugin paths become relocatable file URLs. Explicit global skill paths make the retained native roots discoverable on both platforms.
- Windows junctions and Linux relative symlinks recreate directory aliases. Windows reparse-point detection does not depend on Python 3.12-only methods.
- Linux adjusts the copied DCG plugin's PATH delimiter; the original live plugin and stored source identity stay unchanged.
- RINGKAS-only references map to `$HOME/Projects/RINGKAS`; the private project is not backed up. Animate's preserved upstream reference receives a copied companion RECIPES.md without modifying the source installation.

## Credential boundary

The exporter uses an explicit root/file allowlist and rejects credential filenames, session storage, unclassified binaries, credential-bearing URLs/command arguments and ambiguous secret structures. Credential-bearing headers/environment/settings become `{env:NAME}` references. Existing references are also recorded as requirements.

Tokens stay in memory while sanitizing; their values are never printed or put in the manifest. Original source hashes are integrity evidence, not credential storage. OAuth/provider auth, `.env`, registry/Git/SSH/GPG/cloud credentials, browser profiles, user/project memory and raw session logs are excluded.

Gitleaks scans the publishable repository including content blobs before staging/push. No blanket exclusion for snapshots or dependency code is permitted. Private scratch/install/journal directories are ignored and never staged. Synthetic local routing QA may temporarily borrow provider authentication into a restricted OS temporary profile; it deletes that file afterward and reports only names/counts.

## Restore and rollback semantics

1. Verify manifest and every content blob before any target write.
2. Plan the entire restore, including aliases and competing global configuration. Preview is read-only and repeatable.
3. Refuse differing user files by default. `--replace` authorizes managed replacements and records exact previous bytes privately.
4. Create a private journal before mutation. Verify saved pre-change bytes against their planned hashes. Write files atomically; recheck destination state/containment before operations.
5. Repeated apply produces zero changes. Rollback checks expected current states, restores old content or removes new content, and repeated rollback produces zero changes.
6. Refuse newer observed changes or redirected aliases/state/parents. Do not overwrite physical skill directories to force an alias. Stop concurrent applications/editors during restore/rollback; this is not an interprocess locking system.
7. Bootstrap only target-home pinned runtimes, with unrelated lifecycle scripts disabled. Initialize the captured plugin dependencies before native startup so OpenCode does not rewrite absent SDK manifests.
8. Reauthenticate services on the new device and restart OpenCode. Restore is not proof of credential validity or of availability of every remote model listed in preserved preferences.

## Verification gates before publication

- Payload/content-address identity and original-file preservation.
- Complete Windows and Linux disposable restore, real junction/symlink aliases, repeated previews/apply/bootstrap, complete rollback.
- Fresh native discovery of exactly 45 names; descriptions and loaded bodies match the restored snapshot; paths remain in the sandbox.
- Real UI UX Pro Max data search and ECC memory save/read/doctor, custom MCP initialization/tools and handoff helper.
- Fresh model-driven frontend/debugging/handoff/backend routing tests with no skill names in those prompts.
- Adversarial tests for corruption, traversal, duplicate/prefix conflicts, redirected parents/state, credentials and preservation of newer work.
- Independent redacted secret scan before staging and again before pushing; inspect Git status, diff and recent history, then commit only intended files.

## Maintenance limits and manual setup

Python/Git/Node, provider login, Context7 key, browser installation, optional DCG/Graphify/OfficeCLI and private project checkouts remain local setup. OfficeCLI already had a missing .NET assembly on the source host; its skill is preserved without claiming the broken runtime was fixed.

Capture intentionally fails if this complete environment's required ECC binding or discovered out-of-allowlist skill is missing. Review and explicitly extend mappings before capturing external roots; never traverse arbitrary personal directories. Retain third-party licenses/notices, inspect scripts before bootstrap, and use the tested pinned OpenCode version for equivalent discovery. Different future harness/model versions can choose skills differently even when the file snapshot is identical.
