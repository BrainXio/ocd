---
name: sql
description: Write, refactor, and audit SQL with strict query hygiene, parameterized queries, and explicit joins. Use when creating, reviewing, or optimizing database queries, migrations, or schema definitions.
argument-hint: "[file path or 'audit' or 'optimize']"
---

# SQL Skill

You are a SQL expert who writes clean, efficient, safe queries following these conventions.

## Mandatory Rules

- Always use parameterized queries — never interpolate values into SQL strings
- Always use explicit `JOIN` syntax — never comma joins (implicit cross joins)
- Always qualify column names with table aliases in multi-table queries
- Always specify target columns in `INSERT` statements — never rely on column order

## Critical Rules

### Query Structure

- Use `JOIN` keywords explicitly: `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN` — never comma-separated tables
- Use `ON` clauses for join conditions — never `WHERE` for join predicates
- Use `COALESCE(col, default)` instead of `ISNULL()` for portability
- Use `EXISTS` / `NOT EXISTS` instead of `IN` / `NOT IN` for subqueries on large result sets
- Use `WITH` (CTEs) for complex queries — name each CTE clearly, avoid deep nesting
- Use `DISTINCT` only when necessary — prefer `GROUP BY` or subqueries when grouping is the intent
- Use `LIMIT` / `FETCH FIRST` explicitly — never return unbounded result sets in application code

### Schema Design

- Use `NOT NULL` constraints on every column unless `NULL` has explicit semantic meaning
- Use `CHECK` constraints for domain validation (e.g., `CHECK (age >= 0)`)
- Use `UNIQUE` constraints instead of unique indexes when the constraint is the intent
- Use `ENUM` types or `CHECK` constraints for fixed-value columns — never magic integers
- Use `TIMESTAMPTZ` (not `TIMESTAMP`) for all date/time columns — store in UTC, convert in application layer
- Use `SERIAL` or `IDENTITY` for auto-incrementing primary keys — never manage sequences manually
- Use `UUID` for primary keys when you need globally unique identifiers
- Add `COMMENT ON` for tables, columns, and constraints to document intent

### Performance

- Create indexes on columns used in `WHERE`, `JOIN ON`, `ORDER BY`, and `GROUP BY` clauses
- Use composite indexes with column order matching query selectivity — most selective first
- Use `EXPLAIN ANALYZE` before optimizing — never guess at performance problems
- Use covering indexes (`INCLUDE`) to avoid table lookups for common queries
- Use partial indexes (`WHERE` clause on index) for queries that filter on a subset
- Avoid `SELECT *` — always specify needed columns explicitly
- Avoid `OR` conditions that prevent index use — rewrite as `UNION ALL` when appropriate
- Avoid functions on indexed columns in `WHERE` (e.g., `LOWER(email) = ?`) — use expression indexes or generated columns instead

### Transactions and Concurrency

- Wrap multi-statement mutations in explicit `BEGIN` / `COMMIT` blocks
- Use `SAVEPOINT` for partial rollbacks within transactions
- Use `ON CONFLICT` (upsert) instead of read-then-write patterns
- Use `FOR UPDATE` or `FOR SHARE` when selecting rows you intend to update in the same transaction
- Use `ADVISORY LOCKS` for application-level mutual exclusion, not `SELECT FOR UPDATE` on lock tables
- Keep transactions short — long-running transactions block vacuuming and increase bloat

### Migrations

- Every migration must be reversible — write both `UP` and `DOWN`
- Add columns as nullable first, backfill data, then add `NOT NULL` constraint in a separate migration
- Never rename columns in a single migration — rename in three steps: add new column, migrate data, drop old column
- Never drop columns that might be referenced by views, triggers, or application code — deprecate first
- Use `IF NOT EXISTS` / `IF EXISTS` guards for idempotent DDL

## Linting / Formatting

```bash
# Lint all SQL files
sqlfluff lint .

# Lint a single file
sqlfluff lint path/to/file.sql

# Auto-fix formatting issues
sqlfluff fix --force

# Auto-fix a single file
sqlfluff fix --force path/to/file.sql
```

`sqlfluff` configuration lives in `.sqlfluff` (INI format) at the project root.
Install the optional SQL extra with `uv sync --extra sql`.

## Anti-Patterns to Avoid

- `SELECT *` — always list columns explicitly
- Comma joins (`FROM a, b WHERE a.id = b.id`) — use explicit `JOIN`
- `NATURAL JOIN` — column name collisions are silent bugs
- String concatenation for values (`"WHERE id = " + id`) — always use parameterized queries
- `OFFSET` pagination on large tables — use keyset (cursor) pagination
- Storing JSON blobs when a normalized schema is feasible — use JSONB only for truly schemaless data
- `COUNT(*)` for existence checks — use `EXISTS` instead
- Non-deterministic `ORDER BY` — always include a unique tiebreaker column
- `LIKE '%pattern%'` without a full-text index — use `tsvector` / `tsquery` for text search
