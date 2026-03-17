import frappe
from frappe.utils import now_datetime
import re

@frappe.whitelist(allow_guest=True)
def get_whatsapp_msg():
    try:
        from_phone = frappe.request.args.get("fromphone")
        message = frappe.request.args.get("message")
        from_name = frappe.request.args.get("fromname")
        external_link = ""

        if not from_phone or not message:
            frappe.throw("Missing required WhatsApp parameters")

        # 🔥 Extract first URL (any type)
        url_match = re.search(r"(https?://\S+)", message)

        if url_match:
            external_link = url_match.group(1)

            # Remove ONLY the URL, keep remaining text
            message = message.replace(external_link, "").strip()

        doc = frappe.get_doc({
            "doctype": "Whatsapp Messages",
            "phone_number": from_phone,
            "user_name": from_name,
            "message": message,
            "external_link":external_link,
            "type": "RECEIVED",
            "received_on": now_datetime()
        })

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "name": doc.name
        }

    except Exception as e:
        frappe.log_error(
            title="WhatsApp Webhook Error",
            message=frappe.get_traceback()
        )

        return {
            "status": "error",
            "message": str(e)
        }