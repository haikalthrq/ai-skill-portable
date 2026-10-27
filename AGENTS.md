# Agent instructions

For a request to install or migrate this environment, read [INSTALL.md](INSTALL.md) and execute its workflow. A user request to install authorizes the ordinary installation steps; do not stop at providing commands or ask for redundant confirmation.

For maintenance, read [MIGRATION-BRIEF.md](MIGRATION-BRIEF.md). Keep installed source bytes, pinned dependencies, secret exclusion, read-only preview, conflict protection and rollback intact. Do not run `backup` as an installation step: it replaces the published snapshot with the current machine's state.

Never export credentials, browser sessions, trust decisions, private projects or vault contents. Do not print secret-bearing config or MCP-list JSON from an existing user profile. Use disposable homes for integration tests; publish only sanitized evidence and distinguish current from historical verification.
