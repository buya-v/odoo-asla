# AslaBot — Functional Requirements Document (Reference)

Version 1.0 | 2026-03-31 | ASLA LLC

Full document: see `AslaBot_FRD_v1.0.docx`

## Requirements Summary

### 3.1 Ticket Intake (5 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-1.1 | Multi-channel intake (web, email, Telegram/WhatsApp, Odoo helpdesk) | Must | MVP |
| FR-1.2 | Capture: client ID, Odoo URL, version, description, priority, category | Must | MVP |
| FR-1.3 | Validate submitting user belongs to registered client | Must | MVP |
| FR-1.4 | File attachments with size/type restrictions | Should | MVP |
| FR-1.5 | Unique ticket ID + receipt confirmation with response category | Must | MVP |

### 3.2 Client Registry (4 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-2.1 | Registry: org name, contacts, URLs, versions, modules, custom models, tier | Must | MVP |
| FR-2.2 | Delivery mode: MCP / codebase / hybrid | Must | MVP |
| FR-2.3 | MCP endpoint URL, encrypted credentials, health status | Must | MVP |
| FR-2.4 | Multiple Odoo instances per client | Should | Phase 2 |

### 3.3 Ticket Triage & Classification (5 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-3.1 | Auto-classify: read-only, config change, data mod, customization, bug, feature | Must | MVP |
| FR-3.2 | Risk assessment based on operation type and target models | Must | MVP |
| FR-3.3 | Route to gemma4:e4b (routine) or Claude Sonnet (complex) | Must | MVP |
| FR-3.4 | Escalate to human when: low confidence, client request, or high-risk | Must | MVP |
| FR-3.5 | Detect and link duplicate/related tickets | Should | Phase 2 |

### 3.4 Execution — MCP Mode (7 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-4.1 | Generate operation plan before write execution | Must | MVP |
| FR-4.2 | Dry-run validation against client schema | Must | MVP |
| FR-4.3 | Three permission tiers: auto / confirm / never | Must | MVP |
| FR-4.4 | Approval workflow for confirm-then-execute operations | Must | MVP |
| FR-4.5 | Full audit logging of every MCP operation | Must | MVP |
| FR-4.6 | Graceful connection failure handling with retry | Should | Phase 2 |
| FR-4.7 | Post-execution verification (re-read modified record) | Should | Phase 2 |

### 3.5 Execution — Codebase Delivery (5 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-5.1 | Generate complete Odoo module package | Must | Phase 2 |
| FR-5.2 | Installation guide with rollback instructions | Must | Phase 2 |
| FR-5.3 | Version-tag packages with ticket ID + timestamp | Must | Phase 2 |
| FR-5.4 | Secure download link or repo push | Should | Phase 2 |
| FR-5.5 | Document assumptions about client environment | Must | Phase 2 |

### 3.6 Per-Client Context Management (4 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-6.1 | Per-client knowledge base (custom models, workflows, history) | Must | Phase 2 |
| FR-6.2 | Auto-sync client KB via MCP (ir.model, ir.model.fields) | Should | Phase 2 |
| FR-6.3 | Prompt for updated env info when stale | Could | Phase 3 |
| FR-6.4 | Inject client context into AI prompts | Must | Phase 2 |

### 3.7 Feedback Loop & Learning (4 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-7.1 | Post-resolution confirmation (resolved/partial/unresolved) | Must | Phase 2 |
| FR-7.2 | Auto re-route failed gemma4:e4b tickets to Claude Sonnet | Should | Phase 2 |
| FR-7.3 | Track success rates per type, model, client | Could | Phase 3 |
| FR-7.4 | Feed resolutions back into client KB | Should | Phase 2 |

### 3.8 Security & Compliance (5 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-8.1 | Encrypted credential storage, never in logs | Must | MVP |
| FR-8.2 | Role-based access (client sees own, operator sees all) | Must | MVP |
| FR-8.3 | TLS for all client communication | Must | MVP |
| FR-8.4 | Audit export (PDF/CSV) | Should | Phase 3 |
| FR-8.5 | Respect Odoo native record rules via MCP | Must | MVP |

### 3.9 Monitoring & SLA (3 FRs)
| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| FR-9.1 | SLA tracking per client tier | Should | Phase 3 |
| FR-9.2 | MCP connection health monitoring + alerts | Should | Phase 3 |
| FR-9.3 | Operations dashboard | Could | Phase 3 |

## Phase Totals
| | MVP | Phase 2 | Phase 3 |
|--|-----|---------|---------|
| Must | 16 | 7 | 0 |
| Should | 1 | 5 | 3 |
| Could | 0 | 0 | 3 |
| **Total** | **17** | **12** | **6** |
