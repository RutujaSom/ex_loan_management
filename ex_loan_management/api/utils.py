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
    or_filters = [],
    link_images_fields=None,
    dynamic_search_fields=None,
):
    filters = filters or {}
    or_filters = or_filters or []
    extra_params = extra_params or {}
    link_fields = link_fields or {}

    # 🔹 Dynamic Search Support (main + linked doctypes)
    if search:
        search = search.strip()
        if search_fields:
            # Search in main doctype
            or_filters.extend([[doctype, f, "like", f"%{search}%"] for f in search_fields])

        # Dynamically search in linked doctypes if link_fields are defined
        if link_fields:
            print("TMA00576 .....",link_fields)
            for link_field, target_field in link_fields.items():
                field_meta = frappe.get_meta(doctype).get_field(link_field)
                if not field_meta or field_meta.fieldtype not in ["Link", "Dynamic Link"]:
                    continue

                print("field_meta.fieldtype ....",field_meta.fieldtype)

                if field_meta.fieldtype == "Dynamic Link":
                    # skip dynamic links for simplicity
                    continue

                target_doctype = field_meta.options
                print("target_doctype ...",target_doctype, ' ....target_field ...',target_field,' ...link_field. ',link_field)

                # Fetch linked record names that match
                linked_names = frappe.db.sql_list(f"""
                    SELECT name FROM `tab{target_doctype}`
                    WHERE {target_field} LIKE %s
                    LIMIT 100
                """, (f"%{search}%",))

                if linked_names:
                    or_filters.append([doctype, link_field, "in", linked_names])

        
        if dynamic_search_fields:
            print("dynamic_search_fields ....", dynamic_search_fields)

            for link_field, cfg in dynamic_search_fields.items():
                print("in for .......",link_field, cfg)

                target_doctype = cfg.get("doctype")
                target_field = cfg.get("field")

                if not target_doctype or not target_field:
                    print("in if")
                    continue

                # Ensure link field exists
                field_meta = frappe.get_meta(doctype).get_field(link_field)
                print("field_meta ......",field_meta)
                if not field_meta:
                    continue

                # Fetch matching linked names
                linked_names = frappe.db.sql_list(f"""
                    SELECT name FROM `tab{target_doctype}`
                    WHERE `{target_field}` LIKE %s
                    LIMIT 100
                """, (f"%{search}%",))

                print("linked_names ....", linked_names)

                if linked_names:
                    or_filters.append([doctype, link_field, "in", linked_names])



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
        data = [
            {
                **d,
                **{f: f"{host_url}{d[f]}" for f in image_fields if d.get(f)}
            }
            for d in data
        ]
        return data
    

    def extend_linked_images(data):
        host_url = frappe.request.host_url.rstrip("/")
        if not link_images_fields or not data:
            return data

        for fieldname, image_field in link_images_fields.items():
            if not any(d.get(fieldname) for d in data):
                continue

            field_meta = frappe.get_meta(doctype).get_field(fieldname)
            if not field_meta:
                continue

            # Determine target doctype(s)
            if field_meta.fieldtype == "Dynamic Link":
                dt_field = field_meta.options
                target_map = {}
                for d in data:
                    dt_name = d.get(dt_field)
                    rec_name = d.get(fieldname)
                    if dt_name and rec_name:
                        target_map.setdefault(dt_name, []).append(rec_name)
            else:
                target_map = {field_meta.options: [d[fieldname] for d in data if d.get(fieldname)]}
            # Fetch and attach images
            for target_doctype, names in target_map.items():
                records = frappe.get_all(target_doctype, filters={"name": ["in", names]}, fields=["name", image_field])
                values_map = {r["name"]: r.get(image_field) for r in records}
                for d in data:
                    rec_name = d.get(fieldname)
                    img = values_map.get(rec_name)
                    d[f"{fieldname}_image"] = f"{host_url}{img}" if img else ""

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

        # extend linked fields
        data = extend_linked_fields(data)
        data = extend_image_fields(data)
        data = extend_linked_images(data)

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
        data = extend_linked_images(data)
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





