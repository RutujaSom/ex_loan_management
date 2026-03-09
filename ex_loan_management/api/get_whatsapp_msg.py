
import frappe
from frappe.utils import now_datetime
from frappe.utils.response import build_response

@frappe.whitelist(allow_guest=True)
def get_whatsapp_msg():
    try:

        from_phone = frappe.request.args.get("fromphone")
        message = frappe.request.args.get("message")
        from_name = frappe.request.args.get("fromname")

        # Create document
        doc = frappe.get_doc({
            "doctype": "Whatsapp Messages",
            "phone_number": from_phone,
            "user_name": from_name,
            "message": message,
            # "attachment":"",'
            "type":"RECEIVED",
            "received_on": now_datetime()
        })

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return doc
    
    except Exception as e:
        frappe.local.response["message"] = {
            "status": "error",
            "status_code": 406,
            "msg": f"{e}"
        }
        return build_response("json")
        