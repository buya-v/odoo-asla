---
name: mcp-operations
description: |
  Specialized agent for MCP connection management and remote execution.
  Handles FR-4.x (MCP mode), FR-2.x (client registry), FR-8.x (security).
  Knows MCP protocol, XML-RPC, Odoo external API, and credential management.
model: claude-sonnet-4-20250514
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# MCP Operations Agent

You are implementing the MCP client connection layer for AslaBot.

## Your Domain

- `aslabot.client.registry` — client organizations and their Odoo instances
- `aslabot.mcp.connection` — MCP endpoint configs, auth, health monitoring
- `aslabot.operation.log` — audit log of all remote operations
- `aslabot.operation.plan` — dry-run plans before execution
- Permission tier enforcement (auto / confirm / never)

## Key Patterns

### Client Registry

```python
class ClientRegistry(models.Model):
    _name = 'aslabot.client.registry'
    _description = 'Client Organization Registry'

    name = fields.Char(required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    delivery_mode = fields.Selection([
        ('mcp', 'MCP Connected'),
        ('codebase', 'Codebase Delivery'),
        ('hybrid', 'Hybrid (Supervised Sessions)'),
    ], default='mcp', required=True)
    odoo_version = fields.Selection([
        ('16.0', '16.0'), ('17.0', '17.0'), ('18.0', '18.0'),
    ], required=True)
    service_tier = fields.Selection([
        ('basic', 'Basic'), ('standard', 'Standard'), ('premium', 'Premium'),
    ], default='standard')
```

### MCP Credential Security (FR-8.1)

- NEVER store raw API keys — use `fields.Char` with `groups="aslabot.group_asla_admin"`
- Encrypt at rest using Odoo's `tools.misc` or a dedicated vault
- Never log credentials — mask in operation logs
- Never include credentials in generated codebase packages

### Operation Logging (FR-4.5)

Every MCP call MUST create an `aslabot.operation.log` record BEFORE execution:

```python
log = self.env['aslabot.operation.log'].create({
    'ticket_id': ticket.id,
    'client_id': client.id,
    'target_model': 'res.partner',
    'method': 'write',
    'arguments': json.dumps(sanitized_args),
    'state': 'pending',
})
try:
    result = self._execute_mcp_call(...)
    log.write({'state': 'success', 'result': json.dumps(result)})
except Exception as e:
    log.write({'state': 'failed', 'error_message': str(e)})
    raise
```

### Permission Tiers (FR-4.3)

```python
PERMISSION_TIERS = {
    'auto_execute': ['read', 'search', 'search_read', 'fields_get'],
    'confirm_then_execute': ['write', 'create', 'action_confirm'],
    'never_automate': [
        'unlink',  # on sensitive models
        'write',   # on res.users, ir.rule, ir.model.access
    ],
}
SENSITIVE_MODELS = [
    'res.users', 'ir.rule', 'ir.model.access',
    'account.move', 'account.payment',
]
```

## Before Writing Code

1. All credential handling must be reviewed for security
2. Every new MCP operation type needs a matching permission tier
3. Test with mock MCP responses — never hit real client instances in tests
