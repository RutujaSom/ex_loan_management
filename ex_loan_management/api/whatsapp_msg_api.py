import frappe
import requests
from urllib.parse import urlencode, quote
from lending.loan_management.doctype.repayment_schedule.repayment_schedule import get_todays_emis
from datetime import datetime


MARATHI_DAYS = {
    "Monday": "सोमवार",
    "Tuesday": "मंगळवार",
    "Wednesday": "बुधवार",
    "Thursday": "गुरुवार",
    "Friday": "शुक्रवार",
    "Saturday": "शनिवार",
    "Sunday": "रविवार",
}


# वरील / खालील
@frappe.whitelist(allow_guest=True)
def send_whatsapp_messages(mobile_no,member_name, loan_no, emi_amount, emi_date, extra_text="वरील"):
    """
    Sends a WhatsApp message reminder for a loan EMI to a specified member.
    Args:
        member_name (str): Name of the loan member.
        loan_no (str): Loan number.
        emi_amount (str): EMI amount to be paid.
        emi_date (str or datetime): Date of the EMI.
        extra_text (str, optional): Additional text to include in the message. Defaults to "वरील".
    Returns:
        dict: A dictionary containing the status ("success" or "error") and the response or error message.
    Raises:
        Exception: Logs and returns error details if message sending fails.
    Notes:
        - The function constructs a WhatsApp message URL with the provided parameters and logs the response.
        - The weekday is translated to Marathi using the MARATHI_DAYS mapping.
        - The function currently returns the constructed URL as the response for debugging purposes.
    """
    try:

        emi_date_obj = emi_date

        if isinstance(emi_date, str):
            emi_date_obj = datetime.strptime(emi_date, "%d-%m-%Y").date()
        
        eng_day = frappe.utils.formatdate(
            emi_date_obj, "EEEE"
        )
        
        print("eng_day ...",eng_day, emi_date, type(emi_date))
        # Remove +91 if present
        mobile_no = str(mobile_no).strip()
        if mobile_no.startswith("+91"):
            mobile_no = mobile_no[3:]

        # Marathi weekday
        marathi_day = MARATHI_DAYS.get(eng_day, eng_day)
        print("marathi_day ...",marathi_day)

        # Build params dynamically (ORDER MUST MATCH TEMPLATE)
        params_value = f"{member_name},{loan_no},{emi_amount},{emi_date},{marathi_day},{extra_text}"

        # image_url = "https://i.ibb.co/9w4vXVY/Whats-App-Image-2022-07-26-at-2-57-21-PM.jpg"
        
        # ✅ Get image from Frappe public files
        image_url = frappe.utils.get_url("/files/Tejraj_scanner.jpeg")

        encoded_params = quote(params_value)
        encoded_image_url = quote(image_url, safe=":/")
        print('mobile_no ...',mobile_no)
        url = (
            "http://bhashsms.com/api/sendmsgutil.php"
            "?user=Tejraj_BWAI"
            "&pass=123456"
            "&sender=BUZWAP"
            f"&phone={mobile_no}"
            "&text=loan_emi_reminder"
            "&priority=wa"
            "&stype=normal"
            f"&Params={encoded_params}"
            "&htype=image"
            f"&url={encoded_image_url}"
        )

        print("Final URL:", url)

        response = requests.get(url, timeout=20)
        # response = url

        frappe.logger().info(f"WhatsApp Response: {response.text}")
        return {
            "status": "success",
            "response": response.text
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp API Error")
        # frappe.local.response["http_status_code"] = 406
        return {
            "status": "error",
            "message": str(e)
        }




@frappe.whitelist(allow_guest=True)
def send_emi_whatsapp_reminders():
    """
    Sends WhatsApp reminders for EMIs due today.
    This function retrieves all EMIs that are due on the current date and attempts to send WhatsApp reminders to the associated mobile numbers. 
    If a mobile number is not available for an EMI, it skips sending the reminder for that entry.
    
    Returns:
        list: A list of EMI objects that are due today.
    """

    emis = get_todays_emis(selected_date=frappe.utils.today(), is_schedular=True)
    

    for emi in emis:
        
        mobile_no = emi.mobile_no or emi.mobile_no_2
        if not mobile_no:
            continue

        payment_date = emi.payment_date
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        else:
            payment_date = payment_date.strftime("%d-%m-%Y")

        # send_whatsapp_messages(
        #     mobile_no=mobile_no,
        #     customer_name=emi.member_name,
        #     loan_id=emi.loan_id or emi.loan,
        #     emi_amount=emi.total_payment,
        #     emi_date=emi.payment_date,
        # )
    return emis



