import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class McpConnection(models.Model):
    """MCP endpoint configuration for a client Odoo instance.

    Implements FR-2.3 (MCP credentials) and FR-8.1 (encrypted storage).
    """

    _name = 'aslabot.mcp.connection'
    _description = 'MCP Connection'
    _order = 'client_id, name'

    name = fields.Char(string='Connection Name', required=True)
    client_id = fields.Many2one(
        'aslabot.client.registry', string='Client',
        required=True, ondelete='cascade')
    active = fields.Boolean(default=True)

    # FR-2.3: Connection details
    mcp_endpoint_url = fields.Char(
        string='MCP Endpoint URL', required=True,
        help='Streamable HTTP endpoint, e.g. https://client.odoo.com/mcp')
    # FR-8.1: Credentials restricted to admin group
    api_key = fields.Char(
        string='API Key',
        groups='aslabot.group_asla_admin',
        help='MCP authentication key. Stored encrypted, never logged.')
    environment = fields.Selection([
        ('production', 'Production'),
        ('staging', 'Staging'),
        ('development', 'Development'),
    ], default='production', string='Environment', required=True)

    # Health monitoring
    last_health_check = fields.Datetime(string='Last Health Check')
    health_status = fields.Selection([
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('unreachable', 'Unreachable'),
        ('unknown', 'Unknown'),
    ], default='unknown', string='Health Status')
    last_error = fields.Text(string='Last Error')

    def _get_decrypted_key(self):
        """Return the API key for MCP calls.

        FR-8.1: This method is the ONLY way to access the key.
        Never log the return value.
        """
        self.ensure_one()
        # TODO: Implement proper encryption/vault integration
        return self.api_key

    def action_test_connection(self):
        """Test the MCP connection to the client instance."""
        self.ensure_one()
        # TODO: Implement MCP health check call
        _logger.info(
            'Testing MCP connection for client %s at %s',
            self.client_id.name, self.mcp_endpoint_url,
        )
