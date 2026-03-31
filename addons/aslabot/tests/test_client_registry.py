from odoo.tests.common import TransactionCase


class TestClientRegistry(TransactionCase):
    """Tests for aslabot.client.registry model (FR-2.x)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Registry Test Partner',
        })

    def test_client_creation(self):
        """FR-2.1: Client record stores required fields."""
        client = self.env['aslabot.client.registry'].create({
            'name': 'Acme Corp',
            'partner_id': self.partner.id,
            'odoo_version': '18.0',
            'service_tier': 'premium',
            'delivery_mode': 'mcp',
        })
        self.assertEqual(client.name, 'Acme Corp')
        self.assertEqual(client.odoo_version, '18.0')
        self.assertEqual(client.mcp_status, 'not_configured')

    def test_delivery_modes(self):
        """FR-2.2: All delivery modes can be set."""
        for mode in ('mcp', 'codebase', 'hybrid'):
            client = self.env['aslabot.client.registry'].create({
                'name': f'Client {mode}',
                'partner_id': self.partner.id,
                'odoo_version': '18.0',
                'delivery_mode': mode,
            })
            self.assertEqual(client.delivery_mode, mode)

    def test_ticket_count(self):
        """Client ticket count reflects linked tickets."""
        client = self.env['aslabot.client.registry'].create({
            'name': 'Count Test',
            'partner_id': self.partner.id,
            'odoo_version': '18.0',
        })
        self.assertEqual(client.ticket_count, 0)

        self.env['aslabot.ticket'].create({
            'client_id': client.id,
            'description': '<p>Test</p>',
            'category': 'admin',
        })
        client.invalidate_recordset()
        self.assertEqual(client.ticket_count, 1)
