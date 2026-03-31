---
name: odoo-module
description: |
  Odoo 18.0 module development patterns for AslaBot. Use when creating models,
  views, security rules, wizards, controllers, or tests. Covers ORM API,
  view XML, ir.model.access.csv format, mail.thread integration, and
  Odoo-specific Python patterns.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Odoo 18.0 Module Development Patterns

## Model Definition

```python
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AslaTicket(models.Model):
    _name = 'aslabot.ticket'
    _description = 'Support Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'))
    description = fields.Html(string='Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('triaged', 'Triaged'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='draft', tracking=True, required=True)
    client_id = fields.Many2one('aslabot.client.registry', required=True)
    assigned_model_tier = fields.Selection([
        ('qwen_local', 'Qwen 3 14B (Local)'),
        ('claude_api', 'Claude Sonnet (API)'),
    ], string='AI Model')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'aslabot.ticket') or _('New')
        return super().create(vals_list)
```

## Security: ir.model.access.csv

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
aslabot.access_ticket_user,aslabot.ticket.user,aslabot.model_aslabot_ticket,aslabot.group_asla_user,1,1,1,0
aslabot.access_ticket_admin,aslabot.ticket.admin,aslabot.model_aslabot_ticket,aslabot.group_asla_admin,1,1,1,1
```

Note: `model_id:id` uses format `module.model_[model_name_with_underscores]`
where dots in `_name` become underscores.

## View XML

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Form View -->
    <record id="view_aslabot_ticket_form" model="ir.ui.view">
        <field name="name">aslabot.ticket.form</field>
        <field name="model">aslabot.ticket</field>
        <field name="arch" type="xml">
            <form string="Ticket">
                <header>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,triaged,in_progress,done"/>
                </header>
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="client_id"/>
                        </group>
                        <group>
                            <field name="state"/>
                            <field name="assigned_model_tier"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Description">
                            <field name="description"/>
                        </page>
                    </notebook>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <!-- Action -->
    <record id="action_aslabot_ticket" model="ir.actions.act_window">
        <field name="name">Tickets</field>
        <field name="res_model">aslabot.ticket</field>
        <field name="view_mode">tree,form</field>
    </record>
</odoo>
```

## Tests

```python
from odoo.tests.common import TransactionCase


class TestAslaTicket(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env['aslabot.client.registry'].create({
            'name': 'Test Client',
            'partner_id': cls.env.ref('base.res_partner_1').id,
            'odoo_version': '18.0',
        })

    def test_ticket_creation_sequence(self):
        """FR-1.5: Ticket gets unique reference on creation."""
        ticket = self.env['aslabot.ticket'].create({
            'client_id': self.client.id,
            'description': 'Test issue',
        })
        self.assertNotEqual(ticket.name, 'New')
        self.assertTrue(ticket.name.startswith('ASLA'))
```

## Common Anti-Patterns

```python
# BAD: SQL injection risk
self.env.cr.execute("SELECT * FROM res_partner WHERE name = '%s'" % name)

# GOOD: Parameterized query
self.env.cr.execute("SELECT * FROM res_partner WHERE name = %s", (name,))

# BAD: Hardcoded ID
partner = self.env['res.partner'].browse(42)

# GOOD: XML ID reference
partner = self.env.ref('base.res_partner_1')

# BAD: sudo without justification
records = self.env['model'].sudo().search([])

# GOOD: sudo with documented reason
# sudo() required: cross-company record rule bypass for MCP service account
records = self.env['model'].sudo().search([])
```
