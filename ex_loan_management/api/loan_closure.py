import frappe
from frappe.utils import getdate, date_diff, flt
from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
    get_last_accrual_date,
    get_interest_amount,
    make_loan_interest_accrual_entry,
)

def accrue_interest_till_date(loan_name, posting_date):
    loan = frappe.get_doc("Loan", loan_name)
    posting_date = getdate(posting_date)

    last_accrual_date = get_last_accrual_date(loan.name, posting_date)

    if not last_accrual_date:
        return 0

    no_of_days = date_diff(posting_date, last_accrual_date)

    if no_of_days <= 0:
        return 0

    outstanding_principal = flt(
        loan.loan_amount
        - loan.total_principal_paid
        - loan.written_off_amount
    )

    if outstanding_principal <= 0:
        return 0

    interest_amount = get_interest_amount(
        no_of_days=no_of_days,
        principal_amount=outstanding_principal,
        rate_of_interest=loan.rate_of_interest,
        company=loan.company,
        posting_date=posting_date,
    )

    if interest_amount <= 0:
        return 0

    make_loan_interest_accrual_entry(frappe._dict({
        "loan": loan.name,
        "applicant_type": loan.applicant_type,
        "applicant": loan.applicant,
        "interest_income_account": loan.interest_income_account,
        "loan_account": loan.loan_account,
        "pending_principal_amount": outstanding_principal,
        "interest_amount": interest_amount,
        "total_pending_interest_amount": interest_amount,
        "penalty_amount": 0,
        "posting_date": posting_date,
        "due_date": posting_date,
        "accrual_type": "Repayment",
    }))

    return interest_amount





# custom_app/loan/loan_utils.py
@frappe.whitelist()
def get_loan_closure_data(loan, posting_date):
    from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
        get_last_accrual_date, get_interest_amount
    )
    interest = accrue_interest_till_date(loan, posting_date)
    loan_doc = frappe.get_doc("Loan", loan)
    posting_date = frappe.utils.getdate(posting_date)

    # Step 1: Accrue interest till posting date
    last_accrual = get_last_accrual_date(loan_doc.name, posting_date)
    if last_accrual:
        days = frappe.utils.date_diff(posting_date, last_accrual)
    else:
        days = 0

    principal_remaining = flt(loan_doc.loan_amount - loan_doc.total_principal_paid - loan_doc.written_off_amount)
    interest_remaining = flt(loan_doc.total_interest_payable - loan_doc.total_interest_payable)

    interest_amount = 0
    if days > 0 and principal_remaining > 0:
        interest_amount = get_interest_amount(
            no_of_days=days,
            principal_amount=principal_remaining,
            rate_of_interest=loan_doc.rate_of_interest,
            company=loan_doc.company,
            posting_date=posting_date,
        )
    print('principal_remaining ...',principal_remaining, '....interest_amount ...',interest_amount)

    # Return data to fill in form
    return {
        "principal_amount": principal_remaining,
        "interest_amount": interest_amount,
        "total_amount": flt(principal_remaining + interest_amount),        # "payment_account": loan_doc.default_receivable_account or loan_doc.loan_account
    }



# import frappe
# from frappe.utils import flt, getdate

# @frappe.whitelist()
# def get_loan_closure_data(loan, posting_date):
#     """
#     Returns exact pending amounts for loan closure
#     (principal + interest + penalty + charges)
#     """

#     from lending.loan_management.doctype.loan_repayment.loan_repayment import (
#         calculate_amounts,
#         get_pending_principal_amount,
#     )

#     loan = frappe.get_doc("Loan", loan)
#     posting_date = getdate(posting_date)

#     # 1️⃣ Get pending principal
#     pending_principal = get_pending_principal_amount(loan)

#     # 2️⃣ Get all pending amounts till posting date
#     pending_amounts = calculate_amounts(
#         loan,
#         posting_date,
#         payment_type="Loan Closure",
#         with_loan_details=True
#     )

#     return {
#         "principal_amount": flt(pending_principal),
#         "interest_amount": flt(pending_amounts.get("interest_amount")),
#         "penalty_amount": flt(pending_amounts.get("penalty_amount")),
#         "charges_amount": flt(pending_amounts.get("charges_amount")),
#         "total_amount": flt(
#             pending_principal
#             + pending_amounts.get("interest_amount", 0)
#             + pending_amounts.get("penalty_amount", 0)
#             + pending_amounts.get("charges_amount", 0)
#         ),
#         "payable_account": loan.loan_account,
#     }


