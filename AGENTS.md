# Agent instructions

For installation or migration, follow [INSTALL.md](INSTALL.md) and execute the steps. The install request authorizes ordinary setup; ask only for a required user action or a decision about conflicting files.

For maintenance, read [MIGRATION-BRIEF.md](MIGRATION-BRIEF.md). Preserve installed source bytes, pinned dependencies, secret exclusion, preview, conflict checks and rollback. Keep `backup` out of installation: it replaces the published snapshot with the current machine's state.

Keep credentials, browser sessions, trust decisions, private projects and vault contents out of the repository and logs. Existing config and MCP-list JSON can contain secrets. Use disposable homes for integration tests and label historical test results.
