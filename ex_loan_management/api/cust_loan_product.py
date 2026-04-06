import frappe
from ex_loan_management.api.utils import get_paginated_data, api_error


update_fields = [
	"name",
    "product_code",
	"product_name",
	"rate_of_interest",
	"loan_category",
	"maximum_loan_amount",
    "company",
	"cyclic_day_of_the_month",
	"repayment_date_on",
	"repayment_schedule_type",
	"is_term_loan",
	"validate_normal_repayment",
	"min_days_bw_disbursement_first_repayment",
	"excess_amount_acceptance_limit",
    "penalty_interest_method",
    "penalty_interest_rate",
    "penalty_interest_value_ptpd",
    "grace_period_in_days",
    "write_off_amount",
    "broken_period_interest_charged",
    "auto_close_with_security_deposit",
    "min_auto_closure_tolerance_amount",
    "max_auto_closure_tolerance_amount",
    "repayment_date_on",
    "days_past_due_threshold_for_npa",
    "description",
    "mode_of_payment",
    "disbursement_account",
    "payment_account",
    "custom_online_repayment_account",
    "loan_account",
    "security_deposit_account",
    "suspense_collection_account",
    "interest_income_account",
    "interest_accrued_account",
    "interest_waiver_account",
    "broken_period_interest_recovery_account",
    "interest_receivable_account",
    "suspense_interest_income",
    "suspense_interest_receivable",
    "same_as_regular_interest_accounts",
    "additional_interest_income",
    "additional_interest_accrued",
    "additional_interest_receivable",
    "additional_interest_suspense",
    "additional_interest_waiver",
    "penalty_income_account",
    "penalty_accrued_account",
    "penalty_waiver_account",
    "penalty_receivable_account",
    "penalty_suspense_account",
    "write_off_account",
    "write_off_recovery_account",
]

"""
	Get Loan Product List (with optional pagination, search & sorting)
"""
@frappe.whitelist()
def loan_product_list(page=1, page_size=10, search=None, sort_by="product_name", sort_order="asc", is_pagination=False):
    is_pagination = frappe.utils.sbool(is_pagination)  # convert "true"/"false"/1/0 into int
    extra_params = {"search": search} if search else {}
    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path

    return get_paginated_data(
        doctype="Loan Product",
        fields=update_fields,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["product_code","product_name"],
        is_pagination=is_pagination,
        base_url=base_url,
        extra_params=extra_params,
	)



