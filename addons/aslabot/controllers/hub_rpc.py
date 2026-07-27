import json
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

ERR_UNAUTHORIZED = -32001
ERR_UNKNOWN_CLIENT = -32002
ERR_INTERNAL = -32603
PROTOCOL_VERSION = "1.0"

# Until a real classifier lands (FR-3.1), submitted tickets default to the
# lowest-risk operation type so triage + advisory answer can run.
DEFAULT_OPERATION_TYPE = 'read_only_query'


class AslaHubRpc(http.Controller):
    """Intake endpoint (bot -> hub). Implements hub-bot-protocol.md §5 over
    JSON-RPC 2.0. `session.pair` bootstraps; other methods use the bot_token.

    auth='none': machine endpoint with token auth, not an Odoo session.
    """

    @http.route('/asla/hub/rpc', type='http', auth='none', methods=['POST'], csrf=False)
    def rpc(self, **_kw):
        try:
            req = json.loads(request.httprequest.get_data() or b'{}')
        except ValueError:
            return self._resp(None, error=(ERR_INTERNAL, 'Invalid JSON'))
        rpc_id, method, params = req.get('id'), req.get('method'), req.get('params') or {}
        env = request.env(su=True)  # sudo(): token-authenticated machine endpoint

        try:
            if method == 'session.pair':
                result = self._pair(env, params)
            else:
                link = env['aslabot.bot.link'].link_for_token(env, self._bearer())
                if not link:
                    return self._resp(rpc_id, error=(ERR_UNAUTHORIZED, 'Bad or missing token'))
                if params.get('client_id') and params['client_id'] != link.client_key:
                    return self._resp(rpc_id, error=(ERR_UNKNOWN_CLIENT, 'client_id mismatch'))
                result = self._dispatch(env, link, method, params)
        except Exception as exc:
            _logger.exception('hub rpc %s failed', method)
            return self._resp(rpc_id, error=(ERR_INTERNAL, str(exc)))
        return self._resp(rpc_id, result=result)

    # --- helpers ---------------------------------------------------------------

    def _bearer(self):
        h = request.httprequest.headers.get('Authorization', '')
        return h[7:] if h.startswith('Bearer ') else ''

    def _pair(self, env, params):
        return env['aslabot.bot.link'].complete_pairing(
            params.get('enrollment_code'), params.get('bot'))

    def _dispatch(self, env, link, method, params):
        if method == 'ticket.submit':
            return self._ticket_submit(env, link, params)
        if method == 'client.push_config':
            env['aslabot.brain'].push_client_context(link.client_key, params.get('config') or {})
            return {'ok': True}
        if method == 'operation.report_result':
            env['aslabot.operation.log'].create({
                'client_id': link.client_id.id,
                'target_model': params.get('operation_ref', ''),
                'method': 'report:' + (params.get('status') or ''),
                'result': json.dumps(params.get('result')),
                'error_message': params.get('error'),
                'state': 'success' if params.get('status') == 'success' else 'failed',
            })
            return {'ok': True}
        if method == 'heartbeat':
            link.sudo().last_heartbeat = fields.Datetime.now()
            return {'ok': True, 'server_ts': fields.Datetime.now().isoformat() + 'Z'}
        return {'ok': False, 'error': f'unknown method {method}'}

    def _ticket_submit(self, env, link, params):
        ticket = env['aslabot.ticket'].create({
            'client_id': link.client_id.id,
            'summary': params.get('subject'),
            'description': params.get('body') or '<p></p>',
            'category': params.get('category', 'support'),
            'priority': params.get('priority', '1'),
            'operation_type': DEFAULT_OPERATION_TYPE,
            'bot_link_id': link.id,
            'bot_ref': params.get('bot_ref'),
        })
        ticket.write({'state': 'triaged',
                      'response_category': ticket._determine_response_category()})
        # Grounded advisory answer via odoo-asla-ai, then relay to the bot.
        try:
            result = ticket.action_ai_reply()
            link.post_answer(
                params.get('bot_ref'), result.get('answer', ''),
                sources=[s.get('source') for s in result.get('sources', [])],
                response_category=ticket.response_category)
        except Exception as exc:  # noqa: BLE001 - answer/relay is best-effort
            _logger.warning('answer/relay for %s failed: %s', ticket.name, exc)
        return {'hub_ref': ticket.name, 'state': ticket.state}

    def _resp(self, rpc_id, result=None, error=None):
        body = {'jsonrpc': '2.0', 'id': rpc_id}
        if error:
            body['error'] = {'code': error[0], 'message': error[1]}
        else:
            body['result'] = result
        return request.make_response(
            json.dumps(body), headers=[('Content-Type', 'application/json')])
