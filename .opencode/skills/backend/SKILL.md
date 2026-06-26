---
name: backend
description: >-
  Use for server-side tasks: implementing APIs, services, business logic,
  authentication, and middleware with any backend stack (Python, TypeScript,
  Go, Java, Rust, etc.).
---

# Backend Development

## When to use
- Building REST, GraphQL, or gRPC APIs
- Implementing business logic, services, or use cases
- Configuring server, middleware, or authentication
- Working with ORMs, database access, or caching
- Adding validation, serialization, or error handling
- API versioning, documentation, or testing

## API design patterns

### REST — semantic endpoints
```
GET    /api/v1/users              # list (paginated)
POST   /api/v1/users              # create
GET    /api/v1/users/:id          # retrieve
PUT    /api/v1/users/:id          # replace
PATCH  /api/v1/users/:id          # partial update
DELETE /api/v1/users/:id          # delete
```

### GraphQL — one endpoint
- Queries for reads, mutations for writes
- Input types for mutations (not raw scalars)
- Error codes in `extensions` field
- DataLoader pattern to batch & cache (avoid N+1)

### gRPC — typed contracts
- `.proto` files as source of truth
- Unary for request/response, server streaming, client streaming, bidirectional
- Errors via status codes (google.rpc)

## Response format (REST)

### Success
```json
{
  "data": { ... },
  "meta": { "page": 1, "limit": 20, "total": 100 }
}
```

### Error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": { "field": "email" }
  }
}
```

## Security checklist
- [ ] Input sanitization (all user input is hostile)
- [ ] Rate limiting (per IP, per user, per endpoint)
- [ ] Authentication (JWT, session, OAuth)
- [ ] Authorization (RBAC, ABAC, resource-level)
- [ ] HTTPS in production
- [ ] CORS configured (not `*` for production)
- [ ] SQL/NoSQL injection prevention
- [ ] XSS prevention (output encoding)
- [ ] CSRF tokens for cookie-based auth
- [ ] Secrets never logged or committed

## Dependency injection
```python
# Python
class UserService:
    def __init__(self, repo: UserRepository, mailer: Mailer):
        self.repo = repo
        self.mailer = mailer
```
```typescript
// TypeScript
class UserService {
  constructor(
    private repo: UserRepository,
    private mailer: Mailer
  ) {}
}
```
(DI enables testability — inject mocks in tests)

## Useful patterns

### Service layer
Route → Controller (parse + validate) → Service (business logic) → Repository (data access)

### Unit of Work
Wrap multiple DB operations in a transaction. Pass session/connection through the call chain.

### Result type
```typescript
type Result<T, E = Error> = { ok: true; value: T } | { ok: false; error: E };
```
(Explicit error handling instead of try/catch everywhere)

## Resources
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines)
- [Google API Design Guide](https://cloud.google.com/apis/design)
