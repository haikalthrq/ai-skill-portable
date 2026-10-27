# Portable Codex and OpenCode environment

Back up and restore the installed skills, plugins and MCP connections for Codex and OpenCode. The snapshot keeps their customized instructions, scripts, datasets, licenses and routing descriptions.

It contains 51 portable Codex skills, 51 OpenCode skill names (including one built-in), and 41 directory aliases. Codex supplies its own system skills and account-managed OpenAI plugins.

## Install with an agent

Give this prompt to a coding agent with terminal and network access:

```text
Install https://github.com/haikalthrq/ai-skill-portable for Codex and OpenCode
on this machine. Clone the repository, read AGENTS.md and INSTALL.md, and
complete the installation and verification. Install missing prerequisites,
MCP runtimes, Chromium and browser dependencies. Preserve existing config,
sessions and data. Keep secrets out of the repository and logs.
Ask me only for required login, secret entry, hook approval, unavailable
administrator access, or a decision about conflicting files.
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
| UI UX Pro Max CLI | 2.15.0 |

Bootstrap uses captured Ponytail files and locked npm packages. It leaves existing skill versions intact. The Codex `portable` profile includes ECC Memory Vault, Context7, Playwright and model preferences. OpenCode uses its captured configuration and a separate data directory.

Credentials, browser sessions, private projects, transcripts, memory records and trust approvals stay on the source machine. Supply `CONTEXT7_API_KEY` locally after restore.

## Manual installation

Install Git, Python 3.11+, Node.js 22+ and npm. Install Codex if you want its integration, then run:

```sh
git clone https://github.com/haikalthrq/ai-skill-portable.git
cd ai-skill-portable
python3 scripts/portable.py verify
python3 scripts/portable.py migrate
python3 scripts/portable.py migrate --apply
```

Use `python` on Windows. Preview writes nothing to the target. Resolve reported conflicts before applying; use `--replace` only after approving the affected files. Stop configuration writers and save the restore transaction ID for rollback.

Pass `--home` for an alternate home and place `--repo` before the action when selecting another checkout. If you install Codex later, rerun `python3 scripts/bootstrap.py --apply`.

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
python3 scripts/portable.py verify --home "/absolute/target/home" --native
python3 scripts/codex_verify.py --home "/absolute/target/home"
```

Use your target's absolute path. The first command checks OpenCode files, aliases and discovered skills. The second checks the Codex profile, skills and MCP tools. Neither tests live documentation queries, browser launch, provider login or model routing. The agent runbook includes functional MCP checks.

The current snapshot passed Linux integration tests. Windows and model-routing reports are marked historical and need fresh runs. See the [inventory](reports/inventory.json) and [Linux report](reports/linux-integration.json).

ECC requires the current Git root as `workspaceRoot` and binds each MCP process to one repository. Context7 uses a remote server in OpenCode and a pinned local runtime in Codex. DCG, Graphify and OfficeCLI runtimes require separate setup; the source OfficeCLI runtime was already broken. Optional RINGKAS references point to `$HOME/Projects/RINGKAS`, which you must clone separately.

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
