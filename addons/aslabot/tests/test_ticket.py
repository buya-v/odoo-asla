from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestAslaTicket(TransactionCase):
    """Tests for aslabot.ticket model (FR-1.x, FR-3.x)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Client Partner',
        })
        cls.client = cls.env['aslabot.client.registry'].create({
            'name': 'Test Client Org',
            'partner_id': cls.partner.id,
            'odoo_version': '18.0',
            'delivery_mode': 'mcp',
        })

    def _create_ticket(self, **kwargs):
        vals = {
            'client_id': self.client.id,
            'description': '<p>Test issue description</p>',
            'category': 'support',
            'operation_type': 'read_only_query',
        }
        vals.update(kwargs)
        return self.env['aslabot.ticket'].create(vals)

    def test_ticket_sequence(self):
        """FR-1.5: Ticket gets unique ASLA- prefixed reference."""
        ticket = self._create_ticket()
        self.assertTrue(
            ticket.name.startswith('ASLA-'),
            f'Ticket reference should start with ASLA-, got {ticket.name}',
        )

    def test_ticket_default_state(self):
        """Ticket starts in draft state."""
        ticket = self._create_ticket()
        self.assertEqual(ticket.state, 'draft')

    def test_risk_level_computation(self):
        """FR-3.2: Risk level computed from operation type."""
        ticket = self._create_ticket(operation_type='read_only_query')
        self.assertEqual(ticket.risk_level, 'low')

        ticket2 = self._create_ticket(operation_type='module_customization')
        self.assertEqual(ticket2.risk_level, 'high')

        ticket3 = self._create_ticket(operation_type='data_modification')
        self.assertEqual(ticket3.risk_level, 'medium')

    def test_ai_tier_routing(self):
        """FR-3.3: AI model routed by operation type."""
        ticket_simple = self._create_ticket(
            operation_type='read_only_query')
        self.assertEqual(ticket_simple.assigned_model_tier, 'qwen_local')

        ticket_complex = self._create_ticket(
            operation_type='module_customization')
        self.assertEqual(ticket_complex.assigned_model_tier, 'claude_api')

    def test_triage_action(self):
        """FR-3.1: Triage sets state and response category."""
        ticket = self._create_ticket(operation_type='read_only_query')
        ticket.action_triage()
        self.assertEqual(ticket.state, 'triaged')
        self.assertEqual(ticket.response_category, 'automated')

    def test_triage_requires_operation_type(self):
        """Triage fails without operation type."""
        ticket = self._create_ticket(operation_type=False)
        with self.assertRaises(UserError):
            ticket.action_triage()

    def test_escalation(self):
        """FR-3.4: Escalation sets state and records reason."""
        ticket = self._create_ticket()
        ticket.action_escalate(reason='Client requested human review')
        self.assertEqual(ticket.state, 'escalated')
        self.assertTrue(ticket.escalated)
        self.assertIn('human review', ticket.escalation_reason)

    def test_response_category_high_risk(self):
        """FR-1.5: High-risk tickets get consultation response category."""
        ticket = self._create_ticket(
            operation_type='new_feature_request')
        ticket.action_triage()
        self.assertEqual(ticket.response_category, 'requires_consultation')
