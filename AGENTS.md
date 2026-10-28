# Agent instructions

For installation or migration, follow [INSTALL.md](INSTALL.md) and execute the steps. The install request authorizes ordinary setup; ask only for a required user action or a decision about conflicting files.

For maintenance, read [MIGRATION-BRIEF.md](MIGRATION-BRIEF.md). Preserve installed source bytes, pinned dependencies, secret exclusion, preview, conflict checks and rollback. Keep `backup` out of installation: it replaces the published snapshot with the current machine's state.

Support Codex, OpenCode and Google Antigravity App/IDE. Antigravity global skills belong at `.gemini/config/skills/<skill>/SKILL.md` under the target home. Restore them as physical directory copies with their supporting files on every OS. Windows Antigravity does not follow junctions/reparse points. Reject linked destinations, including with `--replace`, and preserve their targets. Check frontmatter, file hashes and physical directories; report native scanner/routing tests separately.

The active core contains 43 unique skills. Exclude retired `caveman` and `officecli` content. Report Graphify, Ponytail and OpenCode's built-in separately from the core count.

Keep credentials, browser sessions, trust decisions, private projects and vault contents out of the repository and logs. Existing config and MCP-list JSON can contain secrets. Use disposable homes for integration tests and label historical test results.
