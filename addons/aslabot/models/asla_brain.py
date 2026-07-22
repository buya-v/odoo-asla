import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Config parameter holding the odoo-asla-ai base URL (see docs/integration).
_URL_PARAM = 'aslabot.asla_ai_url'
_DEFAULT_URL = 'http://localhost:8080'
_TIMEOUT = 600  # CPU generation can take a while


class AslaBrain(models.AbstractModel):
    """Client for the odoo-asla-ai grounded-language service.

    odoo-asla-ai is the Mongolian language/knowledge brain; AslaBot calls it for
    grounded answers and feeds it live client Odoo config from read-only MCP
    introspection. Advisory only — execution stays in AslaBot's MCP layer.

    Supports FR-3.x (triage responses), FR-6.x (per-client context).
    """

    _name = 'aslabot.brain'
    _description = 'odoo-asla-ai Language Brain Client'

    @api.model
    def _base_url(self):
        # sudo(): reading a system config parameter, not user data.
        url = self.env['ir.config_parameter'].sudo().get_param(_URL_PARAM, _DEFAULT_URL)
        return url.rstrip('/')

    @api.model
    def _post(self, path, payload):
        url = f"{self._base_url()}{path}"
        try:
            resp = requests.post(url, json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            _logger.error("odoo-asla-ai call failed: %s %s", url, exc)
            raise UserError(_("Language service unavailable: %s") % exc) from exc

    @api.model
    def answer(self, role, query, client_id=None, lang='mn'):
        """Return a grounded answer from odoo-asla-ai.

        Args:
            role: 'BA', 'AM', or 'OA'.
            query: the user/ticket question, in the target language.
            client_id: external client key scoping retrieval to that tenant
                (matches the id used in push_client_context). None = shared corpus.
            lang: language pack code ('mn', 'kk', …).

        Returns:
            dict with keys ``answer``, ``sources`` (audit trail), ``tok_s``.
        """
        return self._post('/api/answer', {
            'role': role, 'query': query, 'client_id': client_id, 'lang': lang,
        })

    @api.model
    def push_client_context(self, client_id, config):
        """Send a client's live Odoo config (from read-only MCP) to odoo-asla-ai.

        Makes OA advice for this client config-specific (e.g. flags tasks that need
        an uninstalled module). ``config`` keys: odoo_version, edition,
        modules_installed, modules_absent, ui_language, vat, notes.
        """
        return self._post('/api/client/introspect', {
            'client_id': client_id, 'config': config,
        })
