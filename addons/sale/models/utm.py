# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, SUPERUSER_ID

class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'
    _description = 'UTM Campaign'

    quotation_count = fields.Integer('Quotation Count', groups='sales_team.group_sale_salesman', compute="_compute_quotation_count")
    invoiced_amount = fields.Integer(default=0, compute="_compute_sale_invoiced_amount", string="Revenues generated by the campaign")
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')

    def _compute_quotation_count(self):
        quotation_data = self.env['sale.order'].read_group([
            ('campaign_id', 'in', self.ids)],
            ['campaign_id'], ['campaign_id'])
        data_map = {datum['campaign_id'][0]: datum['campaign_id_count'] for datum in quotation_data}
        for campaign in self:
            campaign.quotation_count = data_map.get(campaign.id, 0)

    def _compute_sale_invoiced_amount(self):
        query = """SELECT move.campaign_id, -SUM(line.balance) as price_subtotal
                    FROM account_move_line line
                    INNER JOIN account_move move ON line.move_id = move.id
                    WHERE move.state not in ('draft', 'cancel')
                        AND move.campaign_id IN %s
                        AND move.type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                        AND line.account_id IS NOT NULL
                        AND NOT line.exclude_from_invoice_tab
                    GROUP BY move.campaign_id
                    """

        self._cr.execute(query, [tuple(self.ids)])
        query_res = self._cr.dictfetchall()

        for datum in query_res:
            campaign = self.browse(datum['campaign_id'])
            campaign.invoiced_amount = datum['price_subtotal']

    def action_redirect_to_quotations(self):
        action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        action['domain'] = [('campaign_id', '=', self.id)]
        action['context'] = {'default_campaign_id': self.id}
        return action

    def action_redirect_to_invoiced(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        invoices = self.env['account.move'].search([('campaign_id', '=', self.id)])
        action['context'] = {
            'create': False,
            'edit': False,
            'view_no_maturity': True
        }
        action['domain'] = [
            ('id', 'in', invoices.ids),
            ('type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
            ('state', 'not in', ['draft', 'cancel'])
        ]
        return action
