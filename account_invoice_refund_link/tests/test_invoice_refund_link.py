# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2014-2023 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api, registry
from odoo.tests import get_db_name, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from .. import post_init_hook


@tagged("post_install", "-at_install")
class TestInvoiceRefundLinkBase(AccountTestInvoicingCommon):
    refund_method = "refund"

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        with registry(get_db_name()).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if not env.ref("l10n_generic_coa.configurable_chart_template", False):
                # Fallback for executing tests in any existing CoA
                coa = env["account.chart.template"].search([("visible", "=", True)])[:1]
                chart_template_ref = coa.get_external_id()[coa.id]
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.invoice_lines = [
            (0, False, {"name": "Test section", "display_type": "line_section"}),
            (
                0,
                False,
                {
                    "name": "Test description #1",
                    "quantity": 1.0,
                    "price_unit": 100.0,
                },
            ),
            (
                0,
                False,
                {
                    "name": "Test description #2",
                    "quantity": 2.0,
                    "price_unit": 25.0,
                },
            ),
        ]
        cls.invoice = cls.env["account.move"].create(
            {
                "partner_id": cls.partner_a.id,
                "move_type": "out_invoice",
                "invoice_line_ids": cls.invoice_lines,
            }
        )
        cls.invoice.action_post()
        cls.refund_reason = "The refund reason"
        cls.env["account.move.reversal"].with_context(
            active_ids=cls.invoice.ids, active_model="account.move"
        ).create(
            {
                "refund_method": cls.refund_method,
                "reason": cls.refund_reason,
                "journal_id": cls.company_data["default_journal_sale"].id,
            }
        ).reverse_moves()

    def _test_refund_link(self):
        self.assertTrue(self.invoice.refund_invoice_ids)
        refund = self.invoice.refund_invoice_ids[0]
        ref = "Reversal of: {}, {}".format(self.invoice.name, self.refund_reason)
        self.assertEqual(refund.ref, ref)
        self.assertEqual(len(self.invoice.invoice_line_ids), len(self.invoice_lines))
        self.assertEqual(len(refund.invoice_line_ids), len(self.invoice_lines))
        # We're checking only the 2nd and 3rd lines because the first is a line section
        self.assertTrue(refund.invoice_line_ids[1].origin_line_id)
        self.assertEqual(
            self.invoice.invoice_line_ids[1], refund.invoice_line_ids[1].origin_line_id
        )
        self.assertTrue(refund.invoice_line_ids[2].origin_line_id)
        self.assertEqual(
            self.invoice.invoice_line_ids[2], refund.invoice_line_ids[2].origin_line_id
        )


class TestInvoiceRefundLink(TestInvoiceRefundLinkBase):
    @classmethod
    def setUpClass(cls):
        super(TestInvoiceRefundLink, cls).setUpClass()

    def test_post_init_hook(self):
        self.assertTrue(self.invoice.refund_invoice_ids)
        refund = self.invoice.refund_invoice_ids[0]
        refund.invoice_line_ids.write({"origin_line_id": False})
        self.assertFalse(refund.mapped("invoice_line_ids.origin_line_id"))
        post_init_hook(self.env.cr, None)
        self.refund_reason = "The refund reason"
        self._test_refund_link()

    def test_refund_link(self):
        self._test_refund_link()

    def test_invoice_copy(self):
        refund = self.invoice.refund_invoice_ids[0]
        self.invoice.copy()
        self.assertEqual(
            refund.invoice_line_ids.origin_line_id, self.invoice.invoice_line_ids
        )

    def test_refund_copy(self):
        refund = self.invoice.refund_invoice_ids[0]
        refund.copy()
        self.assertEqual(
            self.invoice.invoice_line_ids, refund.invoice_line_ids.origin_line_id
        )


class TestInvoiceRefundCancelLink(TestInvoiceRefundLinkBase):
    refund_method = "cancel"

    def test_refund_link(self):
        self._test_refund_link()


class TestInvoiceRefundModifyLink(TestInvoiceRefundLinkBase):
    refund_method = "modify"

    def test_refund_link(self):
        self._test_refund_link()
