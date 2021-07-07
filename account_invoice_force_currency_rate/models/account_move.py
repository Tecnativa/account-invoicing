# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    currency_rate_amount = fields.Float(
        string="Rate amount",
        compute="_compute_currency_rate_amount",
        store=True,
        digits=0,
    )
    new_rate_amount = fields.Float(string="New rate amount")

    """We need to override Odoo functions that use
    https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/models/res_currency.py#L180
    to inject new_rate_amount in context and force to use this value
    """

    def _set_context_with_force_rate_amount(self):
        _self = self
        if not float_is_zero(
            self.new_rate_amount, precision_rounding=self.currency_id.rounding
        ):
            _self = self.with_context(
                force_currency_id=self.currency_id.id,
                force_rate_amount=self.new_rate_amount,
            )
        return _self

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        _self = self._set_context_with_force_rate_amount()
        super(AccountMove, _self)._recompute_tax_lines(
            recompute_tax_base_amount=recompute_tax_base_amount
        )

    def _recompute_cash_rounding_lines(self):
        _self = self._set_context_with_force_rate_amount()
        super(AccountMove, _self)._recompute_cash_rounding_lines()

    def _inverse_amount_total(self):
        for item in self:
            _item = item._set_context_with_force_rate_amount()
            super(AccountMove, _item)._inverse_amount_total()

    def _compute_payments_widget_to_reconcile_info(self):
        for item in self:
            _item = item._set_context_with_force_rate_amount()
            super(AccountMove, _item)._compute_payments_widget_to_reconcile_info()

    def _get_reconciled_info_JSON_values(self):
        _self = self._set_context_with_force_rate_amount()
        return super(AccountMove, _self)._get_reconciled_info_JSON_values()

    @api.depends(
        "line_ids.price_subtotal",
        "line_ids.tax_base_amount",
        "line_ids.tax_line_id",
        "partner_id",
        "currency_id",
    )
    def _compute_invoice_taxes_by_group(self):
        for item in self:
            _item = item._set_context_with_force_rate_amount()
            super(AccountMove, _item)._compute_invoice_taxes_by_group()

    @api.depends("date", "company_id", "currency_id", "new_rate_amount")
    @api.depends_context("currency_rate_amount")
    def _compute_currency_rate_amount(self):
        for item in self:
            if (
                item.date
                and item.company_id
                and item.currency_id
                and item.currency_id != item.company_id.currency_id
                and float_is_zero(
                    item.new_rate_amount, precision_rounding=item.currency_id.rounding
                )
            ):
                rates = item.currency_id._get_rates(item.company_id, item.date)
                item.currency_rate_amount = rates.get(item.currency_id.id)
            elif not float_is_zero(
                item.new_rate_amount, precision_rounding=item.currency_id.rounding
            ):
                item.currency_rate_amount = item.new_rate_amount
            else:
                item.currency_rate_amount = 1

    @api.constrains("new_rate_amount")
    def _check_new_rate_amount(self):
        for item in self:
            if (
                not float_is_zero(
                    item.new_rate_amount, precision_rounding=item.currency_id.rounding
                )
                and item.new_rate_amount <= 0
            ):
                raise exceptions.Warning(_("The rate amount must be greater than 0."))

    @api.onchange("new_rate_amount")
    def _onchange_new_rate_amount(self):
        for item in self:
            if not float_is_zero(
                item.new_rate_amount, precision_rounding=item.currency_id.rounding
            ):
                item.currency_rate_amount = item.new_rate_amount

    def action_post(self):
        res = super().action_post()
        self._compute_currency_rate_amount()
        return res
