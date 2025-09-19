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
]

"""
	Get Loan Member List (with optional pagination, search & sorting)
"""

@frappe.whitelist()
def collection_in_hand_list(page=1, page_size=10, search=None, sort_by="employee", sort_order="asc", is_pagination=False, **kwargs):
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
        search_fields=["employee"],
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
        doc = frappe.get_doc({
            "doctype": "Collection In Hand",
            "employee":data.get("employee"),
            "amount":(data.get("amount")),
            "given_to":data.get("given_to"),
            "posting_date":data.get("posting_date") or nowdate(),
        })
        if "payment_proof" in files:
            upload = "payment_proof"
            if not upload or not upload.filename:
                file_doc = save_file(
                    fname=upload.filename,
                    content=upload.stream.read(),
                    dt="Loan Member",
                    dn=1,
                    is_private=1
                )
                doc.set("payment_proof", file_doc.file_url)


        # Step 2: Insert Collection In Hand (runs validate() automatically)
        doc.insert(ignore_permissions=True)
        doc.submit()
        frappe.db.commit()

        return {
            "status": "success",
            "status_code": 201,
            "msg": "Collection In Hand Created Successfully"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Loan Repayment API Error")
        return api_error(e)


