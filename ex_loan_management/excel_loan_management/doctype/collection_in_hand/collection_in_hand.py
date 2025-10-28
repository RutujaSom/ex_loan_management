# Copyright (c) 2025, Rutuja Somvanshi and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from ex_loan_management.api.utils import get_paginated_data
from frappe.utils.data import nowdate
from frappe.utils.file_manager import save_file
from ex_loan_management.api.utils import api_error

class CollectionInHand(Document):
    pass




update_fields = [
    "name",
    "employee",
    "loan_repayment",
    "amount",
    "given_to",
    "posting_date",
    "applicant",
    "loan",
    "payment_proof",
    "amount_given_emp",
    "description",
    "status",
    "approval_by",
    "approval_date",
]

"""
	Get Loan Member List (with optional pagination, search & sorting)
"""

@frappe.whitelist()
def collection_in_hand_list(page=1, page_size=10, search=None, sort_by="employee", sort_order="asc", employee=None, is_pagination=False, **kwargs):
    is_pagination = frappe.utils.sbool(is_pagination)  # convert "true"/"false"/1/0 into bool
    extra_params = {"search": search} if search else {}
    del kwargs['cmd']

    # 🔹 Collect filters from kwargs (all query params except the defaults)
    filters = {}
    for k, v in kwargs.items():
        if v not in [None, ""]:   # skip empty params
            filters[k] = v

    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path
    
    return get_paginated_data(
        doctype="Collection In Hand",
        fields=update_fields,
        filters=filters,   # ✅ Now your filters will be applied
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["employee","amount_given_emp","description","given_to",],
        is_pagination=is_pagination,
        base_url=base_url,
        extra_params=extra_params,
        link_fields={"employee": "employee_name"},
    )





@frappe.whitelist()
def create_collection_in_hand():
    try:
        data = frappe.form_dict  # works for JSON body and form-data
        files = frappe.request.files  # uploaded files

        # Step 1: Prepare Loan Application doc
        amount = data.get("amount")
        if amount:
            # Convert to float and make negative if positive
            amount = float(amount)
            if amount > 0:
                amount = -amount

        doc = frappe.get_doc({
            "doctype": "Collection In Hand",
            "employee":data.get("employee"),
            "amount":amount,
            "given_to":data.get("given_to"),
            "posting_date":data.get("posting_date") or nowdate(),
            "amount_given_emp":data.get("amount_given_emp"),
            "description":data.get("description")
        })
        if "payment_proof" in files:
            upload = files["payment_proof"] 
            if upload and upload.filename:
                file_doc = save_file(
                    fname=upload.filename,
                    content=upload.stream.read(),
                    dt="Collection In Hand",
                    dn=1,
                    is_private=1
                )
                doc.set("payment_proof", file_doc.file_url)


        # Step 2: Insert Collection In Hand (runs validate() automatically)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "status_code": 201,
            "msg": "Collection In Hand Created Successfully"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Collection In Hand API Error")
        return api_error(e)



@frappe.whitelist()
def approve_or_reject_collection(name, status):
    try:
        """
        Approve or reject Collection In Hand based on session user.
        - If amount_given_emp exists → that employee can approve.
        - If not → admin user can approve.
        """

        doc = frappe.get_doc("Collection In Hand", name)
        current_user = frappe.session.user
        
        # Determine the user who is allowed to approve
        if doc.amount_given_emp:
            # Get the user linked to the Employee
            expected_approver = frappe.db.get_value("Employee", doc.amount_given_emp, "user_id")
            if not expected_approver:
                frappe.throw("Employee linked in amount_given_emp has no user assigned.")
        else:
            # If no employee assigned, only Administrator can approve
            expected_approver = "Administrator"  # or frappe.db.get_single_value("Global Defaults", "default_administrator")
        print("expected_approver ...",expected_approver)
        # Check permission
        if "Administrator" not in frappe.get_roles(current_user):
            if current_user != expected_approver:
                frappe.throw(f"User can not approve/reject this record.")

        # Set status based on status
        if status.lower() == "approved":
            doc.status = "Approved"
        elif status.lower() == "rejected":
            doc.status = "Rejected"
        else:
            frappe.throw("Invalid status. Use 'approved' or 'rejected'.")

        # Record who approved/rejected
        doc.approval_by = current_user
        doc.approval_date = frappe.utils.now()

        doc.save(ignore_permissions=True)
        doc.submit()
        frappe.db.commit()

        return f"Collection In Hand has been {doc.status} by {current_user}."


    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Collection In Hand API Error")
        return api_error(e)




# /////////////////////////////////////////////////////////
@frappe.whitelist()
def get_user_collections():
    print("in collection ....")
    user = frappe.session.user
    roles = frappe.get_roles(user)

    # Admin or Loan Manager sees all records
    if "System Manager" in roles or "Loan Manager" in roles:
        collections = frappe.get_list(
            "Collection In Hand",
            fields=["name", "employee", "amount_given_emp", "amount", "status"],
            order_by="creation desc"
        )
    else:
        # Get Employee linked to this user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not emp:
            return []

        # Fetch records where either employee OR amount_given_emp is the logged-in employee
        collections = frappe.get_list(
            "Collection In Hand",
            fields=["name", "employee", "amount_given_emp", "amount", "status"],
            filters={
                "docstatus": 0  # optional, only draft/pending
            },
            or_filters=[
                ["employee", "=", emp],
                ["amount_given_emp", "=", emp]
            ],
            order_by="creation desc"
        )

    return collections
