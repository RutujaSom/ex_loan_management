import frappe
from frappe import _

@frappe.whitelist()
def get_user_profile():
    """Return logged-in user's profile info from User + Employee DocType"""
    user = frappe.session.user

    if not user or user == "Guest":
        frappe.throw(_("You must be logged in to access profile info."))

    # Get user details
    user_doc = frappe.get_doc("User", user)

    # Get linked employee record
    employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    employee_doc = frappe.get_doc("Employee", employee_id).as_dict() if employee_id else None

    # Prepare response
    profile_data = {
        "user": {
            "name": user_doc.name,
            "full_name": user_doc.full_name,
            "email": user_doc.email,
            "mobile_no": user_doc.mobile_no,
            "username": getattr(user_doc, "username", None),
            "roles": [d.role for d in user_doc.roles],
        },
        "employee": employee_doc if employee_doc else {}
    }

    return profile_data
