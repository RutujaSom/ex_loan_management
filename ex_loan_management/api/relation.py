import frappe

@frappe.whitelist(allow_guest=False)
def get_relation_select_options():
    """
    Fetch dynamic options for the Select field 'custom_nominee_relation'
    from Loan Application (including Custom Fields)
    """

    meta = frappe.get_meta("Loan Application")

    # Debug (optional)
    for field in meta.fields:
        frappe.logger().info(
            f"{field.fieldname} | {field.fieldtype} | {field.options}"
        )

    field = meta.get_field("custom_nominee_relation")

    if field and field.fieldtype == "Select":
        options = [
            {"value": opt.strip()}
            for opt in (field.options or "").split("\n")
            if opt.strip()
        ]
    else:
        options = []

    return options
