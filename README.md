# Portable Codex and OpenCode environment

A sanitized backup of the **installed, customized skills and integrations**, not a list of moving upstream URLs. The current snapshot restores **51 OpenCode discovery names** (50 captured skills plus one built-in), **51 portable Codex skills** (including Graphify and six Ponytail skills), and **41 directory aliases**. Descriptions, routing guidance, native variants, references, scripts, datasets and licenses are retained. Codex system skills and account-managed OpenAI plugins are supplied by Codex itself.

## What is preserved

- Ponytail **5.3.2**: six skills, Codex lifecycle hooks, OpenCode 1 adapter, commands, required assets and license. Bootstrap installs the captured local marketplace, not GitHub HEAD.
- Codex `portable` profile: **ECC Memory Vault**, **Context7**, **Playwright MCP**, and model preferences. Snapshot restore does not replace the main `~/.codex/config.toml`, project trust or hook approvals.
- Locked MCP runtimes: `@upstash/context7-mcp` **4.4.4**, `@playwright/mcp` **0.0.83**.
- Runtime pins: OpenCode **1.18.35**, Agent Browser **0.38.2**, UI UX Pro Max CLI **2.15.0**, ECC Universal **2.2.3**.
- Installed ECC memory code and pure-JS dependencies, without activating the full ECC pack.
- A dedicated OpenCode data directory that avoids incompatible databases from other versions.

**No API key, provider login, browser session, project source, transcript or memory record is included.** Context7 credentials are replaced by a required `CONTEXT7_API_KEY` environment variable.

This snapshot is verified on Linux. Windows and model-driven routing reports are explicitly **historical**, not evidence for the current snapshot. See [inventory](reports/inventory.json) and [Linux integration](reports/linux-integration.json).

## New machine: restore

Install **Git, Python 3.11+, Node.js 22+ and npm**. Install Codex separately for its integration. Authenticate GitHub locally if needed.

```sh
git clone https://github.com/haikalthrq/ai-skill-portable.git
cd ai-skill-portable
python3 scripts/portable.py verify
python3 scripts/portable.py migrate
python3 scripts/portable.py migrate --apply
```

On Windows use `python`. All actions accept `--home` for a disposable/alternate home; `--repo` precedes the action.

**Save the restore transaction ID.** Preview writes nothing to the target. Differing managed files cause a conflict before mutation. `--replace` explicitly permits replacement and stores exact private rollback copies. Stop configuration writers before restore/rollback.

Migration restores the snapshot, installs pinned runtimes and locked MCP packages, initializes existing OpenCode plugin dependencies, registers captured Ponytail when Codex is installed, and verifies native OpenCode discovery. It does not run `skills add`, Impeccable's installer or `uipro init`. Dependency lifecycle scripts stay disabled except OpenCode's pinned binary setup. After installing Codex, rerun `python3 scripts/bootstrap.py --apply` if needed.

### Codex

Add the installed runtime tool directory to your shell PATH, and persist it in your shell profile (or Windows user PATH). Node.js must also be available in non-interactive shells.

```sh
export PATH="$HOME/.local/share/opencode-portable/tools/node_modules/.bin:$PATH"
codex -p portable
```

Set `CONTEXT7_API_KEY` locally through your secret manager or environment configuration; never put its value in Git or a saved shell command. The portable profile forwards it to the pinned Context7 MCP runtime. Inspect registrations with `codex -p portable mcp list`.

Use `-p portable` explicitly: ordinary `codex` keeps your main configuration. Review/trust Ponytail hooks in `/hooks`, then start a new chat; approvals are intentionally not transferable. Skills include `$ponytail:ponytail-review` and `$ponytail:ponytail-help`.

Bootstrap registers the captured local Ponytail marketplace in the target Codex main configuration while retaining other entries. Those generated registration/cache changes are separate from snapshot rollback.

### OpenCode

Use the portable runner so this pinned version has its own database and authentication directory:

```sh
python3 scripts/portable.py run -- auth login
python3 scripts/portable.py run
```

The runner changes only the child's `XDG_DATA_HOME` to `~/.local/share/opencode-portable/data` and adds its tool directory to PATH. Other OpenCode databases remain untouched. `run --home` selects the executable/data directory; set the target's normal HOME/XDG variables too when using a different home interactively.

Ponytail uses OpenCode 1's `plugin` key and captured `.mjs` adapter, with ruleset injection and six `/ponytail` commands. Restart an existing OpenCode process after changes.

### Browser and other local prerequisites

Playwright runtime installation does **not** install browser binaries or Linux system libraries:

```sh
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install chromium
# Linux: may require administrator access.
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install-deps chromium
```

Codex launches Chromium headless with an isolated profile. Cookies/authenticated profiles are not restored.

- **ECC:** pass the current absolute Git root as `workspaceRoot`. Each MCP process pins to one verified repository. Harnesses share its `.ecc/memory/`; project trust and memory remain local.
- **Context7:** OpenCode retains its remote MCP; Codex uses its pinned local runtime. Both use a locally supplied key; restore is not proof of credential validity.
- **Optional tools:** DCG 0.6.7, Graphify 0.9.5 and OfficeCLI are not installed automatically. OfficeCLI was already broken in the source environment; only its skill is preserved.
- **Optional RINGKAS references:** resolve under `$HOME/Projects/RINGKAS`. Clone separately if needed; project source/data are not included.

## Update this backup

Run from the successfully restored installation, with portable tools on PATH:

```sh
python3 scripts/portable.py backup
python3 scripts/inventory_report.py
python3 scripts/portable.py verify
python3 -m unittest discover -s tests -v
python3 scripts/integration_test.py --native --bootstrap --report reports/linux-integration.json
```

Capture reads installed Codex main MCP definitions to produce the safe portable profile. It requires all three reviewed MCPs and the local Ponytail payload, and fails rather than silently dropping an out-of-allowlist skill or required integration. Project trust, hook decisions, unrelated Codex configuration and credentials are excluded. Only Ponytail's Codex/OpenCode runtime payload is captured; unrelated host adapters, tests and optional Claude band setup are not activated.

The manifest maps home-relative destinations to SHA-256 blobs. Identical capture preserves snapshot ID/time. Capture stages privately and publishes only after validation; source files are read, not modified. Adding another plugin/skill source needs a reviewed explicit mapping.

### Scan before publishing

```sh
python3 scripts/fetch_gitleaks.py
python3 scripts/secret_scan.py --gitleaks .work/gitleaks/gitleaks --report reports/secret-scan.json
```

On Windows use `gitleaks.exe`. Gitleaks **8.30.1** is checksum-verified. Local patterns and exact removed-secret detection supplement default scanner rules; **snapshot blobs are scanned**. Findings do not print credential values. Inspect the diff, then commit only intended code/snapshot/docs/sanitized reports. Backup never commits or pushes automatically.

## Verification and rollback

- `verify`: manifest/path safety and every blob's integrity; no target writes.
- `verify --home <home>`: rendered bytes, definitions, aliases and required local Markdown links.
- `verify --home <home> --native`: fresh OpenCode names, descriptions, loaded bodies and contained paths.
- `integration_test.py --native --bootstrap`: disposable HOME with spaces; repeated preview/restore/bootstrap; real dataset search; ECC save/read/doctor, MCP binding and handoff helper; native discovery; one-command migration; full snapshot rollback. If Codex is installed, checks its portable CLI profile, all 51 portable skills and tool discovery from three MCPs, without provider credentials or hook approval. Does not test live Context7 queries, browser launch or model-driven routing.
- `routing_probe.py --home <home>`: optional real model-driven routing after local authentication. Semantic selection is not a guaranteed hard trigger. Historical reports retain their original snapshot identity.

Preview and apply rollback using the saved transaction:

```sh
python3 scripts/portable.py rollback <transaction-id>
python3 scripts/portable.py rollback <transaction-id> --apply
```

Rollback refuses newer edits and restores old bytes/aliases or removes newly restored content. Journals stay private under `~/.local/state/opencode-portable/transactions/`. Downloaded runtimes/browser caches, Codex-generated marketplace/config/cache registrations, OS packages and OpenCode data are outside snapshot rollback. Check for local work before removing them. Windows junction handling is retained, but this revision needs a fresh Windows integration run.

See [MIGRATION-BRIEF.md](MIGRATION-BRIEF.md) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
