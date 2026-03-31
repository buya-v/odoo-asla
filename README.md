# odoo-asla — AslaBot

AI-powered Odoo managed services platform operated at [odoo.asla.mn](https://odoo.asla.mn).

## What It Does

AslaBot receives customer support tickets, triages them using AI, and executes administration, support, and customization tasks on client Odoo instances — either via live MCP connections or by generating deployable codebase packages.

## Architecture

```
Customer → AslaBot (tickets) → odoo.asla.mn (AI brain) → Client Odoo (via MCP)
                                     │                          or
                                     └──────────────────→ Codebase + Install Guide
```

**AI Models:**
- **Qwen 3 14B** (local, Ollama) — routine operations (~80% of tickets)
- **Claude Sonnet** (API) — complex customization (~20% of tickets)

## Quick Start

```bash
# Clone
git clone https://github.com/buya-v/odoo-asla.git
cd odoo-asla

# Install module
odoo-bin -d asla_dev -i aslabot --addons-path=addons

# Run tests
odoo-bin -d asla_dev --test-tags /aslabot --stop-after-init

# Lint
ruff check addons/
```

## Development with Claude Code

This project is configured for [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview). Run `claude` in the project root to start.

**Available slash commands:**
- `/onboard` — Get oriented with the codebase
- `/new-model` — Scaffold a new Odoo model with all files
- `/implement-fr FR-X.X` — Implement a specific functional requirement
- `/security-audit` — Run a security check on the module

**Available agents:**
- `ticket-handler` — Ticket lifecycle features (FR-1.x, FR-3.x, FR-7.x)
- `mcp-operations` — MCP connection and execution (FR-2.x, FR-4.x, FR-8.x)
- `codegen` — Codebase delivery generation (FR-5.x)

## Module Structure

```
addons/aslabot/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── ticket.py              # FR-1.x, FR-3.x
│   ├── client_registry.py     # FR-2.x
│   ├── mcp_connection.py      # FR-2.3, FR-8.1
│   ├── operation_plan.py      # FR-4.1, FR-4.2, FR-4.3
│   └── operation_log.py       # FR-4.5
├── views/
│   ├── ticket_views.xml
│   ├── client_registry_views.xml
│   ├── operation_log_views.xml
│   └── menu_views.xml
├── security/
│   ├── aslabot_groups.xml     # FR-8.2
│   ├── ir.model.access.csv
│   └── aslabot_rules.xml      # Record rules
├── data/
│   └── ir_sequence_data.xml
├── controllers/               # Webhook endpoints (TODO)
├── wizards/                   # Transient models (TODO)
└── tests/
    ├── test_ticket.py
    ├── test_client_registry.py
    └── test_operation_plan.py
```

## Documentation

- [Functional Requirements (FRD)](docs/FRD.md) — 38 requirements across 9 domains
- [System Architecture](docs/architecture.md) — Components, data flows, security

## License

LGPL-3 — See [LICENSE](LICENSE) file.
