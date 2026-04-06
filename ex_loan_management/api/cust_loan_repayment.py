import frappe
import pandas as pd
from frappe.utils import getdate, nowdate
from frappe.utils.file_manager import save_file
from ex_loan_management.api.utils import get_paginated_data, api_error

import frappe
from frappe.utils import nowdate


update_fields = [
    "name",
	"against_loan",
	"applicant",
	"repayment_type",
	"loan_disbursement",
	"loan_adjustment",
	"repayment_schedule_type",
	"loan_product",
	"company",
	"posting_date",
	"loan_restructure",
	"clearance_date",
	"rate_of_interest",
	"days_past_due",
	"custom_mode_of_payment",
	"is_term_loan",
	"custom_created_by",
	"due_date",
	"pending_principal_amount",
	"interest_payable",
	"payable_amount",
	"total_charges_payable",
	"payable_principal_amount",
	"penalty_amount",
	"amount_paid",
	"reference_number",
	"total_interest_paid",
	"total_penalty_paid",
	"reference_date",
	"principal_amount_paid",
	"total_charges_paid",
	"excess_amount",
	"custom_manual_remarks",
	"payment_account",
	"workflow_state",
	"custom_payment_proof",
]

"""
	Get Loan Repayment List (with optional pagination, search & sorting)
"""
@frappe.whitelist(allow_guest=False)
def loan_repayment_list(page=1, page_size=10, search=None, sort_by="name", sort_order="asc", is_pagination=False, loan_group=None, **kwargs):
    is_pagination = frappe.utils.sbool(is_pagination)
    extra_params = {"search": search} if search else {}
    if "cmd" in kwargs:
        del kwargs["cmd"]

    filters = {}
    for k, v in kwargs.items():
        if v not in [None, ""]:
            filters[k] = v

    user = frappe.session.user

    # 🔹 Check if user is an Agent
    if "Agent" in frappe.get_roles(user):
        employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_id:
            return None  # No employee mapped

        # Fetch loan groups assigned to this employee
        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee_id},
            pluck="loan_group"
        )

        if not groups:
            return {
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            }

        # 🔹 If agent selects a group → filter only that group
        if loan_group:
            groups = [loan_group] if loan_group in groups else []

        # If no valid group remains → no records
        if not groups:
            return {
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            }

        # Fetch Members belonging to allowed groups
        member_ids = frappe.get_all(
            "Member",
            filters={"group": ["in", groups]},
            pluck="name"
        )

        if member_ids:
            filters["applicant"] = ["in", member_ids]
        else:
            return {
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            }

    # 🔹 For non-Agents → no restriction
    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path

    return get_paginated_data(
        doctype="Loan Repayment",
        fields=update_fields,
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["applicant"],
        is_pagination=is_pagination,
        base_url=base_url,
        extra_params=extra_params,
		image_fields=["custom_payment_proof"],
        link_fields={"applicant": "member_name","against_loan": "custom_loan_id"},
		link_images_fields={"applicant": "member_image"} ,
		dynamic_search_fields = {"applicant":{"doctype": "Member", "field": "member_id"},}
    )








@frappe.whitelist()
def create_loan_repayment():
    try:
        data = frappe.form_dict  # works for JSON body and form-data
        user_doc = frappe.get_doc("User", frappe.session.user)
        files = frappe.request.files 
        print('user_doc ......',user_doc)
        try:
            emp_details = frappe.get_doc("Employee", {"user_id": user_doc.name})
            company = emp_details.company
        except:
            company = ""

        print('data.get("amount_paid") ///',data.get("amount_paid"), type(data.get("amount_paid")))

        # Step 1: Prepare Loan Application doc
        doc = frappe.get_doc({
            "doctype": "Loan Repayment",
            "against_loan": data.get("against_loan"),
            "applicant": data.get("applicant"),
            "repayment_type": "Normal Repayment",
            "loan_disbursement": data.get("loan_disbursement"),
			"loan_adjustment":data.get("loan_adjustment"),
            "company": company,
            "loan_product": data.get("loan_product"),
            "posting_date": data.get("posting_date"),
            "amount_paid": float(data.get("amount_paid")),
			"custom_mode_of_payment":data.get("custom_mode_of_payment"),
            "reference_number": data.get("reference_number"),
            "custom_manual_remarks": data.get("custom_manual_remarks"),
            "reference_date": data.get("reference_date"),
            "status": "Open",
			"repayment_schedule_type":"Monthly as per repayment start date"
        })

        if "custom_payment_proof" in files:
            upload = files.get("custom_payment_proof")
            if upload or upload.filename:
                file_doc = save_file(
					fname=upload.filename,
					content=upload.stream.read(),
					dt="Loan Repayment",
					# dn=doc.name,
					dn=1,
					is_private=0
				)
                doc.set("custom_payment_proof", file_doc.file_url)

        # Step 3: Insert Loan Application (runs validate() automatically)
        doc.insert(ignore_permissions=True)
        new_doc = apply_workflow(doc, "Submit for verification")
        frappe.db.commit()


        return {
            "status": "success",
            "status_code": 201,
            "msg": "Loan Repayment Created Successfully"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Loan Repayment API Error")
        # return {"status": "error", "message": str(e)}
        return api_error(e)


from frappe.model.workflow import apply_workflow
from urllib.parse import urljoin

@frappe.whitelist()
def loan_repayment_get(name):
    """
    Get Loan Repayment by name (primary key)
    Returns linked Loan Group name and full URLs for image fields
    """
    if not name:
        frappe.throw("Loan Repayment name is required")

    # Fetch Member
    repayments = frappe.get_all(
        "Loan Repayment",
        filters={"name": name},
        fields=update_fields
    )

    if not repayments:
        return {}

    repayment = repayments[0]
    if repayment.get("applicant"):
        member_doc = frappe.get_value("Member", repayment["applicant"], 
									  ["member_name","member_image"], as_dict=True)
        repayment["applicant_name"] = member_doc.get("member_name", "")
        host_url = frappe.request.host_url.rstrip("/")  # e.g. http://127.0.0.1:8000
        
        repayment["applicant_image"] = f"{host_url}{member_doc['member_image']}" if member_doc.get("member_image") else ""

    if repayment.get("custom_payment_proof"):
       repayment["custom_payment_proof"] = urljoin(host_url, repayment["custom_payment_proof"])
    return repayment
