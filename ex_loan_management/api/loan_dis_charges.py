import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_loan_charges(loan, disbursed_amount=0):
    loan_doc = frappe.get_doc("Loan", loan)
    product = frappe.get_doc("Loan Product", loan_doc.loan_product)

    # ✅ Ensure numeric
    disb_amount = flt(disbursed_amount)

    calculated = {}   # charge_type -> amount
    result = []

    # 🔹 STEP 1: Non-GST charges
    base_charges = [ch for ch in product.loan_charges if not ch.custom_is_gst]
    gst_charges = [ch for ch in product.loan_charges if ch.custom_is_gst]

    # ---------- Calculate base charges ----------
    for ch in base_charges:
        base_amount = disb_amount

        percentage = flt(ch.percentage)
        fixed_amount = flt(ch.amount)

        if ch.charge_based_on == "Percentage":
            amount = flt(base_amount * percentage / 100, 2)
        else:
            amount = fixed_amount

        calculated[ch.charge_type] = amount

        result.append({
            "charge_type": ch.charge_type,
            "percentage": percentage,
            "amount": amount,
            "event": ch.event,
            "account": ch.income_account
        })

    # ---------- Calculate GST charges ----------
    for ch in gst_charges:
        base_amount = flt(calculated.get(ch.custom_applied_on))

        if not base_amount:
            frappe.throw(
                f"Base charge '{ch.custom_applied_on}' not found for {ch.charge_type}"
            )

        percentage = flt(ch.percentage)
        amount = flt(base_amount * percentage / 100, 2)

        calculated[ch.charge_type] = amount

        result.append({
            "charge_type": ch.charge_type,
            "percentage": percentage,
            "amount": amount,
            "event": ch.event,
            "account": ch.income_account
        })

    return result