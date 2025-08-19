# -*- coding: utf-8 -*-
import requests
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_whatsapp_server_configs(self):
        """Busca as configurações das APIs nos parâmetros do sistema."""
        get_param = self.env['ir.config_parameter'].sudo().get_param
        
        # --- Configurações WAHA ---
        waha_base_url = get_param('waha.base_url')
        waha_session_id = get_param('waha.session_id')
        
        # --- Configurações API Externa (Boleto) ---
        upload_api_url = get_param('workwise.api.url')
        upload_api_token = get_param('workwise.api.token')

        if not all([waha_base_url, waha_session_id, upload_api_url, upload_api_token]):
            raise UserError(_(
                "As configurações da API do WhatsApp ou da API de Upload não foram definidas.\n"
                "Por favor, configure-as em Configurações > Técnico > Parâmetros do Sistema."
            ))
            
        return {
            'waha_endpoint': f"{waha_base_url}/{waha_session_id}/messages/text",
            'upload_url': upload_api_url,
            'upload_token': upload_api_token,
        }
    
    def _format_phone_number(self, phone_number):
        """Formata o número de telefone para o padrão do WAHA (ex: 5511999998888@s.whatsapp.net)."""
        if not phone_number:
            return False
        # Remove caracteres não numéricos
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        # Adiciona o código do país (Brasil) se não estiver presente
        if len(clean_phone) <= 11 and not clean_phone.startswith('55'):
            clean_phone = '55' + clean_phone
        
        return f"{clean_phone}@s.whatsapp.net"

    def _send_whatsapp_message(self, phone, message):
        """Envia a mensagem de texto usando a API WAHA."""
        if not phone:
            _logger.warning(f"Tentativa de enviar WhatsApp para o pedido {self.name} sem número de telefone.")
            return

        configs = self._get_whatsapp_server_configs()
        formatted_phone = self._format_phone_number(phone)
        
        payload = {
            "chatId": formatted_phone,
            "text": message
        }
        headers = {'Content-Type': 'application/json'}

        try:
            _logger.info(f"Enviando mensagem para {formatted_phone} via WAHA.")
            response = requests.post(configs['waha_endpoint'], json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Adiciona a mensagem ao chatter do pedido
            self.message_post(body=_(
                "Mensagem enviada por WhatsApp para %s:\n%s",
                phone, message
            ))
            _logger.info(f"Mensagem para {self.name} enviada com sucesso.")

        except requests.exceptions.RequestException as e:
            _logger.error(f"Erro ao enviar mensagem via WAHA para {self.name}: {e}")
            raise UserError(_("Falha ao enviar a mensagem via WAHA. Verifique os logs e as configurações."))

    def action_open_whatsapp_composer(self):
        """
        Gera o relatório do Pedido de Venda, cria um anexo,
        e abre o wizard para enviar a mensagem e o anexo.
        """
        self.ensure_one()

        # O nome do relatório que queremos gerar
        report_xml_id = 'sale.action_report_saleorder'

        # 1. Gera o conteúdo do PDF chamando a função da maneira correta
        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(report_xml_id, self.id)

        # 2. Cria o anexo no Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'sale.order',
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })

        # 3. Abre o wizard, passando o anexo recém-criado como padrão
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enviar por WhatsApp'),
            'res_model': 'whatsapp.sale.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_phone_number': self.partner_id.phone or self.partner_id.mobile,
                'default_attachment_ids': [(6, 0, attachment.ids)],
            }
        }

    def action_confirm(self):
        """Sobrescreve a ação de confirmar para enviar WhatsApp."""
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            message = _("Seu pedido %s foi confirmado!", order.name)
            order._send_whatsapp_message(order.partner_id.phone or order.partner_id.mobile, message)
        return res

    def action_cancel(self):
        """Sobrescreve a ação de cancelar para enviar WhatsApp."""
        res = super(SaleOrder, self).action_cancel()
        message = _("Seu pedido %s foi cancelado.", self.name)
        self._send_whatsapp_message(self.partner_id.phone or self.partner_id.mobile, message)
        return res