# import frappe

# def get_paginated_data(
#     doctype, 
#     fields=None, 
#     filters=None, 
#     search=None, 
#     sort_by="creation", 
#     sort_order="asc", 
#     page=1, 
#     page_size=10,
#     search_fields=None,
#     is_pagination=False
# ):
#     print("is_pagination ....",is_pagination)
#     """
#     Generic function for fetching data with optional pagination.
#     """
#     filters = filters or {}

#     # Search support
#     if search and search_fields:
#         search_filters = []
#         for f in search_fields:
#             search_filters.append([doctype, f, "like", f"%{search}%"])
#         filters["or_filters"] = search_filters
#     print('filters ....',filters)
#     if is_pagination:
#         # Count total rows
#         total_count = frappe.db.count(doctype, filters=filters)
#         start = (page - 1) * page_size

#         data = frappe.get_all(
#             doctype,
#             fields=fields,
#             filters=filters,
#             order_by=f"{sort_by} {sort_order}",
#             start=start,
#             page_length=page_size
#         )

#         return {
#             "total": total_count,
#             "page": page,
#             "page_size": page_size,
#             "results": data
#         }
#     else:
#         # Return all data without pagination
#         data = frappe.get_all(
#             doctype,
#             fields=fields,
#             filters=filters,
#             order_by=f"{sort_by} {sort_order}"
#         )
#         return data




# import frappe
# import math
# from urllib.parse import urlencode

# def get_paginated_data(
#     doctype, 
#     fields=None, 
#     filters=None, 
#     search=None, 
#     sort_by="creation", 
#     sort_order="asc", 
#     page=1, 
#     page_size=10,
#     search_fields=None,
#     is_pagination=False,
#     base_url=None,   # pass request.base_url or frappe.local.request.path
#     extra_params=None  # pass other query params like org, search etc.
# ):
#     filters = filters or {}
#     or_filters = []
#     extra_params = extra_params or {}

#     # Search support
#     if search and search_fields:
#         for f in search_fields:
#             or_filters.append([doctype, f, "like", f"%{search}%"])

#     if is_pagination:
#         # Count total rows (manual because frappe.db.count doesn’t support or_filters)
#         total_count = len(
#             frappe.get_all(
#                 doctype,
#                 filters=filters,
#                 or_filters=or_filters,
#                 fields=["name"]
#             )
#         )
#         start = (page - 1) * page_size

#         data = frappe.get_all(
#             doctype,
#             fields=fields,
#             filters=filters,
#             or_filters=or_filters,
#             order_by=f"{sort_by} {sort_order}",
#             start=start,
#             page_length=page_size
#         )

#         total_pages = math.ceil(total_count / page_size) if page_size else 1

#         # Build next/previous links
#         def build_url(p):
#             print('base_url ....',base_url)
            
#             if not base_url:
#                 return None
#             params = {**extra_params, "page": p, "page_size": page_size, "is_pagination": True}
#             print('{urlencode(params)} .....',urlencode(params))
#             return f"{base_url}?{urlencode(params)}"

#         next_url = build_url(page + 1) if page < total_pages else None
#         prev_url = build_url(page - 1) if page > 1 else None

#         return {
#             "count": total_count,
#             "next": next_url,
#             "previous": prev_url,
#             "results": data
#         }

#     else:
#         # Return all data without pagination
#         data = frappe.get_all(
#             doctype,
#             fields=fields,
#             filters=filters,
#             or_filters=or_filters,
#             order_by=f"{sort_by} {sort_order}"
#         )
#         return data






import frappe
import math
from urllib.parse import urlencode

def get_paginated_data(
    doctype, 
    fields=None, 
    filters=None, 
    search=None, 
    sort_by="creation", 
    sort_order="asc", 
    page=1, 
    page_size=10,
    search_fields=None,
    is_pagination=False,
    base_url=None,
    extra_params=None,
    link_fields=None,  # NEW: dict of {link_field: target_field}
    image_fields=None,
):
    filters = filters or {}
    or_filters = []
    extra_params = extra_params or {}
    link_fields = link_fields or {}

    # Search support
    if search and search_fields:
        for f in search_fields:
            or_filters.append([doctype, f, "like", f"%{search}%"])

    def extend_linked_fields(data):
        """Add linked field values without loop-heavy queries"""
        if not link_fields or not data:
            return data

        # collect all link field values for batch query
        for link_field, target_field in link_fields.items():
            print('link_field ...',link_field,'.target_field ...',target_field)
            ids = [d[link_field] for d in data if d.get(link_field)]
            if ids:
                records = frappe.get_all(
                    frappe.get_meta(doctype).get_field(link_field).options,
                    filters={"name": ["in", ids]},
                    fields=["name", target_field]
                )
                print('records ....',records)

                values_map = {r["name"]: r[target_field] for r in records}

                print('values_map ....',values_map,' .... doctype ....',doctype)
                for d in data:
                    if d.get(link_field):
                        d[f"{link_field}_{target_field}"] = values_map.get(d[link_field])
        return data
    
    def extend_image_fields(data):
        """Prefix image fields with full host URL"""
        if not image_fields or not data:
            return data

        host_url = frappe.request.host_url.rstrip("/")  # e.g. http://127.0.0.1:8000
        print('host_url ....',host_url)
        print('base_url ....',base_url)
        data = [
            {
                **d,
                **{f: f"{host_url}{d[f]}" for f in image_fields if d.get(f)}
            }
            for d in data
        ]
        return data


    if is_pagination:
        # Count total rows
        total_count = len(
            frappe.get_all(
                doctype,
                filters=filters,
                or_filters=or_filters,
                fields=["name"]
            )
        )
        start = (page - 1) * page_size

        data = frappe.get_all(
            doctype,
            fields=fields,
            filters=filters,
            or_filters=or_filters,
            order_by=f"{sort_by} {sort_order}",
            start=start,
            page_length=page_size
        )
        print('data ...', len(data))

        # extend linked fields
        data = extend_linked_fields(data)
        data = extend_image_fields(data)

        total_pages = math.ceil(total_count / page_size) if page_size else 1

        def build_url(p):
            if not base_url:
                return None
            params = {**extra_params, "page": p, "page_size": page_size, "is_pagination": True}
            return f"{base_url}?{urlencode(params)}"

        next_url = build_url(page + 1) if page < total_pages else None
        prev_url = build_url(page - 1) if page > 1 else None

        return {
            "count": total_count,
            "next": next_url,
            "previous": prev_url,
            "results": data
        }
    else:
        data = frappe.get_all(
            doctype,
            fields=fields,
            filters=filters,
            or_filters=or_filters,
            order_by=f"{sort_by} {sort_order}"
        )
        data = extend_image_fields(data)
        return extend_linked_fields(data)

























