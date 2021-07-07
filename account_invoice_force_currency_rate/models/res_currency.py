# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _get_rates(self, company, date):
        res = super()._get_rates(company=company, date=date)
        ctx = self.env.context
        if ctx.get("force_rate_amount") and ctx.get("force_currency_id"):
            res[ctx.get("force_currency_id")] = ctx.get("force_rate_amount")
        return res
