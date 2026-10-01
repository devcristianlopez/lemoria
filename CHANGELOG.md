# Changelog

All notable changes to Lemoria will be documented in this file.

The format follows Keep a Changelog, and versions follow Semantic Versioning
while the project moves toward public releases.

## [Unreleased]

### Added
- OpenCode TUI plugin adding a **Lemoria** group to the Ctrl+P command palette:
  per-agent model + effort configuration with select dialogs, model/effort
  clearing, agent `sync` and uninstall (UI integrations or full).
- `installer/lib.sh: install_opencode_lemoria_menu` copies the plugin to
  `~/.config/opencode/plugins/lemoria-menu/`, registers it in `cli.json`
  preserving existing plugins, and writes the plugin `config.json` with the
  repo and agents directories so model pins land in one place.

## [0.3.0] - 2026-09-30

### Added
- `lemoria commit add/list/sync` for commit traceability.
- Historical commit backfill from `Task: <task-id>` trailers.
- Installer logic extracted to a testable shell library with installer tests.
- Support for `uv -> venv -> pip` installation order.
- Community docs: contributing and security policy.

### Changed
- Docker detection now checks the daemon with `docker info`, not only the Compose
  plugin version.
- PostgreSQL native is treated as the preferred path; Docker remains optional.
- Vault `commits.md` now lists registered commits and links them to tasks.
- Omarchy panel changes are included with the contract test that requires them.

### Fixed
- CI failure caused by committing the panel contract test before the matching
  `Panel.qml` implementation.
- `lemoria task create -a` now accepts agent names or UUIDs and fails with a
  readable error instead of a foreign-key traceback.
- `print_db_stop_hint` now handles every database provider state explicitly.
