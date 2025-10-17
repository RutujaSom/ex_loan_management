import frappe
from ex_loan_management.api.utils import get_paginated_data

update_fields = [
  "employee",
  "naming_series",
  "first_name",
  "middle_name",
  "last_name",
  "employee_name",
  "gender",
  "date_of_birth",
  "salutation",
  "date_of_joining",
  "user_id",
]

"""
	Get Loan Member List (with optional pagination, search & sorting)
"""

@frappe.whitelist()
def employee_list(page=1, page_size=10, search=None, sort_by="employee_name", sort_order="asc", is_pagination=False, **kwargs):
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
        doctype="Employee",
        fields=update_fields,
        filters=filters,   # ✅ Now your filters will be applied
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["employee_name"],
        is_pagination=is_pagination,
        base_url=base_url,
        extra_params=extra_params,
        # link_fields={"employee": "employee_name"},
    )

