import frappe
from frappe import _
from frappe.utils import getdate


def validate_custom_repayment_start_date(doc):
    """
    Common holiday validation for Loan and Loan Repayment Schedule
    Uses field: repayment_start_date
    """

    if not getattr(doc, "company", None) or not getattr(doc, "repayment_start_date", None):
        return

    repayment_date = getdate(doc.repayment_start_date)

    company_data = frappe.db.get_value(
        "Company",
        doc.company,
        ["custom_skip_holiday_on_loan_schedule", "default_holiday_list"],
        as_dict=True
    )

    if (
        not company_data
        or not company_data.custom_skip_holiday_on_loan_schedule
        or not company_data.default_holiday_list
    ):
        return

    is_holiday = frappe.db.exists(
        "Holiday",
        {
            "parent": company_data.default_holiday_list,
            "holiday_date": repayment_date
        }
    )

    if is_holiday:
        frappe.throw(
            _(
                "The selected Repayment Start Date {0} is a holiday as per Holiday List {1}. "
                "Please choose another date."
            ).format(
                frappe.bold(repayment_date),
                frappe.bold(company_data.default_holiday_list)
            )
        )