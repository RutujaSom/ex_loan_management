# Copyright (c) 2025, Rutuja Somvanshi and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from openpyxl import load_workbook
import frappe


class LoanGroup(Document):
	pass


@frappe.whitelist()
def import_loan_groups(file_url):
    from frappe.utils.file_manager import get_file

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    filename = file_doc.file_name.lower()

    rows = []
    print("file_doc ....", file_doc, filename)

    # Read Excel file and convert rows to dictionary
    if filename.endswith(".xlsx"):
        file_path = file_doc.get_full_path()
        with open(file_path, "rb") as f:
            wb = load_workbook(f, data_only=True)
            ws = wb.active
            headers = [cell.value for cell in ws[1]]  # First row as headers
            print("headers ....", headers)
            for row in ws.iter_rows(min_row=2, values_only=True):
                rows.append(dict(zip(headers, row)))

    skipped = []
    updated_groups = []
    

    for row in rows:
        member_id = str(row.get("MEMBER NO")).strip() if row.get("MEMBER NO") else None
        if not member_id:
            continue  # Skip if no member_id

        group_id = str(row.get("GROUP CODE")).strip() if row.get("GROUP CODE") else None
        if not group_id:
            continue  # Skip if no group_id
        head_name = row.get("NAME OF GROUP HEAD")
        head_mobile_no = row.get("GROUP HEAD MOB NO")
        print('head_name ......',head_name,"head_mobile_no ......",head_mobile_no)

        # Check if Loan Group exists
        group_name = frappe.db.exists("Loan Group", {"group_id": group_id})
        if group_name:
            # Check if Loan Member exists
            member_name = frappe.db.exists("Loan Member", {"member_name": head_name,"mobile_no":head_mobile_no})
            print('member_name ......',member_name)
            if member_name:
                # Load Loan Group and update loan_head
                group_doc = frappe.get_doc("Loan Group", group_name)
                group_doc.group_head = member_name  # loan_head is a Link field to Loan Member
                group_doc.save(ignore_permissions=True)
                updated_groups.append(group_name)
            else:
                skipped.append(member_id)
        else:
            skipped.append(f"Group:{group_id}")

    frappe.db.commit()

    # Prepare Summary
    msg = f"✅ Processed {len(rows)} rows."
    if updated_groups:
        msg += f"\n🔗 Updated {len(updated_groups)} Loan Groups with loan_head: {', '.join(updated_groups)}"
    if skipped:
        msg += f"\n⏩ Skipped {len(skipped)} items: {', '.join(skipped)}"

    return msg



import frappe
from ex_loan_management.api.utils import get_paginated_data

"""
    Get Loan Group List (with optional pagination, search & sorting)
"""
@frappe.whitelist()
def loan_group_list(page=1, page_size=10,sort_by="group_name", sort_order="asc", search=None, is_pagination=False):
    extra_params = {"search": search} if search else {}
    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path

    return get_paginated_data(
        doctype="Loan Group",
        fields=["name", "group_name", "group_head","group_image"],
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["group_name", "group_head","group_image"],
        is_pagination=frappe.utils.sbool(is_pagination),
        base_url=base_url,
        extra_params=extra_params,
        link_fields={"group_head": "member_name"},
        image_fields=["group_image"]
    )
