# Portable OpenCode environment

An implemented backup of the **actual customized installation**, not a list of upstream skill URLs. It preserves 45 native OpenCode skills, optimized routing/descriptions, native variants, references, scripts, design databases, custom plugins, model preferences, and cross-harness alias relationships.

The snapshot is tested on Windows and Linux. It contains no provider authentication, remote MCP keys, browser sessions, or private memory records. A new device must authenticate locally.

## What is preserved

- The installed files from `.agents/skills`, `.config/opencode/skills`, `.opencode/skills`, `.claude/skills`, and retained Codex/Gemini/Cline variants and aliases.
- Global OpenCode routing and engineering rules, shared instructions, command adapters, plugins, source-license files, skill installation provenance, and non-secret model preferences.
- Original package manifests/locks for the plugin API and pinned runtime versions: OpenCode **1.18.35**, Agent Browser **0.38.2**, UI UX Pro Max CLI **2.15.0**, ECC Universal **2.2.3**.
- The **installed ECC memory code and required pure-JS dependency closure**, vendored as content blobs. The custom workspace-binding MCP adapter and handoff helper work without downloading ECC or activating its full skill/hook pack.
- SHA-256 identities for source bytes and snapshot bytes, including declared portability adaptations.

Inventory and validation evidence live in [`reports/`](reports/). The source environment was read, not reinstalled or changed.

## New laptop: restore

Install **Git, Python 3.10+ and Node.js 22+ with npm** first. Windows 11 uses NTFS junctions; Linux uses relative symbolic links. Log into GitHub locally if access to this repository requires it.

```text
git clone https://github.com/haikalthrq/ai-skill-portable.git
```

Open a terminal in the cloned repository. On Linux use `python3` instead of `python` below.

```text
python scripts/portable.py verify
python scripts/portable.py migrate
python scripts/portable.py migrate --apply
```

**Save the transaction ID printed by restore.** Restore writes no files without `--apply`; differing managed files cause a conflict before mutation. `--replace` explicitly permits replacement and creates exact private rollback copies first. Quit OpenCode and stop other writers before restore or rollback.

`migrate --apply` is the one-command restore: it performs prerequisite preflight, guarded file restore, pinned runtime bootstrap, and native verification. Its preview reports missing runtimes, required environment variables and local authentication. The lower-level `restore` and `bootstrap.py` commands remain available for separate inspection/testing.

Bootstrap installs only the pinned runtime tools into your home. It does **not** run `skills add`, Impeccable's installer, `uipro init`, or any skill update. The pinned plugin dependencies are initialized **before the first OpenCode startup**, preserving their existing manifests. ECC lifecycle scripts remain disabled; only the pinned OpenCode package's own binary setup is run.

Add the generated tool directory to PATH:

**PowerShell — current terminal:**
```powershell
$env:PATH = "$HOME\.local\share\opencode-portable\tools\node_modules\.bin;$env:PATH"
```

Add that same directory to your user PATH for future terminals.

**Linux shell:**
```sh
export PATH="$HOME/.local/share/opencode-portable/tools/node_modules/.bin:$PATH"
```

Put the export in your preferred shell profile for persistence. Then:

```text
python scripts/portable.py verify --home <your-home> --native
opencode auth login
```

Replace `<your-home>` with your actual user home, quoting spaces. All commands accept `--home` for a disposable or alternate profile. `--repo` precedes the action if selecting another repository path.

### Authentication and manual setup

1. **Model providers:** run `opencode auth login` on the new device. OAuth/API credentials are not in this repository.
2. **Context7:** supply `CONTEXT7_API_KEY` locally using a secret manager or local environment configuration. Its preserved header uses `{env:CONTEXT7_API_KEY}`. Never put the value in Git or a shell command saved to history. Restart OpenCode after setting it.
3. **ECC Memory:** no remote OAuth credential exists for the local vault. Its MCP process identifies as `opencode` and pins to the verified repository passed as `workspaceRoot`. The adapter/runtime configuration is restored; project trust and memory content are separate. No `.ecc` vault data or transcript is copied. Git-tracked team memory can travel with its own project repository.
4. **Browser work:** install Chrome/Chromium locally and use the platform's executable path. No browser profile, cookie store, or authentication state is restored.
5. **Optional CLIs:** DCG 0.6.7 and Graphify 0.9.5 are recorded dependencies for their specific workflows/plugins. Install their matching platform runtimes if used. OfficeCLI's original installation already fails with a missing .NET assembly; install a working OfficeCLI/.NET runtime on the new device if Office workflows are needed. Backup does not repair that live installation.
6. **Optional RINGKAS variant:** its project-specific references now resolve under `$HOME/Projects/RINGKAS`. Clone that project separately there if needed; its source/data are not included or exposed to ordinary OpenCode routing.

## Daily backup / update

From the original or successfully restored installation:

```text
python scripts/portable.py backup
python scripts/inventory_report.py
python scripts/portable.py verify
python -m unittest discover -s tests -v
python scripts/integration_test.py --native --bootstrap --report reports/windows-integration.json
```

Backup is idempotent: identical installed content keeps the snapshot ID and timestamp. It stages a new snapshot privately, checks content/credentials, and replaces the published snapshot only after capture succeeds. Capture fails rather than omit discovered out-of-allowlist skills or a missing required ECC integration. Custom external roots require an explicit reviewed mapping rather than arbitrary directory traversal.

The snapshot stores deduplicated blobs under `snapshot/blobs/`; `snapshot/manifest.json` maps them to home-relative destinations and aliases. This avoids Git's Windows symlink problems and saves repeated native-variant bytes. Blob hashes and manifest identity are validated before restore; installed user/project files are not fetched from upstream during restoration.

### Required pre-publication secret scan

```text
python scripts/fetch_gitleaks.py
python scripts/secret_scan.py --gitleaks .work/gitleaks/gitleaks.exe --report reports/secret-scan.json
```

On Linux the executable is `.work/gitleaks/gitleaks`. The scanner download is pinned to **Gitleaks 8.30.1** and verified against the official checksum. Local token/exact-source checks run in addition to independent Gitleaks defaults. Only Git internals and ignored private scratch/cache directories are excluded; **snapshot blobs are scanned**. Scan before staging or pushing, inspect the diff, then commit only the intended snapshot/code/docs/reports.

No automatic commit/push is performed by the backup scripts. Updating this repository always remains an explicit Git operation.

## Rollback

Preview and then apply using the saved restore transaction ID:

```text
python scripts/portable.py rollback <transaction-id>
python scripts/portable.py rollback <transaction-id> --apply
```

Rollback restores exact old bytes and original aliases, or removes newly restored files. It is idempotent and refuses observed newer changes. Journals and old bytes remain private in `$HOME/.local/state/opencode-portable/transactions/`: owner-only access on Linux and a restricted user DACL on Windows. Interrupted restores leave a prepared journal and attempt automatic rollback. Do not run concurrent editors/config writers during mutation; the scripts do not lock unrelated applications.

If OpenCode subsequently upgrades package manifests, rollback treats that as newer work and refuses to overwrite it. Bootstrap before first startup avoids the known initial automatic SDK rewrite.

## Verification

- `verify`: payload integrity and manifest/path safety, no destination changes.
- `verify --home ...`: rendered file hashes, all definitions/aliases and required local Markdown links.
- `verify --home ... --native`: fresh OpenCode discovery, exact names/descriptions/body content, and all native paths contained in the restored home.
- `integration_test.py --native --bootstrap`: complete disposable-HOME restore, two previews, repeated restore/bootstrap, real dataset search, ECC save/read/doctor, custom MCP calls, handoff helper and full rollback. It never applies restore to the original home.
- `routing_probe.py --home ...`: four real fresh model-driven sessions after local authentication: frontend, debugging, durable handoff, and backend-only.

Original-device QA can explicitly use `routing_probe.py --isolated-local-auth`: it borrows provider authentication only into a restricted, disposable OS temporary HOME, deletes it afterward, and publishes only skill names/counts. Credentials/transcripts never enter the snapshot or reports. Normal new-device restore cannot use that authentication.

Linux QA:
```text
docker build -t opencode-portable-test -f tests/Dockerfile .
docker run --rm -v <absolute-repo>:/repo:ro -v <absolute-report-directory>:/results opencode-portable-test
```

The scripts preserve instruction bodies; model-driven routing remains semantic selection, not a guaranteed OpenCode hard trigger. Package README contribution links omitted by upstream npm distributions are informational, not missing skill/runtime dependencies. See [MIGRATION-BRIEF.md](MIGRATION-BRIEF.md) for the implemented contract and maintenance boundaries.

Native verification uses a disposable Git workspace and removes it afterward. OpenCode may write its normal cache/state in the selected home; pure payload verification and restore previews do not write there. Rollback covers snapshot-managed files/aliases; isolated downloaded runtime caches remain in the tools prefix and can be removed separately if no longer needed.
