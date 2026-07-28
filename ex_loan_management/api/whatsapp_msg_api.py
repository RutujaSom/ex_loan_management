import frappe
from types import SimpleNamespace

# ==========================================================
# SAFE IMPORTS (NOW IT WON'T CRASH)
# ==========================================================
import requests
from urllib.parse import quote
from datetime import datetime, timedelta
from frappe.utils import now_datetime, getdate, flt, money_in_words
from ex_loan_management.api.cust_payment_schedule import get_todays_emis


MARATHI_DAYS = {
    "Monday": "सोमवार",
    "Tuesday": "मंगळवार",
    "Wednesday": "बुधवार",
    "Thursday": "गुरुवार",
    "Friday": "शुक्रवार",
    "Saturday": "शनिवार",
    "Sunday": "रविवार",
}

from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file

from num_to_words import num_to_word


@frappe.whitelist(allow_guest=True)
def send_whatsapp_messages(mobile_no,member_name, loan_no, emi_amount, emi_date, extra_text="वरील"):
    print("in sec .......")
    # ensure_background_request()
    """
    Sends a WhatsApp message reminder for a loan EMI to a specified member.
    Args:
        member_name (str): Name of the member.
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

        # ✅ Ensure request context (VERY IMPORTANT)
        # ensure_background_request()

        emi_date_obj = emi_date

        if isinstance(emi_date, str):
            emi_date_obj = datetime.strptime(emi_date, "%d-%m-%Y").date()
        
        eng_day = frappe.utils.formatdate(
            emi_date_obj, "EEEE"
        )
        
        # print("eng_day ...",eng_day, emi_date, type(emi_date))
        # Remove +91 if present
        mobile_no = str(mobile_no).strip()
        if mobile_no.startswith("+91"):
            mobile_no = mobile_no[3:]

        # Marathi weekday
        marathi_day = MARATHI_DAYS.get(eng_day, eng_day)
                
        # =====================================================
        # ✅ Get WhatsApp image from Default Company
        # =====================================================
        company_name = frappe.db.get_single_value(
            "Global Defaults",
            "default_company"
        )
        
        company = frappe.get_doc("Company", company_name)

        custom_whatsapp_image = company.custom_whatsapp_image
        custom_last_whatsapp_msg = company.custom_last_whatapp_msg if company.custom_last_whatapp_msg else "लवकरात लवकर पेमेंट करून त्याचा स्क्रीन शॉट पाठवावा ही विनंती .."

        if not custom_whatsapp_image:
            frappe.throw(
                "WhatsApp message image is missing. Please upload an image in Company."
            )

        # Build full image URL
        # image_url = frappe.utils.get_url(custom_whatsapp_image)
        image_url= "https://tejrajmicro.com"+custom_whatsapp_image
        print("image_url ...",image_url)
        # Build params dynamically (ORDER MUST MATCH TEMPLATE)
        # params_value = f"{member_name},{loan_no},{emi_amount},{emi_date},{marathi_day}"
        params_value = f"{member_name},{loan_no},{emi_amount},{emi_date},{marathi_day},{custom_last_whatsapp_msg}"

        encoded_params = quote(params_value)
        encoded_image_url = quote(image_url, safe=":/")
        # print('mobile_no ...',mobile_no)

        url = (
            "http://bhashsms.com/api/sendmsgutil.php"
            "?user=Tejraj_BWAI"
            "&pass=123456"
            "&sender=BUZWAP"
            f"&phone={mobile_no}"
            "&text=emi_reminder_1"
            "&priority=wa"
            "&stype=normal"
            f"&Params={encoded_params}"
            "&htype=image"
            f"&url={encoded_image_url}"
        )

        response = requests.get(url, timeout=50)

        message = f""" नमस्कार {member_name}, 
            तुमचा लोन क्रमांक {loan_no} याचा हप्ता (ईएमआय) 
            रुपये {emi_amount}/- 
            दिनांक: {emi_date} 
            वार: {marathi_day} रोजी देय आहे. 
            तरी कृपया खालील क्यू आर कोड वर 
           {custom_last_whatsapp_msg} 
            धन्यवाद 
            तेजराज मायक्रो असोसिएशन
        """
        
        # Create document
        doc = frappe.get_doc({
            "doctype": "Whatsapp Messages",
            "phone_number": mobile_no,
            "user_name": member_name,
            "message": message,
            "attachment":custom_whatsapp_image,
            "type":"SENT",
            "received_on": now_datetime()
        })

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "response": response.text,
            "url": f"{url}"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp API Error")
        # frappe.local.response["http_status_code"] = 406
        return {
            "status": "error",
            "message": str(e)
        }




def emi_amount_in_marathi_words(amount):
    """Converts a numeric amount to Marathi words, e.g. 3181 -> 'तीन हजार एकशे एक्याऐंशी'"""
    return num_to_word(int(flt(amount)), lang='mr') + " रुपये"


@frappe.whitelist(allow_guest=True)
def send_due_notice(loan_repayment_schedule, loan_no, emi_date, emi_amount, 
                     send_to_borrower, send_to_co_borrower):
    """
    Sends a WhatsApp EMI due notice PDF to the borrower and/or co-borrower.
    Each recipient gets their own personalized PDF.
    """
    try:
        emi_number = frappe.db.get_value(
            "Repayment Schedule",
            {"parent": loan_repayment_schedule, "payment_date": datetime.strptime(emi_date, "%d-%m-%Y").date()},
            "idx"
        )

        loan_doc = frappe.get_doc("Loan", loan_no)
        loan_app_doc = frappe.get_doc("Loan Application", loan_doc.loan_application)

        # Build list of recipients based on the checkboxes
        recipients = []
        print("send_to_borrower, send_to_co_borrower ...",send_to_borrower, type(send_to_borrower), send_to_co_borrower,type(send_to_co_borrower))
        if str(send_to_borrower).lower() == "true":
            recipients.append({"member": loan_app_doc.applicant, "type": "Borrower"})
        if str(send_to_co_borrower).lower() == "true":
            if not loan_app_doc.custom_co_borrower:
                frappe.msgprint("No co-borrower is set on this loan application")
            else:
                recipients.append({"member": loan_app_doc.custom_co_borrower, "type": "Co-Borrower"})

        if not recipients:
            return {"status": "error", "message": "No recipients selected"}

        params_value = f"{emi_date}"
        encoded_params = quote(params_value)

        results = []

        for recipient in recipients:
            user_doc = frappe.get_doc("Member", recipient["member"])

            # ---- Existing reminder count for this member + EMI ----
            existing_reminder_count = frappe.db.count(
                "Notice Reminder",
                filters={
                    "member": user_doc.name,
                    "emi_date": datetime.strptime(emi_date, "%d-%m-%Y").date(),
                    "emi_no": emi_number,
                }
            )
            print("existing_reminder_count ...",existing_reminder_count)

            # ---- Last created record's ID (docname) for this member + EMI ----
            last_notice = frappe.db.get_value(
                "Notice Reminder",
                filters={},
                fieldname="name",
                order_by="creation desc"
            )
            # last_notice is None if the table is empty, else the last autoincrement id as a string, e.g. "42"
            print("last_notice .....",last_notice)
            last_notice_no = int(last_notice) if last_notice else 0

            reminder_no = existing_reminder_count + 1

            mobile_no = str(user_doc.mobile_no or "").strip()
            if not mobile_no:
                results.append({
                    "type": recipient["type"],
                    "status": "error",
                    "message": "No mobile number on file"
                })
                continue

            if mobile_no.startswith("+91"):
                mobile_no = mobile_no[3:]

            member_name = user_doc.member_name or user_doc.name

            # ---- Personalize loan_doc for THIS recipient before printing ----
            loan_doc.emi_amount = flt(emi_amount, 2)                      # ad-hoc attribute, not a real field
            loan_doc.emi_amount_in_words = emi_amount_in_marathi_words(emi_amount)
            loan_doc.emi_date = emi_date
            loan_doc.emi_number = emi_number
            loan_doc.notice_recipient_name = member_name                # ad-hoc, used by print format
            loan_doc.notice_recipient_type = recipient["type"]          # ad-hoc, "Borrower" / "Co-Borrower"
            loan_doc.reminder_no = reminder_no
            loan_doc.notice_no = str(last_notice_no + 1).zfill(4)

            if recipient["type"] == "Co-Borrower":
                print_format="Co-Borrower EMI Reminder Notice"
            else:
                print_format="EMI Reminder Notice"

            html = frappe.get_print(
                doctype="Loan",
                name=loan_no,
                print_format=print_format,
                doc=loan_doc,
            )
            pdf_content = get_pdf(html)

            # Unique filename per recipient so borrower's and co-borrower's PDFs don't overwrite each other
            file_doc = save_file(
                fname=f"EMI_Reminder_{loan_no}_{recipient['type'].replace('-', '_')}.pdf",
                content=pdf_content,
                dt="Loan",
                dn=loan_no,
                is_private=0,
            )
            pdf_url = frappe.utils.get_url(file_doc.file_url)

            url = (
                "http://bhashsms.com/api/sendmsgutil.php"
                "?user=Tejraj_BWAI"
                "&pass=123456"
                "&sender=BUZWAP"
                f"&phone={mobile_no}"
                "&text=due_emi_notice_temp_2707"
                "&priority=wa"
                "&stype=normal"
                f"&Params={encoded_params}"
                "&htype=document"
                f"&url={quote(pdf_url, safe=':/')}"
            )

            response = requests.get(url, timeout=50)
            # response = ""

            message = f"EMI Due Notice for the payment due on {emi_date}"

            doc = frappe.get_doc({
                "doctype": "Whatsapp Messages",
                "phone_number": mobile_no,
                "user_name": member_name,
                "message": message,
                "attachment": file_doc.file_url,
                "type": "SENT",
                "received_on": now_datetime()
            })
            doc.insert(ignore_permissions=True)
            print("doc ....",doc)
            reminder_doc = frappe.get_doc({
                "doctype": "Notice Reminder",
                "member": user_doc.name,
                "emi_date" : datetime.strptime(emi_date, "%d-%m-%Y").date(),
                "emi_no": emi_number,
                "reminder_no": reminder_no,
            })
            print("reminder_doc ...",reminder_doc)
            reminder_doc.insert(ignore_permissions=True)

            results.append({
                "type": recipient["type"],
                "response":response,
                "status": "success",
                "mobile_no": mobile_no,
                "url": url
            })

        frappe.db.commit()

        successes = [r for r in results if r["status"] == "success"]
        failures = [r for r in results if r["status"] == "error"]

        if failures and successes:
            overall_status = "partial"
        elif failures:
            overall_status = "error"
        else:
            overall_status = "success"

        return {"status": overall_status, "results": results}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp API Error")
        return {"status": "error", "message": str(e)}








@frappe.whitelist(allow_guest=True)
def send_bulk_whatsapp(rows):
    """
    Process bulk WhatsApp messages for selected EMI rows.
    Loops through each row and calls send_whatsapp_messages.
    
    Args:
        rows: List of dictionaries containing mobile, member, loan, date, amount
    
    Returns:
        dict: Summary of successful and failed messages
    """
    import json
    
    if isinstance(rows, str):
        rows = json.loads(rows)
    
    if not rows or not isinstance(rows, list):
        frappe.throw("No rows provided for WhatsApp messaging")
    
    successful = 0
    failed = 0
    errors = []
    
    for row in rows:
        try:
            mobile = row.get("mobile")
            member = row.get("member")
            loan = row.get("loan")
            date = row.get("date")
            amount = row.get("amount")
            
            if not all([mobile, member, loan, date, amount]):
                failed += 1
                errors.append(f"Missing data for row: {row}")
                continue

             # ✅ NORMALIZE DATE HERE
            # Supports: YYYY-MM-DD, DD-MM-YYYY, date object
            try:
                date_obj = getdate(date)   # safest in Frappe
                formatted_date = date_obj.strftime("%d-%m-%Y")
            except Exception:
                failed += 1
                errors.append(f"Invalid date format: {date}")
                continue
            
            # Call the existing send_whatsapp_messages function
            result = send_whatsapp_messages(
                mobile_no=mobile,
                member_name=member,
                loan_no=loan,
                emi_amount=amount,
                emi_date=formatted_date
            )
            
            if result.get("status") == "success":
                successful += 1
            else:
                failed += 1
                errors.append(f"Failed for {member} ({loan}): {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            failed += 1
            errors.append(f"Error for {row.get('member', 'Unknown')}: {str(e)}")
            frappe.log_error(
                title="Bulk WhatsApp Error",
                message=f"Failed to process row: {json.dumps(row)}\nError: {str(e)}"
            )
    
    # Prepare result message
    message = f"Successfully sent {successful} WhatsApp message(s)"
    if failed > 0:
        message += f". Failed: {failed}"
    
    if errors:
        frappe.log_error(
            title="Bulk WhatsApp Summary",
            message=f"Sent: {successful}, Failed: {failed}\nErrors:\n" + "\n".join(errors)
        )
    
    return {
        "message": message,
        "successful": successful,
        "failed": failed,
        "errors": errors
    }


@frappe.whitelist(allow_guest=True)
def send_emi_whatsapp_reminders():    

    """
    Sends WhatsApp reminders based on Company -> custom_message_schedule
    Only sends when current time matches row.time (HH:MM)
    """

    today = frappe.utils.getdate(frappe.utils.today())

    # company_name = frappe.defaults.get_user_default("Company")
    company_name = frappe.db.get_single_value(
        "Global Defaults",
        "default_company"
    )
    
    if not company_name:
        return

    # Fetch child table rows
    message_days = frappe.get_all(
        "Company Message Schedule",
        filters={
            "parent": company_name,
            "parenttype": "Company"
        },
        fields=["day", "time"],
        order_by="idx asc"
    )


    if not message_days:
        return

    all_emis = []

    for index, row in enumerate(message_days, start=1):
        # ⏰ Time check
        if not row.time:
            continue

        now = frappe.utils.now_datetime()

        row_time = frappe.utils.get_time(row.time)

        # Combine today's date with row time
        row_datetime = now.replace(
            hour=row_time.hour,
            minute=row_time.minute,
            second=0,
            microsecond=0
        )

        # ±15 minutes buffer
        buffer_start = row_datetime - timedelta(minutes=15)
        buffer_end = row_datetime + timedelta(minutes=15)
        
        # Check if now is inside buffer window
        if not (buffer_start <= now <= buffer_end):
            continue

        # 📅 Date calculation
        selected_date = today + timedelta(days=(row.day))

        emis = get_todays_emis(
            selected_date=selected_date,
            is_schedular=True
        )

        for emi in emis:
            mobile_no = emi.mobile_no or emi.mobile_no_2
            if not mobile_no:
                continue

            # WhatsApp API call (example)
            send_whatsapp_messages(
                mobile_no=mobile_no,
                member_name=emi.member_name,
                loan_no=emi.loan_id or emi.loan,
                emi_amount=emi.total_payment,
                emi_date=emi.payment_date,
            )

        all_emis.extend(emis)

    return all_emis








