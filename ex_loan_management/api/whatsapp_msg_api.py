import frappe
import requests
from urllib.parse import urlencode, quote

# @frappe.whitelist()
# def send_whatsapp_messages(mobile_no, customer_name, loan_id, emi_amount, emi_date, emi_day):
@frappe.whitelist(allow_guest=True)
def send_whatsapp_messages():
    customer_name="RUTUJA"
    loan_id="LOAN123"
    emi_amount="1000"
    emi_date="2026-02-01"
    emi_day="Monday"
    # TEMPLATENAME = "loan_emi_reminder"
    try:
        # api_url = "http://bhashsms.com/api/sendmsg.php"
        api_url = "http://bhashsms.com/api/sendmsgutil.php"
        # mobile_no = "7823064842"
        mobile_no = 9923921876
        image_url = "/files/WhatsApp Image 2026-01-31 at 11.59.33 AM.jpeg"
        host_url = frappe.request.host_url.rstrip("/")  # e.g. http://127.0.0.1:8000
        full_image_url = f"{host_url}{image_url}"
        print("full_image_url....",full_image_url)
        params = {
            "user": "Tejraj_BWAI",
            "pass": "123456",                # ⚠️ Move this to site_config.json ideally
            "sender": "BUZWAP",
            "phone": mobile_no,
            # "text": "loan_emi_reminder",          # Template name registered in BHASH # marketing template for image
            "text": "otp_verification",
            # "text":"loan_emi_notification", # utility template for image
            "priority": "wa",
            "stype": "normal",
            # "Params": f"{customer_name},{loan_id},{emi_amount},{emi_date},{emi_day},खालील",
            "params": 90098,
            "htype": "image",
            "url": full_image_url
        }

        response = requests.get(api_url, params=params, timeout=20)

        frappe.logger().info(f"WhatsApp API Response: {response.text}")

        return {
            "status": "success",
            "response": response.text
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp API Error")
        return {
            "status": "error",
            "message": str(e)
        }





@frappe.whitelist(allow_guest=True)
def test():
    try:
        # url = (
        #     "http://bhashsms.com/api/sendmsgutil.php"
        #     "?user=Tejraj_BWAI"
        #     "&pass=123456"
        #     "&sender=BUZWAP"
        #     "&phone=9923921876"
        #     "&text=otp_verification"
        #     "&priority=wa"
        #     "&stype=auth"
        #     "&params=1123"
        # )
        # print("url ...",url)

        params_value = "Rutuja,Gl001,1010,20-24-01,Monday,खालील"
        image_url = "http://192.168.1.127:8000/files/WhatsApp Image 2026-01-31 at 11.59.33 AM.jpeg"

        encoded_params = quote(params_value)
        encoded_image_url = quote(image_url, safe=":/")

        url = (
            "http://bhashsms.com/api/sendmsg.php"
            "?user=Tejraj_BWAI"
            "&pass=123456"
            "&sender=BUZWAP"
            "&phone=7823064842"
            "&text=tej_marathi_util_01"
            "&priority=wa"
            "&stype=normal"
            f"&params={encoded_params}"
            "&htype=image"
            f"&url={encoded_image_url}"
        )
        print("url //...",url)

        response = requests.get(url, timeout=20)

        frappe.logger().info(f"WhatsApp OTP Response: {response.text}")

        return {
            "status": "success",
            "response": response.text,
            "url": url
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp OTP Error")
        return {
            "status": "error",
            "message": str(e)
        }
