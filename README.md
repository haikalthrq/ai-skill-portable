# Portable Codex, OpenCode and Google Antigravity environment, with a Claude port

Back up and restore skills for Codex, OpenCode and Google Antigravity, plus the existing Codex/OpenCode plugins and MCP connections. The snapshot keeps customized instructions, scripts, datasets, licenses and routing descriptions. `scripts/claude_port.py` additionally builds Claude Code and Claude app copies of the portable skills (see [Use Claude](#use-claude)).

The snapshot contains 44 unique active core skills. Antigravity receives those 44 skills as physical directories. Codex has 50 portable skills (the core set and six Ponytail skills); OpenCode has 51 skill names (the core set, Ponytail and one built-in). Codex supplies its own system skills and account-managed OpenAI plugins. The retired `caveman`, `officecli` and `graphify` skills are excluded, and `backup` keeps them out of future captures.

## Install with an agent

Give this prompt to a coding agent with terminal and network access:

```text
Install https://github.com/haikalthrq/ai-skill-portable for Codex, OpenCode
and Google Antigravity
on this machine. Clone the repository, read AGENTS.md and INSTALL.md, and
complete the installation and verification. Install missing prerequisites,
MCP runtimes, Chromium and browser dependencies.
Report what passed and what remains blocked.
```

[INSTALL.md](INSTALL.md) tells the agent which commands to run and how to check the result. Account login, secret entry, hook trust and file conflicts may still need your input.

## Included versions

| Component | Version |
|---|---|
| OpenCode | 1.18.35 |
| Ponytail | 5.3.2, all six skills |
| ECC Universal | 2.2.3, memory code and required JavaScript dependencies |
| Context7 MCP | 4.4.4 |
| Playwright MCP | 0.0.83 |
| Agent Browser | 0.38.2 |
| Agent Desktop | 1.1.0 |
| UI UX Pro Max CLI | 2.15.0 |

Bootstrap uses captured Ponytail files and locked npm packages. It leaves existing skill versions intact. The Codex `portable` profile includes ECC Memory Vault, Context7, Playwright and model preferences. OpenCode uses its captured configuration and a separate data directory. Restore writes Antigravity files through the same rollback journal.

Credentials, browser sessions, private projects, transcripts, memory records and trust approvals stay on the source machine. Supply `CONTEXT7_API_KEY` locally after restore.

## Manual installation

Install Git, Python 3.11+, Node.js 22+ and npm. Install Codex if you want its integration, then run:

```sh
git clone https://github.com/haikalthrq/ai-skill-portable.git
cd ai-skill-portable
python3 scripts/portable.py verify
python3 scripts/portable.py migrate
python3 scripts/portable.py migrate --apply --antigravity
```

Use `python` on Windows. Preview writes nothing to the target. Resolve reported conflicts before applying; use `--replace` only after approving the affected files. Stop configuration writers and save the restore transaction ID for rollback.

Pass `--home` for an alternate home and place `--repo` before the action when selecting another checkout. If you install Codex later, rerun `python3 scripts/bootstrap.py --apply`.

### Use Antigravity

Install the Antigravity App or IDE, then run the migration above. Current snapshots always include its target; `--antigravity` requires that target explicitly. Bootstrap also accepts `--antigravity` to check that the snapshot includes it. It does not install Antigravity itself.

Global skills live at `~/.gemini/config/skills/<skill>/SKILL.md`. Every restored skill is a physical directory, including its scripts and references. Windows Antigravity does not follow NTFS junctions/reparse points, so this target never uses junctions or symlinks on any OS. An existing linked target blocks restore; preserve it and resolve the reported path before retrying. `--replace` does not bypass this check.

Start a new Antigravity conversation after restore. It reads skill names and descriptions from frontmatter and automatically loads relevant instructions for your prompt. You can also use `/<skill-name>`. See [Google's skill documentation](https://antigravity.google/docs/skills?tab=ide). This target covers the App/IDE global directory; the separate Antigravity CLI has a different global path.

### Use Claude

Restore already gives Claude Code part of this environment: it writes `~/.claude/CLAUDE.md`, a native `impeccable` copy and 18 `~/.claude/skills/<skill>` links that point at the original `~/.agents/skills/<skill>` folders. Those are the unmodified Codex/OpenCode skills.

`scripts/claude_port.py` builds Claude-compatible copies of all 50 portable skills straight from the snapshot. It reads only `snapshot/` and writes nothing outside the output folder:

```sh
python3 scripts/claude_port.py          # .work/claude/skills/<skill>/ for Claude Code
python3 scripts/claude_port.py --zip    # also .work/claude/upload/<skill>.zip for the Claude app
```

For Claude Code, put the folders from `.work/claude/skills/` into `~/.claude/skills/`. If a name already exists there, move it aside first: copying onto one of the restore links would write into the original skill it points to. For the Claude app, upload the zips under Settings → Capabilities → Skills, choosing only the skills you use, since many design skills overlap.

The port moves keys Claude does not accept into `metadata`, removes angle brackets from descriptions, rewrites `~/.agents`, `~/.opencode` and `~/.config/opencode` skill paths to `~/.claude/skills`, drops Codex `agents/openai.yaml`, and adds a short Codex/OpenCode → Claude tool map to skills that still name another platform's tools. Upload zips keep only the keys the Claude app accepts; Claude Code copies keep `argument-hint` and `disable-model-invocation`.

Skills that call a runtime still need it: Node.js for `impeccable`, Python 3 for `ui-ux-pro-max`, the `agent-browser`/`agent-desktop` CLIs, Context7 for `context7-mcp`/`find-docs`, and `ecc-universal` for `unified-memory`/`cross-harness-handoff`. Claude cannot generate raster images, so the image-first step of `image-to-code` and both `imagegen-frontend-*` skills reports that and falls back to written specs.

### Desktop automation

Bootstrap installs the pinned Agent Desktop CLI. Put the runtime directory on PATH so Codex, OpenCode and Antigravity can call it from the shared skill. Codex prefers it for Windows desktop tasks and keeps native browser tools for browser verification. Version 1.1.0 integrates through the CLI.

### Start Codex

Add the runtime tools to your user PATH and keep Node available in non-interactive shells:

```sh
export PATH="$HOME/.local/share/opencode-portable/tools/node_modules/.bin:$PATH"
codex -p portable
```

Persist PATH in your shell profile or Windows user environment. Set `CONTEXT7_API_KEY` through your secret manager or local environment settings. Keep its value out of Git, command arguments and shell history.

Use `-p portable` to select the restored MCP profile. Review Ponytail hooks in `/hooks`, trust them, then start a new chat. Commands include `$ponytail:ponytail-review` and `$ponytail:ponytail-help`.

Snapshot restore leaves the main Codex config alone. Bootstrap adds the local Ponytail marketplace to it while preserving other entries.

### Start OpenCode

```sh
python3 scripts/portable.py run -- auth login
python3 scripts/portable.py run
```

The runner uses `~/.local/share/opencode-portable/data` for this version's database and login, leaving other OpenCode databases untouched. `run --home` selects the executable and data directory; set HOME/XDG variables too when running as a different home.

Ponytail adds its rules and six `/ponytail` commands through the OpenCode 1 adapter. Restart an existing process to load config changes.

### Install the browser

```sh
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install chromium
# Linux only; may require administrator access.
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install-deps chromium
```

Playwright runs Chromium headless with an isolated profile. Adapt quoting to your shell.

## Verify the installation

```sh
python3 scripts/portable.py verify --home "/absolute/target/home" --native --antigravity
python3 scripts/codex_verify.py --home "/absolute/target/home"
```

Use your target's absolute path. The first command checks OpenCode discovery plus Antigravity's physical files, frontmatter and hashes. Antigravity checks also run automatically for snapshots that include it. The second checks the Codex profile, skills and MCP tools. These checks do not test live documentation queries, browser launch, provider login or Antigravity's native scanner and model routing.

Compare the snapshot ID in the [inventory](reports/inventory.json) with each integration report. Reports from earlier snapshots, including model-driven routing evidence, are historical. Right now that applies to `linux-integration.json`, `windows-integration.json`, `restored-routing.json` and `review-summary.json`: each names an earlier snapshot, so they predate the Graphify removal and need a rerun on real machines to refresh. `secret-scan.json` and `inventory.json` match the current snapshot.

ECC requires the current Git root as `workspaceRoot` and binds each MCP process to one repository. Context7 uses a remote server in OpenCode and a pinned local runtime in Codex. The DCG runtime requires separate setup. Optional RINGKAS references point to `$HOME/Projects/RINGKAS`, which you must clone separately.

## Update and publish the backup

From a restored installation with portable tools on PATH:

```sh
python3 scripts/portable.py backup
python3 scripts/inventory_report.py
python3 scripts/portable.py verify
python3 -m unittest discover -s tests -v
python3 scripts/integration_test.py --native --bootstrap --report reports/linux-integration.json
python3 scripts/fetch_gitleaks.py
python3 scripts/secret_scan.py --gitleaks .work/gitleaks/gitleaks --report reports/secret-scan.json
```

Use `gitleaks.exe` on Windows. The scanner download is checksum-verified, and scans include snapshot blobs. Inspect the diff before committing or pushing.

Capture requires all three Codex MCP definitions and the local Ponytail files. It rejects unknown skill roots and missing required integrations. Identical captures keep the snapshot ID and timestamp. Backup reads source files, validates a staged snapshot, and replaces the old snapshot only after validation. It never commits or pushes.

## Rollback

```sh
python3 scripts/portable.py rollback <transaction-id>
python3 scripts/portable.py rollback <transaction-id> --apply
```

Rollback restores old files and aliases or removes newly restored content. It refuses newer edits and keeps private journals under `~/.local/state/opencode-portable/transactions/`.

Downloaded runtimes, browser caches, OS packages, Codex-generated registrations and OpenCode data are outside snapshot rollback. Check for local work before removing them.

Read [MIGRATION-BRIEF.md](MIGRATION-BRIEF.md) for the preservation contract and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for sources and licenses.
