import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class OperationLog(models.Model):
    """Audit log of every MCP operation executed on a client instance.

    Implements FR-4.5 (audit logging).
    """

    _name = 'aslabot.operation.log'
    _description = 'MCP Operation Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    ticket_id = fields.Many2one(
        'aslabot.ticket', string='Ticket', ondelete='set null', index=True)
    client_id = fields.Many2one(
        'aslabot.client.registry', string='Client',
        required=True, index=True)
    plan_id = fields.Many2one(
        'aslabot.operation.plan', string='Operation Plan', ondelete='set null')

    # FR-4.5: Required log fields
    target_model = fields.Char(string='Target Model', required=True)
    method = fields.Char(string='Method', required=True)
    arguments = fields.Text(
        string='Arguments',
        help='Sanitized JSON. Never contains credentials.')
    result = fields.Text(string='Result')
    error_message = fields.Text(string='Error Message')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], default='pending', string='Status', required=True, index=True)

    execution_duration = fields.Float(
        string='Duration (seconds)',
        help='Time taken to execute the MCP call.')
    executed_by = fields.Many2one(
        'res.users', string='Executed By',
        default=lambda self: self.env.uid)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    def _compute_display_name(self):
        for log in self:
            log.display_name = f"{log.method} on {log.target_model}"
