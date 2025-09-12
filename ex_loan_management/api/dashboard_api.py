import frappe
from frappe.utils import nowdate


@frappe.whitelist()
def get_loan_members():
    user = frappe.session.user
    print('user .....',user)
    roles = frappe.get_roles(user)

    groups = []
    filters = {}

    # If logged-in user is Agent, only show records created by them
    if "Agent" in roles and not "Administrator" in roles:
        filters["owner"] = user

        employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_id:
            return None  # No employee mapped

        # Fetch loan groups assigned to this employee
        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee_id},
            pluck="loan_group"
        )
        print('group ....', groups)

    assigned_members = frappe.get_all(
        "Loan Member",
        filters={"group": ["in", groups]},
        pluck="name"
    )


    # Fetch Loan Members
    loan_members = frappe.get_all(
        "Loan Member",
        fields=["name", "member_name", "group", "status", "creation", "owner"],
        filters=filters,
        order_by="creation desc"
    )

    # Members without group
    without_group = [m for m in loan_members if not m.get("group")]

    # Count based on status
    verified_count = sum(1 for m in loan_members if m.get("status") == "Verified")
    rejected_count = sum(1 for m in loan_members if m.get("status") == "Rejected")
    non_verified_count = sum(1 for m in loan_members if m.get("status") == "Open")

    return {
        "loan_members": len(loan_members),
        "verified_count": verified_count,
        "rejected_count": rejected_count,
        "non_verified_count": non_verified_count,
        "without_group_count": len(without_group),
        "assigned_members":len(assigned_members)
    }












import frappe
from lending.loan_management.doctype.repayment_schedule.repayment_schedule import get_todays_emis

@frappe.whitelist()
def get_loan_summary(group=None):
    """
    Get loan application and repayment counts, filtered by group and role.
    """
    user = frappe.session.user
    print("user ,,,,,",user)
    roles = frappe.get_roles(user)
    try:
        employee = frappe.get_doc("Employee", {"user_id": user.name}, "name")
    except:
        employee = ""

    loan_filters = {}
    repayment_filters = {}

    if "Agent" in roles and not "Administrator" in roles:

        
        # Fetch loan groups assigned to this employee
        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee},
            pluck="loan_group"
        )
        print('groups ../// ....', groups)

        assigned_members = frappe.get_all(
        "Loan Member",
        filters={"group": ["in", groups]},
        pluck="name"
    )

    # Apply group filter if provided
    if group:
        loan_filters["group"] = group
        repayment_filters["group"] = group

    print("assigned_members ...",assigned_members)

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
    total_amount = sum(e["remaining_amount"] for e in emis)
    return {
        "total_loans": len(total_loans),
        "approved_loans": approved_loans,
        "rejected_loans": rejected_loans,
        "total_repayment_amount": total_amount,
        "total_emis":total_emis
    }
