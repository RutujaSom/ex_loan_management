import frappe
from frappe.utils import flt, getdate, cint
from erpnext.accounts.general_ledger import make_gl_entries

def before_submit(doc, method):
    if doc.repayment_type != "Loan Closure":
        return  # let core logic run

    # 🔴 Prevent core GL
    doc.make_gl_entries = lambda *args, **kwargs: None

    make_loan_closure_gl(doc)
    close_loan(doc)


def close_loan(doc):
    loan = frappe.get_doc("Loan", doc.against_loan)

    loan.status = "Closed"
    loan.total_principal_paid = loan.loan_amount
    loan.save(ignore_permissions=True)

    

# def make_loan_closure_gl(doc):
#     precision = cint(frappe.db.get_default("currency_precision")) or 2
#     loan = frappe.get_doc("Loan", doc.against_loan)

#     principal = flt(doc.pending_principal_amount, precision)
#     interest = flt(doc.interest_payable, precision)
#     penalty = flt(doc.penalty_amount, precision)

#     total = principal + interest + penalty

#     gle = []

#     # 1️⃣ Bank / Cash
#     gle.append({
#         "account": doc.payment_account,
#         "debit": total,
#         "debit_in_account_currency": total,
#         "posting_date": getdate(doc.posting_date),
#         "against_voucher_type": doc.doctype,
#         "against_voucher": doc.name,
#         "cost_center": doc.cost_center,
#     })

#     # 2️⃣ Loan Principal
#     gle.append({
#         "account": loan.loan_account,
#         "credit": principal,
#         "credit_in_account_currency": principal,
#         "party_type": loan.applicant_type,
#         "party": loan.applicant,
#         "posting_date": getdate(doc.posting_date),
#     })

#     # 3️⃣ Interest Income
#     if interest > 0:
#         gle.append({
#             "account": loan.interest_income_account,
#             "credit": interest,
#             "credit_in_account_currency": interest,
#             "posting_date": getdate(doc.posting_date),
#             "cost_center": doc.cost_center,
#         })

#     # 4️⃣ Penalty Income
#     if penalty > 0:
#         gle.append({
#             "account": loan.penalty_income_account,
#             "credit": penalty,
#             "credit_in_account_currency": penalty,
#             "posting_date": getdate(doc.posting_date),
#             "cost_center": doc.cost_center,
#         })

#     make_gl_entries(gle, merge_entries=False)




def make_loan_closure_gl(self, cancel=0, adv_adj=0):
    gle_map = []
    remarks = self.get_remarks()
    payment_account = self.get_payment_account()
    precision = cint(frappe.db.get_default("currency_precision")) or 2

    payment_party_type = ""
    payment_party = ""

    if (
        hasattr(self, "process_payroll_accounting_entry_based_on_employee")
        and self.process_payroll_accounting_entry_based_on_employee
    ):
        payment_party_type = "Employee"
        payment_party = self.applicant

    account_details = frappe.db.get_value(
        "Loan Product",
        self.loan_product,
        [
            "interest_receivable_account",
            "suspense_interest_receivable",
            "suspense_interest_income",
            "interest_income_account",
        ],
        as_dict=1,
    )

    if self.total_penalty_paid:
        penalty_receivable_account = frappe.db.get_value(
            "Loan Product", self.loan_product, "penalty_receivable_account"
        )
        gle_map.append(
            self.get_gl_dict(
                {
                    "account": payment_account,
                    "against": penalty_receivable_account,
                    "debit": self.total_penalty_paid,
                    "debit_in_account_currency": self.total_penalty_paid,
                    "against_voucher_type": "Loan",
                    "against_voucher": self.against_loan,
                    "remarks": ("Penalty against loan:") + self.against_loan,
                    "cost_center": self.cost_center,
                    "party_type": self.applicant_type,
                    "party": self.applicant,
                    "posting_date": getdate(self.posting_date),
                },
                item=self,
            )
        )

        gle_map.append(
            self.get_gl_dict(
                {
                    "account": penalty_receivable_account,
                    "against": payment_account,
                    "party_type": self.applicant_type,
                    "party": self.applicant,
                    "credit": self.total_penalty_paid,
                    "credit_in_account_currency": self.total_penalty_paid,
                    "against_voucher_type": "Loan",
                    "against_voucher": self.against_loan,
                    "remarks": ("Penalty against loan:") + self.against_loan,
                    "cost_center": self.cost_center,
                    "posting_date": getdate(self.posting_date),
                },
                item=self,
            )
        )

    for repayment in self.get("repayment_details"):
        if repayment.paid_interest_amount:
            gle_map.append(
                self.get_gl_dict(
                    {
                        "account": payment_account,
                        "against": account_details.interest_receivable_account + ", " + self.penalty_income_account,
                        "debit": repayment.paid_interest_amount,
                        "debit_in_account_currency": repayment.paid_interest_amount,
                        "against_voucher_type": "Loan",
                        "against_voucher": self.against_loan,
                        "remarks": (remarks),
                        "cost_center": self.cost_center,
                        "posting_date": getdate(self.posting_date),
                        "party_type": payment_party_type,
                        "party": payment_party,
                    },
                    item=self,
                )
            )

            gle_map.append(
                self.get_gl_dict(
                    {
                        "account": account_details.interest_receivable_account,
                        "party_type": self.applicant_type,
                        "party": self.applicant,
                        "against": payment_account,
                        "credit": repayment.paid_interest_amount,
                        "credit_in_account_currency": repayment.paid_interest_amount,
                        "against_voucher_type": "Loan",
                        "against_voucher": self.against_loan,
                        "remarks": (remarks),
                        "cost_center": self.cost_center,
                        "posting_date": getdate(self.posting_date),
                    },
                    item=self,
                )
            )

            if self.is_npa:
                gle_map.append(
                    self.get_gl_dict(
                        {
                            "account": account_details.interest_receivable_account,
                            "against": account_details.suspense_interest_receivable,
                            "party_type": self.applicant_type,
                            "party": self.applicant,
                            "debit": repayment.paid_interest_amount,
                            "debit_in_account_currency": repayment.paid_interest_amount,
                            "against_voucher_type": "Loan",
                            "against_voucher": self.against_loan,
                            "cost_center": self.cost_center,
                            "posting_date": getdate(self.posting_date),
                        },
                        item=self,
                    )
                )

                gle_map.append(
                    self.get_gl_dict(
                        {
                            "account": account_details.suspense_interest_receivable,
                            "party_type": self.applicant_type,
                            "party": self.applicant,
                            "against": account_details.interest_receivable_account,
                            "credit": repayment.paid_interest_amount,
                            "credit_in_account_currency": repayment.paid_interest_amount,
                            "against_voucher_type": "Loan",
                            "against_voucher": self.against_loan,
                            "cost_center": self.cost_center,
                            "posting_date": getdate(self.posting_date),
                        },
                        item=self,
                    )
                )

                gle_map.append(
                    self.get_gl_dict(
                        {
                            "account": account_details.interest_income_account,
                            "credit_in_account_currency": repayment.paid_interest_amount,
                            "credit": repayment.paid_interest_amount,
                            "cost_center": self.cost_center,
                            "against": account_details.suspense_interest_income,
                        },
                        item=self,
                    )
                )

                gle_map.append(
                    self.get_gl_dict(
                        {
                            "account": account_details.suspense_interest_income,
                            "debit": repayment.paid_interest_amount,
                            "debit_in_account_currency": repayment.paid_interest_amount,
                            "cost_center": self.cost_center,
                            "against": account_details.interest_income_account,
                        },
                        item=self,
                    )
                )

        if repayment.paid_principal_amount:
            gle_map.append(
                self.get_gl_dict(
                    {
                        "account": payment_account,
                        "against": account_details.interest_receivable_account + ", " + self.penalty_income_account,
                        "debit": repayment.paid_principal_amount,
                        "debit_in_account_currency": repayment.paid_principal_amount,
                        "against_voucher_type": "Loan",
                        "against_voucher": self.against_loan,
                        "remarks": (remarks),
                        "cost_center": self.cost_center,
                        "posting_date": getdate(self.posting_date),
                        "party_type": payment_party_type,
                        "party": payment_party,
                    },
                    item=self,
                )
            )

            gle_map.append(
                self.get_gl_dict(
                    {
                        "account": self.loan_account,
                        "party_type": self.applicant_type,
                        "party": self.applicant,
                        "against": payment_account,
                        "credit": repayment.paid_principal_amount,
                        "credit_in_account_currency": repayment.paid_principal_amount,
                        "against_voucher_type": "Loan",
                        "against_voucher": self.against_loan,
                        "remarks": (remarks),
                        "cost_center": self.cost_center,
                        "posting_date": getdate(self.posting_date),
                    },
                    item=self,
                )
            )

    if not self.get("repayment_details") and flt(self.pending_principal_amount, precision) > 0:

        # if flt(self.amount_paid, precision) > flt(self.pending_principal_amount, precision):
        # 	frappe.throw(
        # 		("The amount paid ({0}) cannot be more than the pending principal amount ({1}).").format(
        # 			flt(self.amount_paid, precision), flt(self.pending_principal_amount, precision)
        # 		)
        # 	)
        print("self.loan_account ....",self.loan_account)
        gle_map.append(
            self.get_gl_dict(
                {
                    "account": payment_account,
                    "against": self.loan_account,
                    "debit": flt(self.amount_paid, precision),
                    "debit_in_account_currency": flt(self.amount_paid, precision),
                    "against_voucher_type": "Loan",
                    "against_voucher": self.against_loan,
                    "remarks": (remarks),
                    "cost_center": self.cost_center,
                    "posting_date": getdate(self.posting_date),
                    "party_type": payment_party_type,
                    "party": payment_party,
                },
                item=self,
            )
        )
        print("gl ....")

        gle_map.append(
            self.get_gl_dict(
                {
                    "account": self.loan_account,
                    "party_type": self.applicant_type,
                    "party": self.applicant,
                    "against": payment_account,
                    "credit": flt(self.amount_paid, precision),
                    "credit_in_account_currency": flt(self.amount_paid, precision),
                    "against_voucher_type": "Loan",
                    "against_voucher": self.against_loan,
                    "remarks": (remarks),
                    "cost_center": self.cost_center,
                    "posting_date": getdate(self.posting_date),
                },
                item=self,
            )
        )

    if gle_map:
        make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj, merge_entries=False)
