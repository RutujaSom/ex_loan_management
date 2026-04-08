import frappe
from frappe.utils import getdate, today


# ==========================================================
# COMMON HELPER
# ==========================================================
def get_active_loans():
    """
    Returns list of active (non-draft) loan names
    """
    return frappe.get_all(
        "Loan",
        filters={"status": ["not in", "Draft", "Closed","Loan Closure Requested"]},
        pluck="name"
    )


def get_today():
    """
    Returns today's date in date format
    """
    return getdate(today())


# ==========================================================
# EXPECTED AMOUNT (EMI DUE TODAY)
# ==========================================================
@frappe.whitelist()
def get_expected_value():
    """
    Returns total expected EMI amount for today
    """
    loans = get_active_loans()
    if not loans:
        return {"value": 0, "fieldtype": "Currency"}

    today_date = get_today()

    expected_amount = frappe.db.sql("""
        SELECT COALESCE(SUM(rs.total_payment), 0)
        FROM `tabLoan Repayment Schedule` lrs
        INNER JOIN `tabRepayment Schedule` rs
            ON rs.parent = lrs.name
        WHERE lrs.loan IN %(loans)s
          AND lrs.status = 'Active'
          AND rs.payment_date = %(today)s
    """, {
        "loans": tuple(loans),
        "today": today_date
    }, as_list=True)[0][0]

    return {
        "value": expected_amount,
        "fieldtype": "Currency",
        "route_options": {"date": today_date},
    }


# ==========================================================
# TOTAL COLLECTED AMOUNT (TODAY)
# ==========================================================
@frappe.whitelist()
def get_collected_value():
    """
    Returns total collected EMI amount for today
    """
    return _get_collected_amount_by_mode()


# ==========================================================
# CASH COLLECTED (TODAY)
# ==========================================================
@frappe.whitelist()
def get_cash_collected_value():
    """
    Returns total cash EMI collection for today
    """
    return _get_collected_amount_by_mode(mode="Cash")


# ==========================================================
# ONLINE COLLECTED (TODAY)
# ==========================================================
@frappe.whitelist()
def get_online_collected_value():
    """
    Returns total online EMI collection for today
    """
    return _get_collected_amount_by_mode(mode="ONLINE")


# ==========================================================
# INTERNAL SHARED FUNCTION
# ==========================================================
def _get_collected_amount_by_mode(mode=None):
    """
    Returns collected amount for today.
    If mode is provided, filters by payment mode.
    """
    loans = get_active_loans()
    if not loans:
        return {"value": 0, "fieldtype": "Currency"}

    today_date = get_today()

    conditions = ""
    values = {
        "loans": tuple(loans),
        "today": today_date
    }

    if mode:
        conditions = " AND UPPER(custom_mode_of_payment) = %(mode)s"
        values["mode"] = mode

    collected_amount = frappe.db.sql(f"""
        SELECT COALESCE(SUM(amount_paid), 0)
        FROM `tabLoan Repayment`
        WHERE against_loan IN %(loans)s
          AND workflow_state != 'Rejected'
          AND reference_date = %(today)s
          {conditions}
    """, values, as_list=True)[0][0]

    return {
        "value": collected_amount,
        "fieldtype": "Currency",
        "route_options": {"date": today_date},
    }