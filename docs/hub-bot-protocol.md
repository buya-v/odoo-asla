# AslaBot Hub ↔ Bot Protocol — v1

Status: Draft · Protocol version `1.0` · Transport: JSON-RPC 2.0 over HTTPS

## 1. Purpose & roles

AslaBot splits into two Odoo modules that run on **different servers/databases**
and therefore share a **wire contract, not code**:

- **`odoo.asla.hub`** (on `odoo.asla.mn`) — the brain: client registry, triage,
  AI (via `odoo-asla-ai`), operation planning, central audit. Canonical ticket store.
- **`odoo.asla.bot`** (on each client's Odoo) — the client agent: native ticket
  intake from the client's own users, config introspection, **local** execution
  with **local** permission-tier enforcement, and response relay back to users.

This document is the sole compatibility surface between them. Either side may be
upgraded independently within the same major protocol version.

### Two channels, one transport

| Channel | Direction | Purpose |
|---|---|---|
| **Intake** | bot → hub | new tickets, user replies, config, execution results, heartbeat |
| **Control** | hub → bot | grounded answers, operation requests, dry-runs, state updates |

Both are JSON-RPC 2.0 (§3), reusing the transport/auth AslaBot already uses for MCP.

## 2. Design principles

1. **Users stay home.** Client staff submit tickets inside their own Odoo; they
   never need a hub login. (Removes the hub-side `contact_ids` record-rule coupling.)
2. **The bot is authoritative on safety.** The hub *proposes* an operation and its
   tier; the **bot re-derives the tier locally and decides** (§7). The client owns
   what the hub may touch — a stronger guarantee than the hub self-restricting.
3. **Advisory by default, execution by exception.** Most tickets resolve with a
   grounded answer (no write). Writes always go through a plan + tier gate.
4. **At-least-once, idempotent.** Every call carries a `correlation_id`; replays
   are de-duplicated (§10). Either side queues when the other is unreachable.
5. **Additive evolution.** New optional params/methods are minor; removed or
   changed semantics are major. Unknown optional fields MUST be ignored.

## 3. Transport & envelope

- **JSON-RPC 2.0** over **HTTPS** (TLS 1.2+, FR-8.3). `Content-Type: application/json`.
- Endpoints (paths are conventions, host is per-deployment):
  - Hub: `POST https://odoo.asla.mn/asla/hub/rpc`
  - Bot: `POST https://<client-host>/asla/bot/rpc`
- Every request `params` object MUST include this envelope:

```json
{
  "protocol_version": "1.0",
  "client_id": "acme",
  "correlation_id": "b1f3…",   // idempotency key (uuid4), unique per logical event
  "ts": "2026-07-24T07:00:00Z"
}
```

- Batch requests are NOT used (one logical event per call — simpler auditing).
- Responses are standard JSON-RPC result/error objects (§9). `id` echoes the request.

## 4. Pairing & authentication

Each client has a **credential pair**, issued once at pairing and revocable:

- `bot_token` — the bot presents it on **intake** calls (`Authorization: Bearer …`).
- `hub_token` — the hub presents it on **control** calls.

Both are per-client, stored encrypted (FR-8.1), **never logged**. TLS is mandatory;
mTLS is RECOMMENDED for high-tier clients.

### `session.pair` (one-time bootstrap, bot → hub)

The operator generates an **enrollment code** in the hub and enters it in the bot.

```json
// request
{"jsonrpc":"2.0","id":1,"method":"session.pair",
 "params":{"protocol_version":"1.0","enrollment_code":"ENR-7Q2K-…",
           "bot":{"version":"1.0.0","odoo_version":"18.0","endpoint":"https://acme.odoo.mn/asla/bot/rpc"}}}
// result
{"jsonrpc":"2.0","id":1,"result":{
   "client_id":"acme","bot_token":"…","hub_token":"…","protocol_version":"1.0"}}
```

After pairing, the hub knows the bot's endpoint (for control calls) and both sides
hold their tokens. Rotation: re-run `session.pair` with a fresh enrollment code.

## 5. Intake channel — bot → hub

| Method | Purpose | Key params | Returns |
|---|---|---|---|
| `ticket.submit` | New ticket from a client user | `bot_ref`, `subject`, `body`, `category`, `priority`, `reporter{name,email}`, `lang`, `attachments[]` | `hub_ref`, `state` |
| `ticket.append` | User added a reply | `hub_ref` \| `bot_ref`, `body`, `author` | `ok` |
| `ticket.set_feedback` | Resolution feedback | `hub_ref`, `feedback` (`resolved`/`partial`/`unresolved`), `notes` | `ok` |
| `client.push_config` | Live Odoo introspection snapshot | see §8 | `ok`, `indexed` |
| `operation.report_result` | Outcome of a requested operation | `operation_ref`, `status`, `result` \| `error`, `executed_by`, `duration` | `ok` |
| `heartbeat` | Liveness + health | `bot_version`, `health`, `queue_depth` | `ok`, `server_ts` |

`ticket.submit` example:

```json
{"jsonrpc":"2.0","id":10,"method":"ticket.submit","params":{
  "protocol_version":"1.0","client_id":"acme","correlation_id":"…","ts":"…",
  "bot_ref":"acme-T-00042",
  "subject":"НӨАТ тохиргоо",
  "body":"<p>Odoo дээр НӨАТ 10% хэрхэн тохируулах вэ?</p>",
  "category":"support", "priority":"2", "lang":"mn",
  "reporter":{"name":"Болд","email":"bold@acme.mn"},
  "attachments":[{"name":"screenshot.png","mimetype":"image/png","data_b64":"…"}]
}}
// result
{"jsonrpc":"2.0","id":10,"result":{"hub_ref":"ASLA-01042","state":"triaged"}}
```

The hub creates its canonical ticket, triages, and (typically) calls
`odoo-asla-ai` for a grounded answer, then pushes it back via `ticket.post_answer`.

## 6. Control channel — hub → bot

| Method | Purpose | Key params | Returns |
|---|---|---|---|
| `ticket.post_answer` | Deliver the grounded answer to the user | `bot_ref`, `body_html`, `sources[]`, `response_category` | `ok` |
| `ticket.set_state` | Reflect hub state to the user | `bot_ref`, `state`, `note` | `ok` |
| `operation.dry_run` | Validate a plan against the client schema (no write) | `operation_ref`, `target_model`, `method`, `arguments` | `valid`, `warnings[]` |
| `operation.request` | Ask the bot to perform an operation | `operation_ref`, `bot_ref`, `target_model`, `method`, `arguments`, `hub_tier` | `accepted`/`pending_confirmation`/`rejected` |

**The hub never sends a raw `tools/call`.** All writes are described as an
`operation.request` so the bot can apply local policy (§7) — this is the key
difference from the generic-MCP delivery mode, and the reason the bot is the
high-trust tier. Legacy MCP-only clients keep using `tools/call` against
`llm_mcp_server` with no local policy layer.

`operation.request` example:

```json
{"jsonrpc":"2.0","id":20,"method":"operation.request","params":{
  "protocol_version":"1.0","client_id":"acme","correlation_id":"…","ts":"…",
  "operation_ref":"OP-9001","bot_ref":"acme-T-00042",
  "target_model":"account.tax","method":"create",
  "arguments":{"values":{"name":"НӨАТ 10%","amount":10.0,"type_tax_use":"sale"}},
  "hub_tier":"confirm_then_execute"
}}
// result (bot decided a human must approve first)
{"jsonrpc":"2.0","id":20,"result":{"status":"pending_confirmation","local_tier":"confirm_then_execute"}}
```

The bot later calls `operation.report_result` (intake channel) with the outcome.

## 7. Permission tiers — authoritative on the bot

The bot re-derives the tier from `(target_model, method)` using **its own**
`SENSITIVE_MODELS` and `READ_METHODS` config, which the **client controls**.
`hub_tier` is advisory; `local_tier` is binding.

| local_tier | Behaviour on the bot |
|---|---|
| `auto_execute` | Execute immediately (read/search/inspect), then `operation.report_result`. |
| `confirm_then_execute` | Create a local approval task; execute only after a client operator approves in the bot UI; then report. |
| `never_automate` | Reject at once (`res.users`, `ir.rule`, `account.move`, …). Return error `-32010`; never queue. |

If `hub_tier` is weaker than `local_tier`, the **stricter** wins. Every executed
operation is logged locally (bot) **and** centrally (hub, via `report_result`) — dual audit (FR-4.5).

## 8. `client.push_config` — introspection payload

Feeds the hub's per-client context (which the hub forwards to
`odoo-asla-ai /api/client/introspect`, keyed `client_id`).

```json
{"jsonrpc":"2.0","id":30,"method":"client.push_config","params":{
  "protocol_version":"1.0","client_id":"acme","correlation_id":"…","ts":"…",
  "config":{
    "odoo_version":"18.0","edition":"Community",
    "modules_installed":["sale","account","stock"],
    "modules_absent":["mrp"],
    "custom_models":["x_loyalty_tier"],
    "custom_fields":{"res.partner":["x_credit_limit"]},
    "ui_language":"mn","vat":"10%"
  }}}
```

The bot SHOULD push on install, on module (un)install, and on a periodic schedule.

## 9. Errors

Standard JSON-RPC error object `{code, message, data}`. AslaBot codes (in the
implementation-defined `-32000…-32099` range):

| code | meaning |
|---|---|
| `-32001` | unauthorized (bad/expired token) |
| `-32002` | unknown_client |
| `-32003` | protocol_version_mismatch |
| `-32004` | unknown_ref (ticket/operation not found) |
| `-32010` | never_automate_blocked |
| `-32011` | confirmation_required (not yet approved) |
| `-32012` | dry_run_failed (schema mismatch) |
| `-32020` | duplicate (idempotent replay — treat as success, see §10) |

`data` MAY carry structured detail (e.g. `{"unknown_fields":["x_foo"]}`).

## 10. Delivery semantics

- **At-least-once.** The sender retries with the **same** `correlation_id` (jittered
  backoff) until it gets a non-transient response.
- **Idempotency.** The receiver records processed `correlation_id`s (TTL ≥ 7 days).
  A replay returns the original result, or `-32020` — the sender treats both as success.
- **Ordering** is not guaranteed; each event is self-contained. Where order matters
  (ticket state), include a monotonically increasing `seq` and ignore stale updates.
- **Queueing.** If the peer is unreachable, events are queued locally and flushed on
  the next successful `heartbeat`. `heartbeat` cadence: 60 s (configurable).

## 11. Ticket identity & state

- `bot_ref` (client-local) ↔ `hub_ref` (canonical) — mapping stored on both sides.
- **Ownership of state:** the **hub owns triage/AI state** (`triaged`, response
  category, model tier); the **bot owns intake + execution UI state** and mirrors
  hub state for the user. State transitions cross the wire via `ticket.set_state`
  (hub→bot) and `ticket.append`/`report_result` (bot→hub).
- Shared state vocabulary: `draft · triaged · in_progress · executing · done · failed · escalated`.

## 12. Security summary (maps to FR-8.x)

- Per-client `bot_token`/`hub_token`; TLS mandatory; mTLS recommended (FR-8.3).
- Tokens & any client secrets encrypted at rest, never logged (FR-8.1).
- Local, client-owned permission enforcement; `never_automate` immovable (FR-8.5).
- Per-client isolation: a token authorizes exactly one `client_id`; the hub MUST
  reject a payload whose `client_id` ≠ the token's client.
- Dual audit trail: bot-local + hub-central for every operation (FR-4.5).

## 13. Versioning

- `protocol_version` is `MAJOR.MINOR`. Peers exchange it at `session.pair` and on
  every call. Same MAJOR = compatible; the higher MINOR degrades to the lower.
- A MAJOR mismatch returns `-32003` and blocks control/intake until upgrade.

## Appendix A — End-to-end flows

**A. Ticket → grounded answer (no write, the common case)**
```
user (client Odoo) ─create ticket─► bot
bot ─ticket.submit──────────────────► hub          (intake)
hub ─triage + brain.answer(odoo-asla-ai)─► grounded answer
hub ─ticket.post_answer──────────────► bot          (control)
bot ─post to ticket chatter──────────► user
```

**B. Ticket → guarded execution**
```
bot ─ticket.submit──────────────────► hub
hub ─operation.dry_run──────────────► bot  → valid + warnings
hub ─operation.request(confirm)─────► bot  → pending_confirmation
client operator approves in bot UI ─► bot executes locally (tier-gated)
bot ─operation.report_result────────► hub
hub ─ticket.post_answer / set_state─► bot → user
```

**C. Config sync**
```
bot ─client.push_config─────────────► hub ─/api/client/introspect─► odoo-asla-ai
```

## Appendix B — Method index

Intake (bot→hub): `session.pair`, `ticket.submit`, `ticket.append`,
`ticket.set_feedback`, `client.push_config`, `operation.report_result`, `heartbeat`.

Control (hub→bot): `ticket.post_answer`, `ticket.set_state`, `operation.dry_run`,
`operation.request`.
