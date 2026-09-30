# Security Policy

Lemoria is a developer tool that stores project memory, conversations, decisions
and task/commit traceability. Treat its database and vault as private data.

## Supported versions

The `main` branch is the currently supported development line. Tagged releases
will be documented here once public releases start.

## Reporting a vulnerability

Please report security issues privately by opening a GitHub security advisory if
available, or by contacting the maintainer listed in `pyproject.toml`.

Do not include secrets, database dumps, opencode logs, vault contents, API keys
or private prompts in public issues.

## Security notes for users

- Keep `.env`, `*.db` and `~/.lemoria/vault` out of git.
- The Obsidian vault can contain private prompts, ADRs, PRDs and conversations.
- PostgreSQL native is recommended over adding your user to the `docker` group.
  The `docker` group is root-equivalent on Linux.
- `install.sh` parses `.env`; it does not `source` it, so env files are not
  executed as shell code.
