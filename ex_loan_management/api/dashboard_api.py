import frappe
from frappe.utils import nowdate,get_first_day, get_last_day
from lending.loan_management.doctype.repayment_schedule.repayment_schedule import get_todays_emis


@frappe.whitelist()
def get_loan_members():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    groups = []
    filters = {}

    # If logged-in user is Agent, only show records created by them
    if "Agent" in roles and not "Administrator" in roles:
        # filters["owner"] = user

        employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_id:
            return None  # No employee mapped

        # Fetch loan groups assigned to this employee
        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee_id},
            pluck="loan_group"
        )

    assigned_members = frappe.get_all(
        "Loan Member",
        filters={"group": ["in", groups]},
        # pluck="name",
        fields=["name", "member_name", "group", "status", "creation", "owner"],
    )


    # Fetch Loan Members
    loan_members = frappe.get_all(
        "Loan Member",
        fields=["name", "member_name", "group", "status", "creation", "owner"],
        # filters=filters,
        order_by="creation desc"
    )
    print("loan_members ...",loan_members)

    # Members without group
    without_group = [m for m in loan_members if not m.get("group")]

    # Count based on status
    verified_count = sum(1 for m in assigned_members if m.get("status") == "Verified")
    rejected_count = sum(1 for m in assigned_members if m.get("status") == "Rejected")
    non_verified_count = sum(1 for m in loan_members if m.get("status") == "Draft")
    pending_count = sum(1 for m in assigned_members if m.get("status") == "Pending")
    draft_count = sum(1 for m in loan_members if m.get("status") == "Draft")

    return {
        "loan_members": len(assigned_members),
        "verified_count": verified_count,
        "rejected_count": rejected_count,
        "non_verified_count": non_verified_count,
        "draft_count": draft_count,
        "pending_count": pending_count,
        "without_group_count": len(without_group),
        "assigned_members":len(assigned_members)
    }











@frappe.whitelist()
def get_loan_summary(group=None):
    """
    Get loan application and repayment counts, filtered by group and role.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    try:
        employee = frappe.get_doc("Employee", {"user_id": user}, "name")
    except:
        employee = ""

    loan_filters = {}
    repayment_filters = {}

    assigned_members = frappe.get_all(
        "Loan Member",
        pluck="name"
    )

    if "Agent" in roles and not "Administrator" in roles:
        # Fetch loan groups assigned to this employee
        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee.name},
            pluck="loan_group"
        )

        assigned_members = frappe.get_all(
            "Loan Member",
            filters={"group": ["in", groups]},
            pluck="name"
        )

    # Apply group filter if provided
    if group:
        loan_filters["group"] = group
        repayment_filters["group"] = group


    # Loan Applications count
    total_loans = frappe.get_all("Loan Application", filters={"applicant": ["in", assigned_members]}, fields=["name","status"] )
    approved_loans = sum(1 for m in total_loans if m.get("status") == "Approved")
    rejected_loans = sum(1 for m in total_loans if m.get("status") == "Rejected")

    # Loan Repayments count

    emis = get_todays_emis(
        selected_date=nowdate(), 
        employee=employee,
    )

    total_emis = len(emis)
    remaining_amount = sum(e["remaining_amount"] for e in emis)

    # ------------------ This month's collection by this user ------------------
    first_day = get_first_day(nowdate())
    last_day = get_last_day(nowdate())

    monthly_collection = frappe.db.sql("""
        SELECT COALESCE(SUM(amount_paid), 0)
        FROM `tabLoan Repayment`
        WHERE created_by = %s
          AND docstatus = 1
          AND reference_date BETWEEN %s AND %s
    """, (employee.name, first_day, last_day))[0][0] or 0


    # ------------------ Todays's collection by this user ------------------
    todays_collection = frappe.db.sql("""
        SELECT COALESCE(SUM(amount_paid), 0)
        FROM `tabLoan Repayment`
        WHERE created_by = %s
          AND docstatus = 1
          AND reference_date = %s
    """, (employee.name, nowdate(),))[0][0] or 0

    # ------------------ Employee collection by this user ------------------
    collection_in_hand = frappe.db.sql("""
        SELECT COALESCE(SUM(amount), 0)
        FROM `tabCollection In Hand`
        WHERE employee = %s AND status = "Approved"
    """, (employee.name,))[0][0] or 0



    return {
        "total_loans": len(total_loans),
        "approved_loans": approved_loans,
        "rejected_loans": rejected_loans,
        "remaining_amount": remaining_amount,
        "total_emis":total_emis,
        "collection_in_hand":collection_in_hand,
        "todays_collection": todays_collection,
        "monthly_collection": monthly_collection,
    }
