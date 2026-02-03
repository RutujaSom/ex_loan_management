
import frappe
from frappe.utils.pdf import get_pdf

@frappe.whitelist(allow_guest=True)
def loan_application_print(
    loan_application: str,
    print_format: str
):
    """
    API to get Loan Application print format PDF
    """

    PRINT_FORMAT_TYPES = {
        "POLICY_APPLY_LETTER":"Policy Apply Letter",
        "GROUP_DECLARATION":"Group Declaration And Terms And Consition VERSION JAN 24",
        "GROUP_LOAN_AGREEMENT":"GROUP LOAN AGREEMENT version jan 24",
        "DEMAND_PROMISSORY_NOTE":"demand promissory note",
        "SANCTION_LETTER":"Sanction Letter",
        "DP_NOTE_WAIVER_LETTER":"dp note cum waiver letter",
        "FACT_SHEET":"Fact Sheet",
        "INDIVIDUAL_DECLARATION":"Individual Decleration and Terms and Conditions version jan 24",
    }

    if not loan_application:
        frappe.throw("Loan Application is required")

    if not print_format:
        frappe.throw("Print Format is required")

    # 🔹 If key is passed, fetch actual print format name
    if print_format in PRINT_FORMAT_TYPES:
        print_format = PRINT_FORMAT_TYPES[print_format]

    # Permission check
    if not frappe.has_permission("Loan Application", "read", loan_application):
        frappe.throw("Not permitted")

    # Get document
    doc = frappe.get_doc("Loan Application", loan_application)

    # Get print format HTML
    html = frappe.get_print(
        doctype="Loan Application",
        name=loan_application,
        print_format=print_format,
        doc=doc,
        no_letterhead=0
    )

    # Convert to PDF
    pdf = get_pdf(html)

    frappe.local.response.filename = f"{loan_application}_{print_format}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"
