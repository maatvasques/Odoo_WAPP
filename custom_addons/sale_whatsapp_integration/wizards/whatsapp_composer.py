# -*- coding: utf-8 -*-
import requests
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WhatsappSaleComposer(models.TransientModel):
    _name = 'whatsapp.sale.composer'
    _description = 'WhatsApp Sale Composer'

    sale_order_id = fields.Many2one('sale.order', string="Pedido de Venda", readonly=True)
    phone_number = fields.Char(string="Número de Telefone", required=True)
    message = fields.Text(string="Mensagem", required=True)
    attachment_ids = fields.Many2many('ir.attachment', string="Anexo (Boleto)")
    
    @api.model
    def default_get(self, fields):
        """Define os valores padrão para o wizard."""
        res = super(WhatsappSaleComposer, self).default_get(fields)
        if self.env.context.get('active_model') == 'sale.order' and self.env.context.get('active_id'):
            order = self.env['sale.order'].browse(self.env.context.get('active_id'))
            
            # Mensagem padrão para envio de boleto
            message_body = _(
                "Seu pedido %s foi realizado e está sendo processado. Segue anexo o boleto para pagamento.", 
                order.name
            )
            res.update({
                'sale_order_id': order.id,
                'phone_number': order.partner_id.phone or order.partner_id.mobile,
                'message': message_body,
            })
        return res

    def _upload_boleto(self, attachment):
        """Faz o upload do PDF para a API externa."""
        self.ensure_one()
        order = self.sale_order_id
        configs = order._get_whatsapp_server_configs()
        
        file_content = base64.b64decode(attachment.datas)
        
        payload = {'order_name': order.name}
        files = [('file', (attachment.name, file_content, attachment.mimetype))]
        headers = {'Authorization': f'Bearer {configs["upload_token"]}'}

        try:
            _logger.info(f"Fazendo upload do boleto para o pedido {order.name}.")
            response = requests.post(configs['upload_url'], headers=headers, data=payload, files=files, timeout=15)
            response.raise_for_status()
            
            _logger.info(f"Upload do boleto para {order.name} bem-sucedido.")
            order.message_post(body=_(
                "Boleto '%s' enviado para a API externa com sucesso.",
                attachment.name
            ))
            return True

        except requests.exceptions.RequestException as e:
            _logger.error(f"Erro ao fazer upload do boleto para {order.name}: {e}")
            raise UserError(_("Falha ao enviar o arquivo do boleto para o servidor externo. Verifique os logs."))


    def action_send_whatsapp_boleto(self):
        """Orquestra o envio do boleto e da mensagem."""
        self.ensure_one()
        order = self.sale_order_id

        # Passo 1: Fazer upload do anexo, se houver
        if self.attachment_ids:
            # Assumimos que haverá apenas um boleto por vez
            boleto_attachment = self.attachment_ids[0]
            self._upload_boleto(boleto_attachment)

        # Passo 2: Enviar a mensagem de texto via WAHA
        order._send_whatsapp_message(self.phone_number, self.message)
        
        return {'type': 'ir.actions.act_window_close'}