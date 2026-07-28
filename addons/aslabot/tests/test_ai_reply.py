from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAiReply(TransactionCase):
    """action_ai_reply posts a grounded answer from odoo-asla-ai to the chatter."""

    def setUp(self):
        super().setUp()
        partner = self.env['res.partner'].create({'name': 'Acme Co'})
        self.client = self.env['aslabot.client.registry'].create({
            'name': 'Acme Co',
            'partner_id': partner.id,
            'odoo_version': '18.0',
        })
        self.ticket = self.env['aslabot.ticket'].create({
            'description': '<p>НӨАТ 10% тохиргоо хийх алхмуудыг заа.</p>',
            'summary': 'VAT setup',
            'client_id': self.client.id,
            'category': 'support',
            'operation_type': 'read_only_query',
        })

    def _fake_answer(self):
        return {
            'answer': 'Алхам 1: Тохиргоо (Settings) руу орно.',
            'sources': [{'source': 'odoo/18/taxes.md', 'score': 0.7}],
            'tok_s': 20.0,
        }

    def test_action_ai_reply_posts_answer(self):
        brain = type(self.env['aslabot.brain'])
        with patch.object(brain, 'answer', return_value=self._fake_answer()) as mocked:
            self.ticket.action_ai_reply()
            mocked.assert_called_once()
            # role derived from category 'support' -> 'OA'; client key from registry id
            args, kwargs = mocked.call_args
            self.assertEqual(args[0], 'OA')
            self.assertEqual(kwargs.get('client_id'), f"reg{self.client.id}")
        bodies = self.ticket.message_ids.mapped('body')
        self.assertTrue(any('Алхам 1' in (b or '') for b in bodies),
                        'suggested answer should appear in the chatter')

    def test_triage_ai_reply_is_best_effort(self):
        # If the brain raises, triage must still succeed (non-blocking).
        brain = type(self.env['aslabot.brain'])
        with patch.object(brain, 'answer', side_effect=Exception('service down')):
            self.ticket.action_triage()
        self.assertEqual(self.ticket.state, 'triaged')
