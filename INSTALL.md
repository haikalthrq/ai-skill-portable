# Installation guide for agents

Complete the installation when the user asks for it. Run the commands, check the results, and finish independent work while waiting for required user input. Keep the captured versions.

## 1. Check the machine and checkout

Identify the OS, architecture, shell, target home, installed runtimes and existing Codex/OpenCode config. The target is the machine running your terminal; an SSH session may target a different machine from the user's laptop. Use session context and ask only if the target is unclear.

Install both Codex and OpenCode unless the user narrows the request. Restore also copies Claude/Gemini/Cline skill variants and global instructions. It does not install those applications.

Clone `https://github.com/haikalthrq/ai-skill-portable.git` into a persistent directory. For an existing checkout, inspect its remote, branch and local changes before fetching. Fast-forward a clean checkout; preserve local work. Record the commit being installed.

Read `README.md`, this guide and the entry-point scripts. Check for active configuration writers. Keep credentials and config values out of output, and leave the user's editor, server and sessions running unless stopping them is authorized.

## 2. Install missing prerequisites

Check versions: Python 3.11+, Node.js 22+, npm and Git. Install Codex before migration when requested. On Windows, find a working Python launcher and resolve npm/Codex executable shims. Use `python` or `python3` as appropriate below.

Use an existing compatible runtime, a version manager, the OS package manager or official installation instructions. Prefer user-scoped installs and preserve unrelated global versions. Check that Node works in a non-interactive subprocess. Install the ECC runtime through bootstrap; leave its full skill/hook pack disabled.

If a dependency needs unavailable administrator access or OS approval, request that specific action. Continue independent work. Report the missing version and block dependent steps if you cannot install it.

## 3. Verify and preview

From the checkout:

```sh
python3 scripts/portable.py verify
python3 scripts/portable.py migrate
```

Pass the same absolute `--home` to every target-dependent command when using an alternate home. Check the JSON: verification must pass, prerequisites must meet the version requirements, and conflicts must be empty. Preview must leave target files untouched.

For conflicting files, inspect the differences without exposing credentials. Show the user which files would change and request a replacement decision. A general install request does not authorize replacing existing user rules or config. Use `--replace` only with that approval; the restorer saves private rollback copies. Preserve symlink and path-containment checks.

## 4. Apply and save the transaction ID

```sh
python3 scripts/portable.py migrate --apply
```

Check the exit code and JSON `ok`, including bootstrap and verification results. Save the transaction ID privately and include it in the final report, even if bootstrap fails. An unchanged rerun may have no new transaction; retain the original ID.

If a download or runtime fails, repair that dependency, then rerun bootstrap and verification:

```sh
python3 scripts/bootstrap.py --apply
```

Run this again if Codex was installed after migration. Preserve installed skills; do not run upstream skill installers or `backup` during installation. If rollback is needed, preview it with the saved ID and preserve newer work and data outside snapshot rollback.

Bootstrap registers the captured Ponytail marketplace in the target Codex main config, preserving other entries. MCP connections and model preferences live in `~/.codex/portable.config.toml`, selected by `codex -p portable`. Keep the user's main config and default profile intact.

## 5. Set PATH, browser dependencies and credentials

Add `~/.local/share/opencode-portable/tools/node_modules/.bin` to the user PATH without duplicating entries or replacing existing profile content. Use the user's shell profile on POSIX or user environment settings on Windows. Check Node and Codex in a fresh non-interactive subprocess. Desktop applications may need restarting to pick up environment changes.

Install Chromium from the locked Playwright package:

```sh
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install chromium
```

On Linux, install its OS libraries as needed:

```sh
node "$HOME/.local/share/codex-mcp/node_modules/playwright/cli.js" install-deps chromium
```

Adapt quoting and paths to the platform. Request missing administrator access when required. Keep the pinned Playwright version and browser sandbox settings. Browser downloads and OS packages are outside snapshot rollback.

Check for `CONTEXT7_API_KEY` without printing it. Reuse an authorized credential or ask the user to enter it through their local secret mechanism. Keep it out of public issues, Git, logs, process arguments and shell history. The portable profile forwards the environment variable; never place a literal key in that profile.

## 6. Verify the result

```sh
python3 scripts/portable.py verify --home "/absolute/target/home" --native
python3 scripts/codex_verify.py --home "/absolute/target/home"
```

Replace the quoted path with the selected home. The first command checks restored OpenCode files and skill discovery. The second checks the Codex profile, skills and tools from ECC, Context7 and Playwright. Run the Codex check when Codex is installed. Read expected counts from the manifest.

These commands leave hook approvals, model calls, live docs queries and browser launch untested. Follow them with functional MCP checks using available tools or a local client:

- **ECC:** start a fresh MCP process from a disposable Git repository. Initialize it, list tools, and call `memory_doctor` with `scopes: ["project"]` and that repository's absolute `workspaceRoot`. Leave the user's project and personal memory untouched. An existing process bound to another repository must stay bound there.
- **Context7:** resolve a public library and retrieve a small documentation result. Report authentication or rate-limit failures separately from server discovery. Keep the key out of logs.
- **Playwright:** launch configured headless, isolated Chromium, open a local synthetic page, inspect its snapshot, and close your session. Use the isolated profile rather than the user's browsing profile.

If this session has not loaded the new tools, test through a local MCP client or the installed runtime. If that is unavailable, mark the functional check pending. Report discovery and functional checks separately.

Use these targeted checks for installation. The maintainer integration suite tests a disposable home and is not a replacement for checking the user's installed result.

## 7. Finish required user actions

Complete automated work before requesting remaining actions. Ask only for a specific unresolved requirement:

- Provider/GitHub login requiring a browser, consent or MFA. Start the supported interactive flow. OpenCode login uses `python3 scripts/portable.py run -- auth login`; preserve other installations' auth and databases. Use Codex's provider login flow when needed.
- Secret entry through the user's local mechanism.
- Ponytail hook review and trust in Codex `/hooks`, followed by a fresh chat. Leave trust storage and approval checks intact.
- Missing administrator access or approval to replace specific conflicting files.

Keep the installation session running until its work is complete. Config presence alone does not prove credentials work.

Report the checkout commit, target home/profile, installed components, checks passed or pending, transaction ID, rollback command and remaining user actions. Distinguish installed, discovered and functionally verified components. Give `codex -p portable` and `python3 scripts/portable.py run` as launch commands for later use.
