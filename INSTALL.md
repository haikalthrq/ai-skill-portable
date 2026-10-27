# Installation runbook for coding agents

This is an execution workflow for an agent with terminal and network access. When the user asks to install this repository, **perform the steps**; do not hand them a list of commands. Use the existing scripts, retain the captured versions, and finish every independent step while a required human action is pending.

The target is the user's home on the machine running your terminal, not automatically the laptop displaying an SSH session. Confirm the target from session context; ask only if it is genuinely ambiguous. Default to both Codex and OpenCode unless the user narrows the request. Explain that snapshot restore also retains existing Claude/Gemini/Cline variants and global instructions; it does not install those applications.

## 1. Inspect the machine and checkout

Determine OS, architecture, target home, shell, installed runtimes, existing Codex/OpenCode configuration, and relevant running configuration writers. Do not dump config values, environment variables or login files into output. Do not terminate the user's editor, server or session without authorization.

Clone `https://github.com/haikalthrq/ai-skill-portable.git` into a normal persistent directory and work from that checkout. If it already exists, inspect its remote, branch and local changes first. Do not overwrite local work or reuse an unrelated directory. Fetch updates and fast-forward only a clean, appropriate checkout. Record the commit being installed.

Read `README.md`, this file and the entry-point scripts before executing them. This repository is a snapshot restorer, not a request to reinstall all upstream skills at their latest revisions.

## 2. Resolve prerequisites yourself

Check actual versions, not just command existence: **Python 3.11+, Node.js 22+, npm and Git**. Check `codex` when Codex integration is requested. On Windows, find the usable Python launcher and resolve npm/Codex executable shims. Use `python` or `python3` as appropriate throughout the workflow.

Install missing prerequisites using an existing version manager, the OS package manager or the software's official installation instructions. Prefer an existing compatible runtime or a user-scoped installation. Avoid changing unrelated global runtime versions or installing a full ECC skill/hook pack. Ensure the selected Node works in a non-interactive subprocess too, not only an interactive version-manager shell.

If administrator rights or an OS approval are required and unavailable, request that specific action and explain which dependency needs it. Do not bypass permissions. Continue independent steps that can run safely. If a prerequisite cannot be installed, report its exact name/version requirement and mark dependent steps blocked rather than starting a partial migration blindly.

## 3. Verify and preview before writing

Run these from the checkout (adapt the Python executable to the platform):

```sh
python3 scripts/portable.py verify
python3 scripts/portable.py migrate
```

For an explicitly selected alternate home, pass the same absolute `--home` to every target-dependent command. Inspect the JSON: snapshot verification must pass; prerequisites must exist at supported versions; conflicts must be empty. Preview itself must not write target files.

When there are conflicting managed files, inspect the relevant differences without exposing credentials, explain the exact files that would change, and obtain a specific replacement decision. Do not infer permission to replace existing user rules or configuration from the general install request. Use `--replace` only when that replacement is authorized; the restorer keeps private rollback copies. Never delete files or bypass a symlink/containment rejection to make preview pass.

## 4. Apply, bootstrap and preserve recovery information

```sh
python3 scripts/portable.py migrate --apply
```

Inspect both the exit code and JSON `ok`, including bootstrap and verification results. Save the restore transaction ID privately and include it in the final installation summary. Do not discard it when bootstrap fails. On an idempotent rerun there may be no new transaction: retain the original ID.

If a runtime download or initialization fails, identify and repair that dependency and rerun `scripts/bootstrap.py --apply`, followed by verification. Do not rerun upstream skill installers or use `backup` to hide drift. If necessary, preview rollback using the saved ID; do not overwrite newer work or remove caches/data outside snapshot rollback.

Codex should be installed before migration when requested. If it was installed later, rerun:

```sh
python3 scripts/bootstrap.py --apply
```

Bootstrap registers Ponytail from the captured local marketplace in the target Codex main config while preserving unrelated entries. The three MCP connections and model preferences live in `~/.codex/portable.config.toml`, selected with `codex -p portable`. Do not silently overwrite the main config to make the profile the default.

## 5. Finish environment and browser setup

Add `~/.local/share/opencode-portable/tools/node_modules/.bin` to the appropriate user PATH, idempotently, preserving the existing shell/profile contents. Make the supported Node and Codex executable available to fresh non-interactive subprocesses. For Windows use user environment settings; for POSIX use the user's actual shell profile. Do not assume editing `.bashrc` alone fixes a desktop application's environment.

Install Chromium using the locked Playwright package:

```sh
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install chromium
```

On Linux install its OS libraries as needed:

```sh
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install-deps chromium
```

Adapt shell quoting and path syntax to the platform. These commands operate on the installed pinned runtime; do not upgrade Playwright or disable the browser sandbox as a generic workaround. Request actual missing administrator access if needed. Browser downloads and OS packages are outside snapshot rollback.

For Context7, check whether `CONTEXT7_API_KEY` is available **without printing it**. Reuse a credential the user already authorized, or use their normal secret manager/local credential-entry mechanism. Do not request it in a public issue, commit it, print it, put it in process arguments or save it in shell history. The portable profile forwards this environment variable; do not put a literal key in the captured profile. After environment changes, desktop processes may need restarting. Without a usable key, distinguish an MCP schema connection from a successful authenticated documentation query.

## 6. Verify the installed result

Run and inspect:

```sh
python3 scripts/portable.py verify --home <absolute-target-home> --native
python3 scripts/codex_verify.py --home <absolute-target-home>
```

The first checks the restored OpenCode snapshot and discovery. The second checks the actual Codex portable CLI profile, portable skills and tools exposed by ECC, Context7 and Playwright. Run the Codex check only when Codex is installed. Read expected counts from the manifest rather than hard-coding future versions. The verifier does not approve hooks, invoke a model, query live docs or launch a browser.

Then perform functional smoke checks through available MCP tools or a local MCP client using the installed definitions:

- **ECC:** start a fresh local MCP process from a disposable Git repository, initialize/list tools, then run `memory_doctor` with `scopes: ["project"]` and that repository's absolute `workspaceRoot`. Do not try to rebind an existing MCP process from another repository, write test memories into the user's real project or scan personal memory.
- **Context7:** resolve a public library and retrieve a small documentation result. Never include the key in test logs. If authentication/rate limits block this, report that separately from server discovery.
- **Playwright:** launch configured headless/isolated Chromium, navigate to a local synthetic page, inspect its snapshot, then close the session you created. This proves the browser binaries and OS libraries work without using the user's browsing profile.

If tool refresh is required, use a local client or installed runtime for the test rather than claiming a tool call happened. If no supported test path is available, report the functional test as pending. A discovery-only check is not proof of full readiness.

Do not run the full maintainer integration suite against the live user home. It already uses a disposable home when explicitly run; normal installation requires the targeted checks above.

## 7. Complete the remaining human gates

Finish all automated work before asking the user for remaining actions. Do not request a second generic installation approval. Only these concrete gates may remain:

- Provider/GitHub login that needs the user's browser, account consent or MFA. Use the portable OpenCode runner for its login: `python3 scripts/portable.py run -- auth login`. Do not import another installation's auth/database. Follow the provider login flow for Codex if needed.
- Secret entry through the user's local mechanism.
- Ponytail hook review/trust in Codex `/hooks` and a fresh chat. Do not edit approval/trust storage or bypass hook trust.
- An OS administrator prompt or a decision on exact conflicting files.

If a login command must be interactive, start or present that specific supported flow; do not claim credentials are valid because configuration exists. Do not forcibly restart the session you are using to perform the installation.

End with a concise report: checkout commit; selected home/profile; installed components; exact verification outcomes and pending tests; transaction ID and rollback command; remaining user actions. Distinguish **installed**, **discovered**, and **functionally verified**. For later use, provide `codex -p portable` and `python3 scripts/portable.py run` as launch commands, not as unfinished installation work.
