---
name: code-review
description: >-
  Use for code review tasks: reviewing PRs, verifying PRD alignment, detecting
  technical debt, security issues, and suggesting improvements.
---

# Code Review

## When to use
- Reviewing a pull request or branch before merge
- Verifying implementation matches PRD/specs
- Auditing code for security, performance, or maintainability
- Checking traceability (are decisions documented?)
- Reviewing tests for quality and coverage

## Review workflow

### 1. Understand the context
- Read the PRD or task description
- Read the linked task/ticket
- Understand what problem this solves

### 2. Review architecture first
- Does the design fit the existing system?
- Are new abstractions justified?
- Is there over-engineering or under-engineering?

### 3. Review logic
- Does it handle: happy path, error path, edge cases?
- Are the function signatures typed?
- Are side effects documented?

### 4. Review specific concerns

**Security (OWASP Top 10)**
- SQL/NoSQL injection → parameterized queries?
- XSS → output encoding?
- CSRF → tokens on state-changing requests?
- Authz → is the user authorized for this action?
- Secrets → any token/hardcoded credential?

**Performance**
- N+1 queries → lazy loading when expecting a collection?
- Unbounded loops → is there a limit?
- Expensive operations in hot paths?

**Data integrity**
- Validations at the right level (API + DB)?
- Constraints enforced in schema?
- Race conditions in concurrent access?

**Testing**
- Are tests present and passing?
- Do tests cover the change?
- Are there tests for edge cases?

## Rating system

| Rating | Meaning | Action |
|--------|---------|--------|
| 💬 **Comment** | Suggestion, non-blocking | Author may address or not |
| ❌ **Request** | Blocking issue | Must be resolved before merge |
| ✅ **Approve** | Ready to merge | No blocking issues |

## Tone rules
- Describe the problem, not the person: "This query will cause N+1" not "You missed an N+1"
- Explain the *why* behind a suggestion: "Use `find` instead of `filter().first()` because it raises when not found"
- Acknowledge good code: "Clean separation of concerns here"
- Ask questions: "What happens when `user` is null?"

## Common issues (quick checklist)

### General
- [ ] Magic numbers / hardcoded values (extract to constants)
- [ ] Function too long (> 20 lines)
- [ ] Too many parameters (> 3, consider a config object)
- [ ] Unused imports, variables, or dead code
- [ ] Missing or inadequate error handling
- [ ] No logging for non-trivial operations

### Database
- [ ] N+1 queries (check eager vs lazy loading)
- [ ] Missing indexes on FKs and filtered columns
- [ ] Unbounded pagination (missing limit/offset)
- [ ] Migrations irreversible (no down)

### API
- [ ] No input validation
- [ ] Error messages leaking internals
- [ ] Missing status codes (always return standard ones)
- [ ] No rate limiting on sensitive endpoints

### Frontend
- [ ] Missing loading/error/empty states
- [ ] No keyboard accessibility (Tab order, focus)
- [ ] Missing alt text on images
- [ ] No form validation feedback
- [ ] Unoptimized assets

## Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Google Code Review Guide](https://google.github.io/eng-practices/review/)
- [Conventional Comments](https://conventionalcomments.org/) — standard comment format
