import frappe
import random
import string
from frappe.utils import now_datetime, add_to_date
from ex_loan_management.api.utils import api_error

# Step 1: Send OTP to email
@frappe.whitelist(allow_guest=True)
def send_forgot_password_otp(email):
    user = frappe.db.get_value("User", {"email": email}, ["name", "email"])
    if not user:
        return api_error("User with this email does not exist.")

    # Generate 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))
    expiry_time = add_to_date(now_datetime(), minutes=10)
    print('expiry_time ...',expiry_time, type(expiry_time), 'otp .....',otp)

    # Store OTP & expiry in user record (custom fields recommended)
    frappe.db.set_value("User", user[0], {
        "otp": otp,
        "otp_expire_time": expiry_time
    })
    try:
        # Send email
        frappe.sendmail(
            recipients=[email],
            subject="Password Reset OTP",
            message=f"Your OTP for password reset is {otp}. It will expire in 10 minutes."
        )
    except Exception as e:
        print("E ..................",e)
    return {
        "status": "success",
        "status_code": 201,
        "msg": "OTP sent to your email."}


# Step 2: Verify OTP
@frappe.whitelist(allow_guest=True)
def verify_forgot_password_otp(email, otp):
    stored_otp, expiry_time = frappe.db.get_value("User", {"email": email}, ["otp", "otp_expire_time"])

    if not stored_otp:
        return api_error("No OTP found. Please request OTP again.")

    if now_datetime() > expiry_time:
        return api_error("OTP expired. Please request OTP again.")

    if otp != stored_otp:
        return api_error("Invalid OTP.")

    return {
        "status": "success",
        "status_code": 201,
        "msg": "OTP verified successfully."
    }


# Step 3: Reset password
@frappe.whitelist(allow_guest=True)
def reset_password_with_otp(email, otp, new_password, confirm_password):
    if new_password != confirm_password:
        return api_error("New password and confirm password do not match.")

    stored_otp, expiry_time = frappe.db.get_value("User", {"email": email}, ["otp", "otp_expire_time"])

    if not stored_otp:
        return api_error("No OTP found. Please request OTP again.")

    if now_datetime() > expiry_time:
        return api_error("OTP expired. Please request OTP again.")

    if otp != stored_otp:
        return api_error("Invalid OTP.")

    # Update password
    user = frappe.get_doc("User", {"email": email})
    user.new_password = new_password
    user.save(ignore_permissions=True)

    # Clear OTP fields
    frappe.db.set_value("User", user.name, {
        "otp": 0,
        "otp_expire_time": None
    })

    return {
            "status": "success",
            "status_code": 201,
            "msg": ("Password updated successfully")
    }