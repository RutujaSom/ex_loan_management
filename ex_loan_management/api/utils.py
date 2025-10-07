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

        for link_field, target_field in link_fields.items():
            ids = [d[link_field] for d in data if d.get(link_field)]
            if not ids:
                continue

            field_meta = frappe.get_meta(doctype).get_field(link_field)

            # Handle Link field
            if field_meta.fieldtype == "Link":
                target_doctype = field_meta.options

            # Handle Dynamic Link field
            elif field_meta.fieldtype == "Dynamic Link":
                # pick the doctype from applicant_type in each row
                target_doctype = None
                for d in data:
                    print('d.get(field_meta.options) ....',d.get(field_meta.options))
                    dynamic_dt = d.get(field_meta.options)  # e.g. "Loan Member"
                    if dynamic_dt:
                        target_doctype = dynamic_dt
                        break
                if not target_doctype:
                    continue

            else:
                continue

            records = frappe.get_all(
                target_doctype,
                filters={"name": ["in", ids]},
                fields=["name", target_field]
            )
            values_map = {r["name"]: r[target_field] for r in records}

            for d in data:
                if d.get(link_field):
                    d[f"{link_field}_{target_field}"] = values_map.get(d[link_field], "")
                else:
                    d[f"{link_field}_{target_field}"] = ""
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



def api_response(status="success", status_code=200, message=None, data=None):
    """Standardized API response"""
    resp = {
        "status": status,
        "status_code": status_code,
        "message": message or "",
    }
    if data:
        resp["data"] = data
    return resp

from frappe.utils.response import build_response


def api_error(e, status_code=406):
    """Return dynamic standardized error response"""
    errors = []

    # Check frappe validation errors (_server_messages or message_log)
    if hasattr(frappe.local, "message_log") and frappe.local.message_log:
        print("frappe.local.message_log ////// .. ",frappe.local.message_log)
        for m in frappe.local.message_log:
            try:
                if isinstance(m, dict) and "message" in m:
                    errors.append(clean_error_message(m["message"]))
                elif isinstance(m, str):
                    errors.append(clean_error_message(m))
            except Exception:
                errors.append(str(m))

        frappe.clear_messages()

    # If nothing found, fallback to exception string
    if not errors:
        errors = [str(e)]

    # Force HTTP status
    frappe.local.response["http_status_code"] = status_code
    frappe.local.response["message"] = {
        "status": "error",
        "status_code": status_code,
        "msg": ", ".join(errors)
    }
    return build_response("json")


def clean_error_message(msg: str) -> str:
    msg = msg.strip()

    # Handle "missing value" type
    if msg.startswith("Error: Value missing for Loan Member:"):
        field = msg.replace("Error: Value missing for Loan Member:", "").strip()
        return f"{field} is required"

    # Otherwise, return message as it is
    return msg





