# Copyright (c) 2025, Rutuja Somvanshi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ex_loan_management.api.utils import get_paginated_data

class Occupation(Document):
	pass




"""
	Get Occupation List (with optional pagination, search & sorting)
"""
@frappe.whitelist()
def occupation_list(page=1, page_size=10, search=None, sort_by="occupation", sort_order="asc", is_pagination=False):
    page = int(page)
    page_size = int(page_size)
    is_pagination = frappe.utils.sbool(is_pagination)  # convert "true"/"false"/1/0 into int

    return get_paginated_data(
        doctype="Occupation",
        fields=["name", "occupation"],
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        search_fields=["occupation"],
        is_pagination=is_pagination
    )

