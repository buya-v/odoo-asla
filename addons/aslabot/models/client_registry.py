import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class ClientRegistry(models.Model):
    """Client organization registered for AslaBot managed services.

    Implements FR-2.x (Client Registry).
    """

    _name = 'aslabot.client.registry'
    _description = 'Client Organization'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Organization Name', required=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True, tracking=True)
    active = fields.Boolean(default=True)

    # FR-2.2: Delivery mode
    delivery_mode = fields.Selection([
        ('mcp', 'MCP Connected'),
        ('codebase', 'Codebase Delivery'),
        ('hybrid', 'Hybrid (Supervised Sessions)'),
    ], default='mcp', required=True, string='Delivery Mode', tracking=True)

    # FR-2.1: Instance details
    odoo_version = fields.Selection([
        ('16.0', '16.0'),
        ('17.0', '17.0'),
        ('18.0', '18.0'),
        ('19.0', '19.0'),
    ], string='Odoo Version', required=True)
    instance_url = fields.Char(string='Primary Odoo URL')
    installed_modules = fields.Text(
        string='Installed Modules',
        help='Comma-separated list of installed module technical names.',
    )
    custom_models = fields.Text(
        string='Custom Models',
        help='Known custom model names on the client instance.',
    )

    # FR-2.1: Service tier
    service_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ], default='standard', string='Service Tier', tracking=True)

    # FR-2.3: MCP connection
    mcp_connection_ids = fields.One2many(
        'aslabot.mcp.connection', 'client_id', string='MCP Connections')
    mcp_status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
        ('not_configured', 'Not Configured'),
    ], default='not_configured', string='MCP Status', tracking=True)

    # Relations
    ticket_ids = fields.One2many(
        'aslabot.ticket', 'client_id', string='Tickets')
    ticket_count = fields.Integer(
        compute='_compute_ticket_count', string='Tickets')
    contact_ids = fields.Many2many(
        'res.partner', string='Contact Persons',
        help='Authorized contacts who can submit tickets.',
    )

    def _compute_ticket_count(self):
        for client in self:
            client.ticket_count = len(client.ticket_ids)

    def action_view_tickets(self):
        """Open tickets for this client."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tickets — %s', self.name),
            'res_model': 'aslabot.ticket',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id},
        }
