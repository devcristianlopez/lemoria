---
name: database
description: >-
  Use for database tasks: designing schemas, writing migrations, indexing,
  query optimization, and data modeling with SQL and NoSQL databases.
---

# Database Design & Management

## When to use
- Designing or modifying database schemas
- Creating migrations (up/down)
- Indexing strategy and query optimization
- Data modeling (entities, relationships, constraints)
- Connection pooling and configuration
- Seed data and factories

## Schema design principles

### Normalization (relational)
| Normal Form | Rule |
|-------------|------|
| 1NF | Atomic columns, no repeating groups |
| 2NF | 1NF + every non-key depends on full PK |
| 3NF | 2NF + every non-key depends only on the PK |
| (BCNF) | Every determinant is a candidate key |

Denormalize only when performance measurements justify it.

### Naming conventions

**Relational (SQL)** — `snake_case`
- Tables: plural nouns (`users`, `order_items`)
- Columns: singular (`first_name`, `email`, `created_at`)
- PK: `id` (auto-increment or UUID)
- FK: `{table}_id` (`user_id`, `order_id`)
- Index: `idx_{table}_{column}`
- Unique: `uq_{table}_{column}`

**Document (MongoDB)** — `camelCase`
- Collections: plural (`users`, `orderItems`)
- Fields: `firstName`, `email`, `createdAt`

## Indexing strategy

### When to index
- Columns in WHERE clauses
- Columns in JOIN conditions (FKs)
- Columns in ORDER BY / GROUP BY
- Columns used in range queries (date, numeric)

### Index types
```sql
-- B-tree (default) — most queries
CREATE INDEX idx_users_email ON users(email);

-- Composite — prefix match queries
CREATE INDEX idx_users_status_created ON users(status, created_at);

-- Partial — subset of data
CREATE INDEX idx_users_active ON users(email) WHERE active = true;

-- Unique — enforce uniqueness
CREATE UNIQUE INDEX uq_users_email ON users(email);
```

### Anti-patterns
- Over-indexing (slows writes)
- Indexing low-cardinality columns (boolean, status with 2 values)
- Not using `EXPLAIN` before optimizing
- Missing indexes on FKs (causes N+1 in ORMs)

## Migration best practices
- One file = one atomic change
- Always reversible (up + down)
- Descriptive name: `add_users_email_unique_constraint`
- Never edit an already-applied migration
- Test migrations on a copy of production data

```python
# Example migration structure
migrations/
  versions/
    001_initial_schema.py
    002_add_email_unique.py
    003_add_user_status.py
```

## Query optimization workflow
1. Get slow query
2. Run `EXPLAIN ANALYZE` (or equivalent)
3. Identify: Sequential scan on large table? Missing index?
4. Add index or rewrite query
5. Re-run `EXPLAIN` to verify
6. Measure in production-like data

## Connection pooling
| Parameter | Recommended |
|-----------|-------------|
| Pool size | 5-20 (depends on workload) |
| Overflow | 5-10 (burst capacity) |
| Timeout | 30s acquire, 300s idle |
| Health check | `pool_pre_ping=True` (SQLAlchemy) |

## Resources
- [Use the Index, Luke](https://use-the-index-luke.com/) — SQL indexing guide
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MongoDB University](https://university.mongodb.com/) — free courses
