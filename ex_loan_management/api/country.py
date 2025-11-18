import frappe
from .utils import get_paginated_data

"""
    Get Country List (with optional pagination, search & sorting)
"""
@frappe.whitelist()
def country_list(page=1, page_size=10,sort_by="country_name", sort_order="asc", search=None, is_pagination=False):
    extra_params = {"search": search} if search else {}
    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path

    return get_paginated_data(
        doctype="Country",
        fields=["name", "country_name", "code"],
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["country_name", "code"],
        is_pagination=frappe.utils.sbool(is_pagination),
        base_url=base_url,
        extra_params=extra_params
    )




"""
    Get Mode Of Payment List (with optional pagination, search & sorting)
"""
@frappe.whitelist()
def mode_of_payment_list(page=1, page_size=10,sort_by="mode_of_payment", sort_order="asc", search=None, is_pagination=False):
    extra_params = {"search": search} if search else {}
    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path

    filters={}
    filters['name'] = ["in", ["CASH", "ONLINE"]]
    return get_paginated_data(
        doctype="Mode of Payment",
        fields=["name", "mode_of_payment", "type"],
        search=search,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["mode_of_payment", "type"],
        is_pagination=frappe.utils.sbool(is_pagination),
        base_url=base_url,
        extra_params=extra_params
    )
