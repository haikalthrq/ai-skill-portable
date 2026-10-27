# Third-party source and notices

This is a personal environment snapshot. It does not relicense captured third-party material. Original notices, license declarations, installed package metadata and the retained `skill-source-licenses` files remain authoritative inside the snapshot. Content hashes identify the installed copies, not merely upstream HEAD.

Principal sources:

- Impeccable: https://github.com/pbakaus/impeccable — installed 3.9.1 provider variants and optimized shared workflow, Apache-2.0 declaration retained.
- Taste skills: https://github.com/Leonxlnx/taste-skill — installed/optimized variants and preserved original references; upstream MIT notice.
- UI UX Pro Max: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill — official OpenCode installation from CLI 2.15.0, including databases/search code and catalog/font license metadata; upstream MIT notice.
- Emil skills: https://github.com/emilkowalski/skills — installed animate, emil-design-eng and conditional pick-ui-library copies. No additional license grant is invented here.
- Matt Pocock skills and supporting engineering workflows: origins/revisions and available original license copies are retained in the installed source inventory and source-license subtree.
- ECC Universal: https://github.com/affaan-m/ECC — installed 2.2.3 memory implementation and its required installed dependency closure. The original ECC license and Ajv/dependency notices are captured. No full ECC skill/agent/hook pack is activated by restore.
- Ponytail: https://github.com/DietrichGebert/ponytail — installed 5.3.2 Codex/OpenCode runtime payload, six skills, shared hooks, native adapter/commands, required icons and MIT license. Original source commit: 09c434ab73ca43761c5d8b0c5d341926c2fba710. Other host adapters and optional Claude band activation are not registered.
- Context7: https://github.com/upstash/context7 — MCP runtime 4.4.4, pinned in the captured npm lockfile; fetched by bootstrap, not vendored as node_modules. API keys remain local.
- Playwright MCP: https://github.com/microsoft/playwright-mcp — runtime 0.0.83, pinned in the captured npm lockfile. Browser binaries and OS libraries are installed separately, not redistributed here.
- Agent Browser: https://github.com/vercel-labs/agent-browser — pinned runtime 0.38.2; runtime packages are installed locally by bootstrap, not placed in this Git repository.
- OpenCode: https://github.com/anomalyco/opencode — pinned runtime 1.18.35; its built-in customize-opencode skill is supplied by that runtime.
- Gitleaks: https://github.com/gitleaks/gitleaks — scanner 8.30.1 is fetched locally and verified against the official checksum, never bundled into the committed snapshot.

Package contribution-document links missing from upstream npm distributions are not functional dependencies. Browser binaries, optional OS CLI binaries, user projects, authentication and personal vault records are not redistributed by this snapshot.
