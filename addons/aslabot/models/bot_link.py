import logging
import secrets
import uuid

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "1.0"
_TIMEOUT = 30


class AslaBotLink(models.Model):
    """Hub side of a paired odoo.asla.bot agent.

    Holds the per-client tokens and the bot's control endpoint, and provides the
    outbound JSON-RPC client the hub uses to deliver answers and request
    operations (control channel, hub-bot-protocol.md §6). Pairing is completed
    from the intake controller's session.pair handler.
    """

    _name = 'aslabot.bot.link'
    _description = 'AslaBot Agent Link'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    client_id = fields.Many2one(
        'aslabot.client.registry', string='Client', required=True, ondelete='cascade')
    client_key = fields.Char(
        string='Client Key', compute='_compute_client_key', store=True,
        help='Stable tenant key used on the wire and for the per-client corpus.')
    bot_endpoint = fields.Char(string='Bot RPC URL', help='Learned at pairing.')
    protocol_version = fields.Char(default=PROTOCOL_VERSION, readonly=True)
    state = fields.Selection([
        ('unpaired', 'Unpaired'),
        ('enrolling', 'Enrolling'),
        ('paired', 'Paired'),
    ], default='unpaired', string='Status', tracking=True)

    enrollment_code = fields.Char(string='Enrollment Code', readonly=True, copy=False)
    # Credentials — restrict to admins; encrypt at rest before production (FR-8.1).
    bot_token = fields.Char(string='Bot Token', groups='aslabot.group_asla_admin', copy=False)
    hub_token = fields.Char(string='Hub Token', groups='aslabot.group_asla_admin', copy=False)
    last_heartbeat = fields.Datetime(string='Last Heartbeat', readonly=True)

    @api.depends('client_id')
    def _compute_client_key(self):
        for link in self:
            link.client_key = f"reg{link.client_id.id}" if link.client_id else False

    # --- pairing ---------------------------------------------------------------

    def action_generate_enrollment(self):
        """Issue a one-time enrollment code for the client to enter in their bot."""
        self.ensure_one()
        self.write({'enrollment_code': secrets.token_urlsafe(12), 'state': 'enrolling'})
        self.message_post(body=_('Enrollment code generated. Share it with the client.'))

    def complete_pairing(self, enrollment_code, bot_info):
        """session.pair (spec §4): validate the code, mint tokens, store endpoint.

        Returns the dict the bot expects: client_id, bot_token, hub_token.
        """
        link = self.search([('enrollment_code', '=', enrollment_code),
                             ('state', '=', 'enrolling')], limit=1)
        if not link:
            raise UserError(_('Invalid or already-used enrollment code.'))
        link.write({
            'bot_endpoint': (bot_info or {}).get('endpoint'),
            'bot_token': secrets.token_urlsafe(24),
            'hub_token': secrets.token_urlsafe(24),
            'enrollment_code': False,
            'state': 'paired',
        })
        link.message_post(body=_('Bot paired from %s.') % link.bot_endpoint)
        return {'client_id': link.client_key,
                'bot_token': link.bot_token, 'hub_token': link.hub_token}

    # --- outbound control (hub -> bot) -----------------------------------------

    def _control(self, method, params):
        self.ensure_one()
        if self.state != 'paired' or not self.bot_endpoint:
            raise UserError(_('Bot is not paired.'))
        payload = {
            'jsonrpc': '2.0', 'id': uuid.uuid4().int % 1_000_000, 'method': method,
            'params': {'protocol_version': PROTOCOL_VERSION, 'client_id': self.client_key,
                       'correlation_id': uuid.uuid4().hex,
                       'ts': fields.Datetime.now().isoformat() + 'Z', **params},
        }
        headers = {'Content-Type': 'application/json',
                   'Authorization': f'Bearer {self.hub_token}'}
        try:
            resp = requests.post(self.bot_endpoint, json=payload, headers=headers, timeout=_TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException as exc:
            _logger.warning('control %s to bot failed: %s', method, exc)
            raise UserError(_('Bot unreachable: %s') % exc) from exc
        if body.get('error'):
            raise UserError(_('Bot error %(c)s: %(m)s') % {
                'c': body['error'].get('code'), 'm': body['error'].get('message')})
        return body.get('result', {})

    def post_answer(self, bot_ref, body_html, sources=None, response_category=None):
        return self._control('ticket.post_answer', {
            'bot_ref': bot_ref, 'body_html': body_html,
            'sources': sources or [], 'response_category': response_category})

    def set_state(self, bot_ref, state, note=None):
        return self._control('ticket.set_state', {
            'bot_ref': bot_ref, 'state': state, 'note': note})

    def request_operation(self, bot_ref, operation_ref, target_model, method, arguments, hub_tier):
        return self._control('operation.request', {
            'bot_ref': bot_ref, 'operation_ref': operation_ref,
            'target_model': target_model, 'method': method,
            'arguments': arguments, 'hub_tier': hub_tier})

    @staticmethod
    def link_for_token(env, bot_token):
        return env['aslabot.bot.link'].sudo().search(
            [('bot_token', '=', bot_token), ('state', '=', 'paired')], limit=1)
