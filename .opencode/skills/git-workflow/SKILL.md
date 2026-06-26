---
name: git-workflow
description: >-
  Use for version control tasks: commits, branching, merging, pull requests,
  changelogs, and git configuration.
---

# Git Workflow

## When to use
- Committing code changes with traceability
- Branching strategy setup or decisions
- Creating pull requests
- Fixing git history (rebase, squash, amend)
- Generating changelogs
- Setting up git hooks or CI/CD

## Branching strategy

### GitHub Flow (recommended for most projects)
```
main ← stable, always deployable
  └── feature/<name>       ← new features
  └── fix/<name>           ← bug fixes
  └── chore/<name>         ← maintenance
  └── refactor/<name>      ← refactoring
  └── docs/<name>          ← documentation
```
- All branches branch off `main`
- PR into `main` when ready
- Delete branch after merge
- No long-lived branches

### Git Flow (legacy / release management)
```
master ← production releases
  └── develop ← integration branch
        └── feature/<name>
        └── release/<version>
        └── hotfix/<name>
```
(Use only when you need release trains or multiple active versions)

## Conventional Commits
```
<type>(<scope>): <description>

[optional body]
[optional footer(s)]
```

### Types
| Type | When |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code change that neither fixes nor adds |
| `test` | Adding or fixing tests |
| `chore` | Maintenance (deps, build, CI) |

### Examples
```
feat(auth): add JWT authentication
fix(api): handle null email in user creation
docs(readme): update installation steps
refactor(parser): extract validation logic
test(cart): add checkout flow tests
```

## Atomic commits
One commit = one complete logical change:
- ✅ `feat(api): add user registration endpoint` (a single endpoint with route, controller, tests)
- ❌ `feat(api): add user registration` + `fix(api): fix user registration bug` (should be one)
- ❌ `update stuff` (too vague)
- ❌ `feat(api): add user registration` + `feat(api): add product listing` (two features in one commit)

## Commit traceability
Always link commits to tasks:
```
feat(auth): implement password reset

Password reset flow with email token.
Token expires in 1 hour.

Task: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

## Pull requests

### Template
```markdown
## What
Brief description of the change.

## Why
Why is this needed? (link to task or issue)

## How to test
1. Run `npm run dev`
2. Go to /users
3. Click "Create"
4. Verify user appears in list

## Checklist
- [ ] Tests pass
- [ ] No TODO/FIXME
- [ ] Docs updated
- [ ] Decision logged

Closes #TASK-ID
```

### PR size
- Small: < 200 lines changed per PR
- Focused: one feature/concern per PR
- Reviewable: reviewer can understand in < 30 min

## Changelog
### Per version (semver)
```markdown
## [1.5.0] - 2026-05-20
### Added
- Password reset flow (#42)

### Changed
- Session timeout from 30m to 60m (#40)

### Fixed
- Null pointer on empty cart (#38)
```

## Git commands reference

| Action | Command |
|--------|---------|
| New branch | `git checkout -b feature/name` |
| Stage | `git add <file>` or `git add -p` (interactive) |
| Commit | `git commit -m "type: message"` |
| Push | `git push -u origin feature/name` |
| Sync main | `git fetch origin && git rebase origin/main` |
| Amend | `git commit --amend` (never if pushed) |
| Undo last commit (local) | `git reset HEAD~1 --soft` |
| Drop last commit (local) | `git reset HEAD~1 --hard` (destructive) |

## Resources
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Keep a Changelog](https://keepachangelog.com/)
