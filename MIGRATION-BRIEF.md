# Codex, OpenCode and Google Antigravity migration contract

This repository preserves the installed skill environment for Codex, OpenCode and Google Antigravity App/IDE. Credentials, private projects, transcripts and memory records remain local.

## Authoritative artifacts

| Artifact | Purpose |
|---|---|
| `snapshot/manifest.json` | Schema/version, content identity, source hashes, installed tool pins, all skill definitions, aliases, declared path adaptations and authentication requirements |
| `snapshot/blobs/<sha256>` | Deduplicated actual installed content; plain files, not opaque archives hiding scan results |
| `scripts/portable.py` | Idempotent capture, preview/apply restore, one-command migrate/bootstrap/verify, and guarded rollback |
| `scripts/bootstrap.py` | Target-home runtime/package setup; no skill installation/update |
| `scripts/antigravity.py` | Physical Antigravity skill copies and required frontmatter/file verification |
| `scripts/secret_scan.py`, `fetch_gitleaks.py` | Fail-closed local checks plus pinned independent scanner |
| `scripts/integration_test.py`, `tests/` | Disposable full restore/rollback and adversarial path/credential tests |
| `scripts/routing_probe.py` | Fresh authenticated native skill calls after restore |
| `reports/` | Publishable inventory, Windows/Linux validation, routing and secret-scan results |

## Preservation rules

1. Read the installed files. Preserve their descriptions, bodies, references, scripts, datasets, licenses, local adapters and custom plugins. Never replace them with current upstream downloads merely because upstream exists.
2. Keep physical variants distinct. Deduplicate identical file content only; reconstruct original directory destinations and explicit aliases from the manifest.
3. Keep 43 unique active core skills, including the installed reverse-engineering skill. Exclude retired `caveman` and `officecli` definitions, content and installation metadata. Codex has 50 portable skills (core, Graphify, six Ponytail skills); OpenCode has 50 names (core, Ponytail, one built-in). Antigravity receives the 43 core skills. Preserve provider variants and keep those count categories separate.
4. Keep Context7/ECC integration instructions and host-identity/repository-binding behavior. Exclude all authentication, browser/session data, memory vault records and unrelated home/project content.
5. Never change the original skill installation during backup/testing. Integration tests rehash captured source files to detect mutation. Removing a skill from this backup does not delete its live installation or user data.

## Portable path contract

- Destinations are home-relative, allowlisted logical paths. Absolute paths, traversal, duplicate destinations, file/directory collisions and unapproved redirected parents are rejected before mutation.
- Actual home prefixes become `__PORTABLE_HOME__` in stored text and expand on restore. Source and transformed hashes distinguish intentional portability from accidental content changes.
- The ECC memory/runtime configuration points to the captured installed memory implementation under `$HOME/.local/share/opencode-portable/ecc-runtime`, rather than the old Windows roaming npm path.
- MCP uses `node` from PATH; native plugin paths become relocatable file URLs. Explicit global skill paths make the retained native roots discoverable on both platforms.
- Windows junctions and Linux relative symlinks recreate aliases outside the Antigravity target. Windows reparse-point detection does not depend on Python 3.12-only methods.
- Antigravity App/IDE global skills use `.gemini/config/skills/<skill>/SKILL.md` under the target home. Capture dereferences approved core aliases into physical file records and keeps existing native variants. Restore writes real directories with all supporting files on every OS; no Antigravity alias/junction records are allowed. Windows Antigravity does not follow NTFS junctions/reparse points.
- Antigravity's copies use the normal restore journal, conflict checks and rollback. Existing redirected destination parents are rejected before writing, including with `--replace`; their targets remain untouched. Resolve an existing linked installation explicitly rather than copying through it.
- `migrate --antigravity` and `bootstrap.py --antigravity` require Antigravity metadata; current snapshots deploy it by default. `verify --home <home> --antigravity` checks required name/description frontmatter, non-empty instructions, physical paths and file hashes. It does not claim a native App/IDE scanner or model-routing test. The standalone Antigravity CLI global path is outside this target.
- Linux adjusts the copied DCG plugin's PATH delimiter; the original live plugin and stored source identity stay unchanged.
- RINGKAS-only references map to `$HOME/Projects/RINGKAS`; the private project is not backed up. Animate's preserved upstream reference receives a copied companion RECIPES.md without modifying the source installation.
- Codex's sanitized `.codex/portable.config.toml` profile keeps the three reviewed MCP definitions and model preferences, excluding the main config, hook approvals, project trust and credentials. Capture can use the restored profile when main config has no MCP definitions.
- Ponytail 5.3.2 is a captured Codex/OpenCode runtime payload with its local marketplace, not a moving upstream Git registration. Unrelated host adapters and optional Claude band setup are not activated.
- Context7 and Playwright runtime packages are installed from captured npm manifests/lockfile with lifecycle scripts disabled. Playwright's Chromium and OS libraries remain separate local prerequisites.
- The portable OpenCode runner and isolated test environment use a dedicated XDG data directory; no pre-existing database/authentication directory is copied or migrated.

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
7. Bootstrap only target-home pinned runtimes and locked MCP packages, with unrelated lifecycle scripts disabled. Initialize captured OpenCode plugin dependencies before native startup. If Codex is installed, register the captured local Ponytail marketplace under the target CODEX_HOME; preserve unrelated main configuration. These generated Codex registrations/caches are outside snapshot rollback.
8. Reauthenticate services on the new device and restart OpenCode. Restore is not proof of credential validity or of availability of every remote model listed in preserved preferences.

## Verification gates before publication

- Payload/content-address identity and original-file preservation.
- Complete Windows and Linux disposable restore, real junction/symlink aliases, repeated previews/apply/bootstrap, complete rollback.
- Fresh OpenCode discovery of 50 names; descriptions and loaded bodies match the restored snapshot; paths remain in the sandbox.
- If Codex is available: its portable CLI profile, 50 portable skills and tools from ECC/Context7/Playwright are discovered without credentials, model calls or hook approval. app-server does not accept --profile, so verification checks CLI profile loading separately and uses its exact MCP values as app-server overrides.
- All 43 Antigravity core directories are physical, complete and valid after restore. Tests reject missing frontmatter, modified references, linked roots/children, broken links and alias-bearing manifests. Restore, repeated apply, recapture and rollback retain this contract.
- Real UI UX Pro Max data search and ECC memory save/read/doctor, custom MCP initialization/tools and handoff helper.
- Fresh model-driven frontend/debugging/handoff/backend routing tests with no skill names in those prompts.
- Adversarial tests for corruption, traversal, duplicate/prefix conflicts, redirected parents/state, credentials and preservation of newer work.
- Independent redacted secret scan before staging and again before pushing; inspect Git status, diff and recent history, then commit only intended files.

## Maintenance limits and manual setup

Python 3.11+/Git/Node 22+, Codex/Antigravity application installation, provider login, Context7 key, Codex hook approval, browser binaries/OS libraries, optional DCG/Graphify and private project checkouts remain local setup. Windows and model-driven routing evidence from previous snapshots is labelled historical. Native Windows Antigravity scanner and routing checks require the installed application; filesystem checks alone do not prove them.

Capture fails if required ECC binding is missing or a discovered skill has no approved mapping. Review mappings before adding external roots. Keep third-party licenses, inspect scripts before bootstrap, and use the pinned OpenCode version for equivalent discovery. Tool and model versions can select different skills from the same snapshot.
