# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from odoo.tools import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    """We need to override Odoo functions that use
    https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/models/res_currency.py#L180
    to inject new_rate_amount in context and force to use this value
    """

    def _set_context_with_force_rate_amount(self):
        _self = self
        if not float_is_zero(
            self.move_id.new_rate_amount,
            precision_rounding=self.move_id.currency_id.rounding,
        ):
            _self = self.with_context(
                force_currency_id=self.move_id.currency_id.id,
                force_rate_amount=self.move_id.new_rate_amount,
            )
        return _self

    def _get_computed_price_unit(self):
        _self = self._set_context_with_force_rate_amount()
        return super(AccountMoveLine, _self)._get_computed_price_unit()

    @api.model
    def _get_fields_onchange_subtotal_model(
        self, price_subtotal, move_type, currency, company, date
    ):
        _self = self._set_context_with_force_rate_amount()
        return super(AccountMoveLine, _self)._get_fields_onchange_subtotal_model(
            price_subtotal=price_subtotal,
            move_type=move_type,
            currency=currency,
            company=company,
            date=date,
        )

    def _recompute_debit_credit_from_amount_currency(self):
        for item in self:
            _item = item._set_context_with_force_rate_amount()
            super(AccountMoveLine, _item)._recompute_debit_credit_from_amount_currency()

    def check_full_reconcile(self):
        _self = self._set_context_with_force_rate_amount()
        super(AccountMoveLine, _self).check_full_reconcile()

    def _reconcile_lines(self, debit_moves, credit_moves, field):
        _self = self._set_context_with_force_rate_amount()
        return super(AccountMoveLine, _self)._reconcile_lines(
            debit_moves=debit_moves, credit_moves=credit_moves, field=field
        )
