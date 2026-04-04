import frappe

def execute():
    fieldname = "repayment_type"   # confirm fieldname
    doctype = "Loan Repayment"

    options = frappe.db.get_value(
        "DocField",
        {"parent": doctype, "fieldname": fieldname},
        "options"
    )

    if options and "Loan Closure" not in options:
        options += "\nLoan Closure"

        frappe.db.set_value(
            "DocField",
            {"parent": doctype, "fieldname": fieldname},
            "options",
            options
        )

        frappe.db.commit()