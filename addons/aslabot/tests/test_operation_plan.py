from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestOperationPlan(TransactionCase):
    """Tests for aslabot.operation.plan model (FR-4.x)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Plan Test Partner',
        })
        cls.client = cls.env['aslabot.client.registry'].create({
            'name': 'Plan Test Client',
            'partner_id': cls.partner.id,
            'odoo_version': '18.0',
        })
        cls.ticket = cls.env['aslabot.ticket'].create({
            'client_id': cls.client.id,
            'description': '<p>Test</p>',
            'category': 'admin',
        })

    def _create_plan(self, **kwargs):
        vals = {
            'ticket_id': self.ticket.id,
            'client_id': self.client.id,
            'target_model': 'res.partner',
            'method': 'search_read',
        }
        vals.update(kwargs)
        return self.env['aslabot.operation.plan'].create(vals)

    def test_permission_tier_auto_execute(self):
        """FR-4.3: Read methods get auto_execute tier."""
        plan = self._create_plan(method='search_read')
        self.assertEqual(plan.permission_tier, 'auto_execute')

        plan2 = self._create_plan(method='fields_get')
        self.assertEqual(plan2.permission_tier, 'auto_execute')

    def test_permission_tier_confirm(self):
        """FR-4.3: Write on non-sensitive models gets confirm tier."""
        plan = self._create_plan(
            target_model='res.partner', method='write')
        self.assertEqual(plan.permission_tier, 'confirm_then_execute')

    def test_permission_tier_never_automate(self):
        """FR-4.3: Operations on sensitive models get never_automate."""
        for model in ('res.users', 'ir.rule', 'account.move'):
            plan = self._create_plan(
                target_model=model, method='write')
            self.assertEqual(
                plan.permission_tier, 'never_automate',
                f'{model} should be never_automate',
            )

    def test_never_automate_blocks_approval(self):
        """FR-4.3: never_automate plans cannot request approval."""
        plan = self._create_plan(
            target_model='res.users', method='write')
        plan.write({'state': 'validated'})
        with self.assertRaises(UserError):
            plan.action_request_approval()

    def test_approval_workflow(self):
        """FR-4.4: Plans go through approval before execution."""
        plan = self._create_plan(
            target_model='res.partner', method='write')
        plan.action_validate_dry_run()
        self.assertEqual(plan.state, 'validated')

        plan.action_request_approval()
        self.assertEqual(plan.state, 'pending_approval')

        plan.action_approve()
        self.assertEqual(plan.state, 'approved')
        self.assertTrue(plan.approver_id)

    def test_execute_requires_approval(self):
        """Execution blocked without approval for confirm tier."""
        plan = self._create_plan(
            target_model='res.partner', method='write')
        with self.assertRaises(UserError):
            plan.action_execute()
