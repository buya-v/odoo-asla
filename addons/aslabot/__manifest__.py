{
    'name': 'AslaBot',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'AI-Powered Odoo Managed Services Platform',
    'description': """
AslaBot — AI-Powered Odoo Managed Services
===========================================

Receives customer support tickets, triages them via AI (Qwen 3 14B / Claude Sonnet),
and executes admin, support, and customization tasks on client Odoo instances
via MCP (Model Context Protocol) or generates deployable codebase packages.

Features:
- Multi-channel ticket intake (web, email, messaging)
- AI-powered ticket triage and classification
- MCP-based remote execution on client Odoo instances
- Codebase delivery for clients without MCP
- Per-client context management and knowledge base
- Full audit logging and security controls
    """,
    'author': 'ASLA LLC',
    'website': 'https://odoo.asla.mn',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
    ],
    'data': [
        'security/aslabot_groups.xml',
        'security/ir.model.access.csv',
        'security/aslabot_rules.xml',
        'data/ir_sequence_data.xml',
        'views/ticket_views.xml',
        'views/client_registry_views.xml',
        'views/operation_log_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
