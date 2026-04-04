import frappe
from lending.loan_management.doctype.loan_repayment.loan_repayment import LoanRepayment

# ✅ Keep references to original methods
_original_validate = LoanRepayment.validate
_original_on_submit = LoanRepayment.on_submit


def custom_validate(self):
    """
    Treat Loan Closure as Normal Repayment ONLY for accounting logic
    """
    if self.repayment_type == "Loan Closure":
        self._is_loan_closure = True
        self.repayment_type = "Normal Repayment"

    # ✅ Call original validate (NOT super)
    _original_validate(self)


def custom_on_submit(self):
    # ✅ Call original submit first
    _original_on_submit(self)

    # Restore label after GL + loan update
    if getattr(self, "_is_loan_closure", False):
        self.db_set("repayment_type", "Loan Closure")


def apply_patch(bootinfo=None):
    LoanRepayment.validate = custom_validate
    LoanRepayment.on_submit = custom_on_submit
