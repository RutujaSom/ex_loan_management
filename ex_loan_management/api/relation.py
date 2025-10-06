import frappe

@frappe.whitelist()
def get_relation_select_options():
    """
    Fetch dynamic options for the Select field 'nominee_relation' in Loan Application doctype
    """
    # Get the DocType
    doc = frappe.get_doc('DocType', 'Loan Application')

    # Find your Select field
    loan_field = next((f for f in doc.fields if f.fieldname == 'nominee_relation'), None)

    if loan_field and loan_field.fieldtype == "Select":
        # Split newline-separated options into list of dicts
        options = [{"value": opt} for opt in loan_field.options.split("\n") if opt]
    else:
        options = []

    return options
