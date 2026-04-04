from lending.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
    ProcessLoanInterestAccrual,
)

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
    make_accrual_interest_entry_for_demand_loans,
    make_accrual_interest_entry_for_term_loans,
)


class ProcessLoanInterestAccrualOverride(ProcessLoanInterestAccrual):

    def on_submit(self):
        print("in overide submit ")
        open_loans = []

        if self.loan:
            loan_doc = frappe.get_doc("Loan", self.loan)
            if loan_doc:
                open_loans.append(loan_doc)

        if self.custom_for_loan_closure:
            from ex_loan_management.api.cust_interest_accrual import (
                after_submit,
            )
            after_submit(self)
            return

        if (not self.loan or not loan_doc.is_term_loan) and self.process_type != "Term Loans":
            print("in if ....")
            make_accrual_interest_entry_for_demand_loans(
                self.posting_date,
                self.name,
                open_loans=open_loans,
                loan_product=self.loan_product,
                accrual_type=self.accrual_type,
            )

        if (not self.loan or loan_doc.is_term_loan) and self.process_type != "Demand Loans":
            print("in 2if ...")
            make_accrual_interest_entry_for_term_loans(
                self.posting_date,
                self.name,
                term_loan=self.loan,
                loan_product=self.loan_product,
                accrual_type=self.accrual_type,
            )