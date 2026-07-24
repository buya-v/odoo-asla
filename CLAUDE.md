# Project: odoo-asla (AslaBot)

AI-powered Odoo managed services platform. Receives customer tickets, triages via AI, executes admin/support/customization tasks on client Odoo instances via MCP or delivers generated codebase packages.

See @docs/FRD.md for full functional requirements (38 FRs across 9 domains).
See @docs/architecture.md for system architecture and data flows.

## Quick Facts

- **Stack**: Odoo 18.0, Python 3.12, PostgreSQL 16
- **AI Models**: gemma4:e4b (local/Ollama) for routine, Claude Sonnet API for complex tasks
- **MCP**: Apexive `llm_mcp_server` for client connections
- **License**: LGPL-3
- **Target Platform**: odoo.asla.mn

## Commands

- `odoo-bin -d asla_dev -i aslabot --addons-path=addons` — Install module in dev DB
- `odoo-bin -d asla_dev -u aslabot --addons-path=addons` — Update module after changes
- `odoo-bin -d asla_dev --test-tags /aslabot --stop-after-init` — Run module tests
- `python -m pytest addons/aslabot/tests/ -v` — Run tests with pytest
- `ruff check addons/` — Lint Python code
- `ruff format addons/` — Format Python code

## Key Directories

- `addons/aslabot/` — Main Odoo module
- `addons/aslabot/models/` — ORM models (ticket, client_registry, operation_log)
- `addons/aslabot/views/` — XML views and actions
- `addons/aslabot/security/` — Access rights and record rules (ir.model.access.csv)
- `addons/aslabot/wizards/` — Transient models for user workflows
- `addons/aslabot/controllers/` — HTTP controllers (webhook endpoints, API)
- `addons/aslabot/data/` — Demo data and initial configuration
- `addons/aslabot/tests/` — Unit and integration tests
- `docs/` — FRD, architecture docs, API specs

## Odoo Development Rules

- Always inherit from `models.Model` (persistent) or `models.TransientModel` (wizards)
- Use `_name` and `_description` on every model
- Field strings must be human-readable: `client_id = fields.Many2one('res.partner', string='Client')`
- Security: every model needs a line in `ir.model.access.csv` — no exceptions
- Views: use `<record>` tags, never `<template>` for backend views
- Use `_inherit` for extending existing models, `_name` + `_inherit` for delegation
- API decorators: `@api.depends` for computed, `@api.onchange` for UI, `@api.constrains` for validation
- Never use `sudo()` unless explicitly required and documented with a comment explaining why
- All monetary fields use `fields.Monetary` with a `currency_id` companion
- Tests inherit from `odoo.tests.common.TransactionCase` or `HttpCase`

## Code Style

- Python: PEP 8, enforced by ruff
- Max line length: 120 characters
- Imports: stdlib → third-party → odoo → local, separated by blank lines
- Docstrings: Google style on public methods
- No `print()` — use `_logger = logging.getLogger(__name__)`
- String formatting: f-strings preferred over `.format()` or `%`

## Do NOT

- Use `cr.execute()` with string formatting — always use parameterized queries `cr.execute(query, params)`
- Bypass Odoo ORM for CRUD operations unless there is a documented performance reason
- Hardcode IDs — use XML IDs with `self.env.ref('module.xml_id')`
- Store MCP credentials or API keys in Python code or XML data files
- Modify `res.users` or `ir.rule` records without explicit approval comment
- Create models without security rules — CI will reject the PR
- Use `@api.multi` — deprecated since Odoo 13

## Git Conventions

- Branch: `feat/FR-X.X-short-description`, `fix/FR-X.X-short-description`, `chore/description`
- Commit format: conventional commits — `feat(ticket): add auto-classification engine`
- PRs require: passing tests, ruff clean, security file coverage check
- Never commit to `main` directly

## MCP Integration Notes

- Client MCP connections use Streamable HTTP transport
- Tool calls target standard Odoo models via `search_records`, `create_record`, `update_record`, `delete_record`
- Every MCP operation MUST be logged to `aslabot.operation.log`
- Dry-run mode validates against `ir.model.fields` before execution
- Permission tiers: auto-execute, confirm-then-execute, never-automate (see FR-4.3)
