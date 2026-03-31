# AslaBot — System Architecture

## High-Level Flow

```
Customer Channels                    odoo.asla.mn (Hub)                Client Instances
─────────────────                    ──────────────────                ─────────────────
                                     ┌────────────────┐
  Web Form  ─────┐                   │   AslaBot      │
  Email     ─────┤                   │   (Odoo 18)    │
  Telegram  ─────┼──── tickets ────► │                │
  WhatsApp  ─────┤                   │ ┌────────────┐ │    MCP Mode
  Helpdesk  ─────┘                   │ │  Triage    │ │ ──────────────► Client Odoo A
                                     │ │  Engine    │ │                 (MCP Server)
                                     │ └─────┬──────┘ │
                                     │       │        │    MCP Mode
                                     │   ┌───▼────┐   │ ──────────────► Client Odoo B
                                     │   │AI Brain│   │                 (MCP Server)
                                     │   │        │   │
                                     │   │Qwen 14B│   │    Codebase
                                     │   │Claude  │   │ ──────────────► Client C
                                     │   └────────┘   │                 (ZIP download)
                                     └────────────────┘
```

## Component Architecture

### 1. AslaBot Module (`addons/aslabot/`)

The core Odoo module installed on odoo.asla.mn.

**Models:**

| Model | Purpose | FR |
|-------|---------|-----|
| `aslabot.ticket` | Support ticket lifecycle | FR-1.x |
| `aslabot.ticket.category` | Ticket type taxonomy | FR-1.2 |
| `aslabot.client.registry` | Client organizations | FR-2.x |
| `aslabot.client.instance` | Per-client Odoo instances | FR-2.4 |
| `aslabot.mcp.connection` | MCP endpoint configs + auth | FR-2.3 |
| `aslabot.operation.plan` | Pre-execution plans + dry-run | FR-4.1, FR-4.2 |
| `aslabot.operation.log` | Audit trail of all operations | FR-4.5 |
| `aslabot.triage.rule` | Classification rules engine | FR-3.1, FR-3.2 |
| `aslabot.client.knowledge` | Per-client context/KB | FR-6.x |
| `aslabot.codegen.package` | Generated module packages | FR-5.x |

### 2. AI Integration Layer

**Qwen 3 14B (Local)**
- Runs on Ollama at `localhost:11434`
- Handles: read queries, simple config changes, standard admin tasks
- Connected via `llm_ollama` Odoo module
- Temperature: 0.1 (for reliable tool-calling JSON)

**Claude Sonnet (API)**
- Accessed via Anthropic API
- Handles: module generation, complex debugging, multi-model logic
- Connected via `llm_openai` (OpenAI-compatible endpoint) or `llm` base
- Used when: ticket.assigned_model_tier == 'claude_api'

**Routing Logic (FR-3.3):**
```
read_only_query       → Qwen (auto-execute)
configuration_change  → Qwen (confirm-then-execute)
data_modification     → Qwen (confirm-then-execute)
bug_investigation     → Qwen first, Claude on failure
module_customization  → Claude (human review)
new_feature_request   → Claude (human review)
```

### 3. MCP Client Layer

AslaBot acts as an MCP **client** connecting to MCP **servers** running on each client's Odoo.

**Connection Flow:**
1. AslaBot reads `aslabot.mcp.connection` for client endpoint + key
2. Sends JSON-RPC 2.0 over Streamable HTTP
3. Client's `llm_mcp_server` translates to Odoo XML-RPC
4. Result returns through the same path
5. AslaBot logs everything to `aslabot.operation.log`

**Permission Enforcement:**
```
Client MCP Server (their Odoo)
    └── Service User (limited Odoo access rights)
         └── Tool calls filtered by AslaBot permission tiers
              ├── auto_execute: read, search, search_read, fields_get
              ├── confirm_then_execute: write, create (non-sensitive models)
              └── never_automate: anything on res.users, ir.rule, account.move
```

### 4. Codebase Delivery Pipeline

For clients refusing MCP:

1. Ticket classified as needing code changes
2. AI generates Odoo module scaffold
3. `aslabot.codegen.package` record created with:
   - Generated Python/XML/CSV files
   - Installation guide (INSTALL.md)
   - Version tag: `{ticket_id}-{timestamp}`
   - List of assumptions (FR-5.5)
4. Package zipped and stored in `ir.attachment`
5. Secure download link sent to client (expiring)

## Security Architecture

### Credential Management
- MCP API keys: encrypted at rest in `aslabot.mcp.connection`
- Access restricted to `aslabot.group_asla_admin` group
- Never logged, never in AI prompts, never in generated code

### Data Isolation
- Record rules ensure Client A cannot see Client B's data
- Operation logs filtered by `client_id`
- Per-client KB isolated by `client_id`

### Network
- All MCP traffic over TLS (FR-8.3)
- Client endpoints validated on connection creation
- Health checks run periodically (FR-9.2)

## Infrastructure

### odoo.asla.mn Server
- Odoo 18.0 Community/Enterprise
- PostgreSQL 16
- Ollama + Qwen 3 14B (16GB+ RAM dedicated)
- Python 3.12
- Ubuntu 24.04 LTS

### Dependencies (Odoo Modules)
- `llm` — LLM Integration Base (Apexive)
- `llm_ollama` — Ollama provider
- `llm_mcp_server` — MCP server (for dev/testing only)
- `mail` — Messaging and chatter
- `base` — Core Odoo
