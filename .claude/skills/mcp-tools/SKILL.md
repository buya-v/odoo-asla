---
name: mcp-tools
description: |
  MCP (Model Context Protocol) integration patterns for AslaBot. Use when
  implementing client connections, remote tool calls, operation planning,
  dry-run validation, or permission tier enforcement. Covers Streamable HTTP
  transport, JSON-RPC 2.0, and Odoo XML-RPC bridge patterns.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# MCP Integration Patterns for AslaBot

## MCP Protocol Basics

AslaBot connects to client Odoo instances via MCP Streamable HTTP transport.
The client runs `llm_mcp_server` (Apexive) which exposes Odoo tools.

Standard tools available on client MCP servers:
- `search_records` — search any Odoo model
- `create_record` — create a record
- `update_record` — update existing records
- `delete_record` — delete records
- `inspect_model` — get model fields and metadata
- `execute_method` — call arbitrary model methods

## Operation Plan Pattern (FR-4.1)

Before executing, always create a plan:

```python
class OperationPlan(models.Model):
    _name = 'aslabot.operation.plan'
    _description = 'MCP Operation Plan'

    ticket_id = fields.Many2one('aslabot.ticket', required=True)
    client_id = fields.Many2one('aslabot.client.registry', required=True)
    target_model = fields.Char(required=True)
    method = fields.Char(required=True)
    arguments = fields.Text()  # JSON
    expected_outcome = fields.Text()
    permission_tier = fields.Selection([
        ('auto_execute', 'Auto Execute'),
        ('confirm_then_execute', 'Confirm Then Execute'),
        ('never_automate', 'Never Automate'),
    ], compute='_compute_permission_tier', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('approved', 'Approved'),
        ('executed', 'Executed'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ], default='draft')

    @api.depends('target_model', 'method')
    def _compute_permission_tier(self):
        for plan in self:
            if plan.method in ('read', 'search', 'search_read', 'fields_get'):
                plan.permission_tier = 'auto_execute'
            elif plan.target_model in SENSITIVE_MODELS:
                plan.permission_tier = 'never_automate'
            else:
                plan.permission_tier = 'confirm_then_execute'
```

## Dry-Run Validation (FR-4.2)

```python
def _validate_dry_run(self, plan):
    """Validate operation against client schema without writing."""
    connection = plan.client_id.mcp_connection_id
    # Fetch model fields from client
    result = self._mcp_call(connection, 'inspect_model', {
        'model': plan.target_model,
    })
    client_fields = json.loads(result)

    # Validate all fields in arguments exist
    args = json.loads(plan.arguments)
    if 'values' in args:
        unknown = set(args['values'].keys()) - set(client_fields.keys())
        if unknown:
            raise ValidationError(
                _('Unknown fields on client: %s') % ', '.join(unknown)
            )
    plan.state = 'validated'
```

## MCP Call Wrapper

```python
import json
import requests
from odoo.exceptions import UserError

def _mcp_call(self, connection, tool_name, arguments):
    """Execute an MCP tool call on a client instance.

    Every call is logged to aslabot.operation.log (FR-4.5).
    """
    log = self.env['aslabot.operation.log'].create({
        'ticket_id': self.env.context.get('active_ticket_id'),
        'client_id': connection.client_id.id,
        'target_model': arguments.get('model', ''),
        'method': tool_name,
        'arguments': json.dumps(arguments),
        'state': 'pending',
    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {connection._get_decrypted_key()}',
    }

    payload = {
        'jsonrpc': '2.0',
        'id': log.id,
        'method': 'tools/call',
        'params': {
            'name': tool_name,
            'arguments': arguments,
        }
    }

    try:
        response = requests.post(
            connection.mcp_endpoint_url,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        if 'error' in result:
            log.write({
                'state': 'failed',
                'error_message': result['error'].get('message', 'Unknown'),
            })
            raise UserError(_('MCP Error: %s') % result['error']['message'])

        log.write({
            'state': 'success',
            'result': json.dumps(result.get('result', {})),
        })
        return result['result']

    except requests.exceptions.ConnectionError:
        log.write({'state': 'failed', 'error_message': 'Connection refused'})
        raise UserError(_('Cannot reach client MCP server at %s') %
                        connection.mcp_endpoint_url)
```

## Security Rules

- Never log raw MCP API keys — use `connection._get_decrypted_key()`
- Operation logs must be filtered by client: users only see their own
- The `never_automate` tier must raise `UserError` immediately, not queue
