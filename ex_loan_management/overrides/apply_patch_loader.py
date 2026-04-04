import frappe
from frappe.utils import flt
from frappe import _

def apply_patch():
    """
    Patch LoanRepayment.validate_principal_amount ONCE
    """
    from lending.loan_management.doctype.loan_repayment.loan_repayment import LoanRepayment

    # 🧪 Debug: confirm patch applied
    if getattr(LoanRepayment, "_closure_patch_applied", False):
        return

    original = LoanRepayment.validate_principal_amount

    def patched_validate_principal_amount(self, precision):
        if getattr(self.flags, "ignore_principal_validation", False):
            return
        return original(self, precision)

    LoanRepayment.validate_principal_amount = patched_validate_principal_amount
    LoanRepayment._closure_patch_applied = True

    frappe.logger().info("✅ LoanRepayment principal validation patched for Loan Closure")