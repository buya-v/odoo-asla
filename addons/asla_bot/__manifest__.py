{
    'name': 'AslaBot Agent (odoo.asla.bot)',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Client-side agent for AslaBot managed services',
    'description': """
AslaBot Agent — Client-side companion to odoo.asla.hub
======================================================

Installed on a client's own Odoo. Lets the client's users raise tickets
natively, relays them to the AslaBot hub, receives grounded answers back into
the ticket chatter, and executes hub-requested operations locally under
client-owned permission tiers.

Implements the bot side of the Hub <-> Bot protocol (see hub-bot-protocol.md):
  - intake  (bot -> hub): ticket.submit, client.push_config, operation.report_result, heartbeat
  - control (hub -> bot): ticket.post_answer, ticket.set_state, operation.dry_run, operation.request
""",
    'author': 'ASLA LLC',
    'website': 'https://odoo.asla.mn',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        'security/asla_bot_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/asla_bot_data.xml',
        'views/hub_connection_views.xml',
        'views/bot_ticket_views.xml',
        'views/bot_operation_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
}
