# odoo-asla (AslaBot)

AI-powered Odoo managed services platform. Odoo 18.0, Python 3.12, PostgreSQL 16.

## Commands
- Install: `odoo-bin -d asla_dev -i aslabot --addons-path=addons`
- Update: `odoo-bin -d asla_dev -u aslabot --addons-path=addons`
- Test: `odoo-bin -d asla_dev --test-tags /aslabot --stop-after-init`
- Lint: `ruff check addons/`
- Format: `ruff format addons/`

## Structure
- `addons/aslabot/models/` — ORM models
- `addons/aslabot/views/` — XML views
- `addons/aslabot/security/` — ACLs and record rules
- `addons/aslabot/controllers/` — HTTP endpoints
- `addons/aslabot/tests/` — Tests

## Rules
- Every model needs `ir.model.access.csv` entry
- Use parameterized SQL queries, never string formatting
- Use `fields.Monetary` with `currency_id` for money
- No `sudo()` without documented justification
- No hardcoded IDs — use `self.env.ref()`
- All MCP operations must be logged
- Tests inherit from `TransactionCase` or `HttpCase`
- Conventional commits: `feat(scope): description`
