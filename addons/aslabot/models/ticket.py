import logging
import re

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


def _md_to_html(text):
    """Render the model's Markdown answer to safe HTML for the chatter.

    odoo-asla-ai returns Markdown (headings, **bold**, numbered/bullet steps);
    posting it raw shows the markers literally and collapses newlines. This
    converts the common cases so the answer is readable in the chatter.
    """
    def inline(chunk):
        s = str(escape(chunk))
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
        return s

    parts = []
    list_tag = None
    for line in (text or '').split('\n'):
        heading = re.match(r'^\s*#{1,6}\s+(.*)', line)
        bullet = re.match(r'^\s*[-*]\s+(.*)', line)
        numbered = re.match(r'^\s*\d+[.)]\s+(.*)', line)
        if heading:
            if list_tag:
                parts.append(f'</{list_tag}>')
                list_tag = None
            parts.append(f'<p><b>{inline(heading.group(1))}</b></p>')
        elif bullet or numbered:
            want = 'ul' if bullet else 'ol'
            if list_tag != want:
                if list_tag:
                    parts.append(f'</{list_tag}>')
                parts.append(f'<{want}>')
                list_tag = want
            parts.append(f'<li>{inline((bullet or numbered).group(1))}</li>')
        else:
            if list_tag:
                parts.append(f'</{list_tag}>')
                list_tag = None
            if line.strip():
                parts.append(f'<p>{inline(line)}</p>')
    if list_tag:
        parts.append(f'</{list_tag}>')
    return ''.join(parts)

# Map ticket category to an odoo-asla-ai advisory role. AslaBot tickets are
# Odoo tasks, so they default to the Odoo advisory role (OA).
ROLE_BY_CATEGORY = {
    'admin': 'OA',
    'support': 'OA',
    'customization': 'OA',
}

# FR-3.2: Risk classification by operation type
OPERATION_RISK = {
    'read_only_query': 'low',
    'configuration_change': 'medium',
    'data_modification': 'medium',
    'module_customization': 'high',
    'bug_investigation': 'medium',
    'new_feature_request': 'high',
}

# FR-3.3: AI model routing by operation type
AI_TIER_ROUTING = {
    'read_only_query': 'gemma_local',
    'configuration_change': 'gemma_local',
    'data_modification': 'gemma_local',
    'bug_investigation': 'gemma_local',
    'module_customization': 'claude_api',
    'new_feature_request': 'claude_api',
}


class AslaTicket(models.Model):
    """Support ticket received from a client organization.

    Implements FR-1.x (Ticket Intake) and FR-3.x (Triage & Classification).
    """

    _name = 'aslabot.ticket'
    _description = 'Support Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    # FR-1.5: Unique ticket reference
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    description = fields.Html(string='Description', required=True)
    summary = fields.Char(string='Summary')

    # FR-1.2: Required ticket fields
    client_id = fields.Many2one(
        'aslabot.client.registry',
        string='Client',
        required=True,
        tracking=True,
    )
    client_instance_url = fields.Char(string='Odoo Instance URL')
    client_odoo_version = fields.Selection(
        related='client_id.odoo_version',
        string='Odoo Version',
        store=True,
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1', string='Priority', tracking=True)
    category = fields.Selection([
        ('admin', 'Administration'),
        ('support', 'Support'),
        ('customization', 'Customization'),
    ], string='Category', required=True, tracking=True)

    # FR-3.1: Auto-classification
    operation_type = fields.Selection([
        ('read_only_query', 'Read-Only Query'),
        ('configuration_change', 'Configuration Change'),
        ('data_modification', 'Data Modification'),
        ('module_customization', 'Module Customization'),
        ('bug_investigation', 'Bug Investigation'),
        ('new_feature_request', 'New Feature Request'),
    ], string='Operation Type', tracking=True)

    # FR-3.2: Risk assessment
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Risk Level', compute='_compute_risk_level', store=True)

    # FR-3.3: AI model routing
    assigned_model_tier = fields.Selection([
        ('gemma_local', 'gemma4:e4b (Local)'),
        ('claude_api', 'Claude Sonnet (API)'),
    ], string='AI Model', compute='_compute_assigned_model_tier', store=True)

    # Workflow state
    state = fields.Selection([
        ('draft', 'Draft'),
        ('triaged', 'Triaged'),
        ('in_progress', 'In Progress'),
        ('executing', 'Executing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('escalated', 'Escalated to Human'),
    ], default='draft', string='Status', required=True, tracking=True)

    # FR-1.5: Response category
    response_category = fields.Selection([
        ('automated', 'Automated'),
        ('needs_review', 'Needs Review'),
        ('requires_consultation', 'Requires Consultation'),
    ], string='Response Category')

    # FR-1.4: Attachments handled via mail.thread chatter

    # FR-7.1: Resolution feedback
    resolution_feedback = fields.Selection([
        ('resolved', 'Resolved'),
        ('partial', 'Partially Resolved'),
        ('unresolved', 'Unresolved'),
    ], string='Resolution Feedback', tracking=True)
    resolution_notes = fields.Text(string='Resolution Notes')

    # Relational
    operation_plan_ids = fields.One2many(
        'aslabot.operation.plan', 'ticket_id', string='Operation Plans')
    operation_log_ids = fields.One2many(
        'aslabot.operation.log', 'ticket_id', string='Operation Logs')
    operation_count = fields.Integer(
        compute='_compute_operation_count', string='Operations')

    # FR-3.4: Escalation tracking
    escalated = fields.Boolean(default=False)
    escalation_reason = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        """FR-1.5: Assign unique ticket reference on creation."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'aslabot.ticket') or _('New')
        return super().create(vals_list)

    @api.depends('operation_type')
    def _compute_risk_level(self):
        """FR-3.2: Assess risk based on operation type."""
        for ticket in self:
            ticket.risk_level = OPERATION_RISK.get(
                ticket.operation_type, 'medium')

    @api.depends('operation_type')
    def _compute_assigned_model_tier(self):
        """FR-3.3: Route to appropriate AI tier."""
        for ticket in self:
            ticket.assigned_model_tier = AI_TIER_ROUTING.get(
                ticket.operation_type, 'gemma_local')

    def _compute_operation_count(self):
        for ticket in self:
            ticket.operation_count = len(ticket.operation_log_ids)

    def action_triage(self):
        """Run triage classification on the ticket."""
        self.ensure_one()
        if not self.operation_type:
            raise UserError(_(
                'Set the operation type before triaging.'))
        self.write({
            'state': 'triaged',
            'response_category': self._determine_response_category(),
        })
        self.message_post(
            body=_(
                'Ticket triaged: %s risk, routed to %s',
                self.risk_level,
                dict(self._fields['assigned_model_tier'].selection).get(
                    self.assigned_model_tier, ''),
            ),
            message_type='notification',
        )
        # FR-6.4: post a grounded suggested answer; best-effort so triage still
        # succeeds if the language service is unavailable.
        try:
            self.action_ai_reply()
        except Exception as exc:  # noqa: BLE001 - AI reply is best-effort
            _logger.warning('AI reply failed for %s: %s', self.name, exc)
            self.message_post(
                body=_('AI reply unavailable: %s', exc),
                message_type='notification',
            )

    def action_escalate(self, reason=''):
        """FR-3.4: Escalate ticket to human operator."""
        self.ensure_one()
        self.write({
            'state': 'escalated',
            'escalated': True,
            'escalation_reason': reason,
        })
        self.message_post(
            body=_('Ticket escalated to human operator. Reason: %s', reason),
            message_type='notification',
        )

    def action_mark_done(self):
        """Mark ticket as resolved."""
        self.ensure_one()
        self.write({'state': 'done'})

    def action_mark_failed(self):
        """Mark ticket as failed."""
        self.ensure_one()
        self.write({'state': 'failed'})

    def _determine_response_category(self):
        """FR-1.5: Determine response category based on triage."""
        self.ensure_one()
        if self.risk_level == 'low' and self.assigned_model_tier == 'gemma_local':
            return 'automated'
        elif self.risk_level == 'high':
            return 'requires_consultation'
        return 'needs_review'

    def _ai_reply_role(self):
        """Map the ticket category to an odoo-asla-ai role (defaults to OA)."""
        self.ensure_one()
        return ROLE_BY_CATEGORY.get(self.category, 'OA')

    def _ai_client_key(self):
        """Stable per-tenant key for the odoo-asla-ai client corpus."""
        self.ensure_one()
        return f"reg{self.client_id.id}"

    def _ai_query(self):
        """Plain-text query built from the ticket for the language brain."""
        self.ensure_one()
        parts = [self.summary or '', html2plaintext(self.description or '')]
        return '\n'.join(part for part in parts if part).strip()

    def action_ai_reply(self):
        """Fetch a grounded answer from odoo-asla-ai and post it to the chatter.

        Advisory only: this posts a *suggested* answer for the operator/client and
        never executes anything on a client Odoo (execution stays in the MCP layer).

        Returns:
            dict: the raw brain response (answer, sources, tok_s).
        """
        self.ensure_one()
        query = self._ai_query()
        if not query:
            raise UserError(_('Ticket has no description to answer.'))
        result = self.env['aslabot.brain'].answer(
            self._ai_reply_role(), query, client_id=self._ai_client_key(),
        )
        answer = result.get('answer') or _('(no answer)')
        sources = ', '.join(s.get('source', '') for s in result.get('sources', []))
        label = escape(_('AI suggested answer:'))
        body = f'<p><b>{label}</b></p>' + _md_to_html(answer)
        if sources:
            grounded = escape(_('Grounded on: %s', sources))
            body += f'<p><i>{grounded}</i></p>'
        self.message_post(body=Markup(body), message_type='comment')
        return result
