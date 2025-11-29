# import frappe
# from frappe.utils.pdf import get_pdf

# @frappe.whitelist(allow_guest=True)
# def download_loan_agreement_pdf(loan_name=None):
#     print("loan_name ...",)
#     if not loan_name:
#         frappe.throw("Loan name is required")

#     html = frappe.get_print(
#         doctype="Loan",
#         name=loan_name,
#         print_format="GROUP LOAN AGREEMENT version jan 24",
#         as_pdf=False
#     )

#     pdf_data = get_pdf(html)

#     # Force download with descriptive filename
#     frappe.local.response.filename = f"GROUP_LOAN_AGREEMENT_{loan_name}.pdf"
#     frappe.local.response.filecontent = pdf_data
#     frappe.local.response.type = "download"




import frappe
from frappe.utils.pdf import get_pdf

@frappe.whitelist(allow_guest=True)
def download_loan_agreement_pdf(loan_name):
    if not loan_name:
        frappe.throw("Loan name is required")

    html = frappe.get_print(
        doctype="Loan Application",
        name=loan_name,
        print_format="GROUP LOAN AGREEMENT version jan 24",
        as_pdf=False
    )

    pdf_data = get_pdf(html)

    frappe.local.response = frappe._dict()
    frappe.local.response.filecontent = pdf_data
    frappe.local.response.filename = f"GROUP_LOAN_AGREEMENT_{loan_name}.pdf"
    frappe.local.response.type = "download"



@frappe.whitelist(allow_guest=True)
def download_group_declaration_pdf(loan_name):
    if not loan_name:
        frappe.throw("Loan name is required")

    html = frappe.get_print(
        doctype="Loan Application",
        name=loan_name,
        print_format="Group Declaration And Terms And Consition VERSION JAN 24",
        as_pdf=False
    )

    pdf_data = get_pdf(html)

    frappe.local.response = frappe._dict()
    frappe.local.response.filecontent = pdf_data
    frappe.local.response.filename = f"GROUP_DECLARATION_{loan_name}.pdf"
    frappe.local.response.type = "download"