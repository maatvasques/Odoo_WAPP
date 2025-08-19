# -*- coding: utf-8 -*-
{
    'name': 'Integração de Vendas com WhatsApp (WAHA)',
    'version': '17.0.1.0',
    'summary': 'Envia notificações de pedidos de venda e boletos via WhatsApp usando a API WAHA.',
    'description': """
        Este módulo adiciona um botão "Enviar por WhatsApp" aos Pedidos de Venda, permitindo:
        - Enviar mensagens personalizadas para clientes.
        - Anexar e fazer upload de boletos para uma API externa.
        - Enviar notificações automáticas na confirmação e cancelamento de pedidos.
    """,
    'author': 'Seu Nome',
    'category': 'Sales/Sales',
    'depends': [
        'sale_management', # Dependência do módulo de Vendas
        'mail',            # Dependência para o chatter e anexos
    ],
    'data': [
        'security/ir.model.access.csv', # Não esqueça da segurança!
        'wizards/whatsapp_composer_view.xml',
        'views/sale_order_view.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}