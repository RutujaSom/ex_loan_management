# Copyright (c) 2025, Rutuja Somvanshi and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from openpyxl import load_workbook
from datetime import datetime

# class LoanMember(Document):
#     def before_save(self):
#         # check if all required verifications are done
#         if self.address_verified and self.pancard_verified and self.aadhar_verified:
#             self.status = "Verified"
#         if self.status ==  "Verified" and (not self.address_verified or not self.pancard_verified or not self.aadhar_verified):
#             frappe.throw("To set status as 'Verified', all verifications must be completed.")
        
    

import frappe
from frappe.model.document import Document

class LoanMember(Document):
    def before_save(self):
        if self.address_verified and self.pancard_verified and self.aadhar_verified:
            self.status = "Verified"
        if self.status == "Verified" and (not self.address_verified or not self.pancard_verified or not self.aadhar_verified):
            frappe.throw("To set status as 'Verified', all verifications must be completed.")

        self.member_name = f"{self.first_name or ''} {self.middle_name or ''} {self.last_name or ''}".strip()


@frappe.whitelist()
def import_loan_members(file_url):
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
    created_members = []
    created_groups = []
    created_branches = []
    created_occupations = []

    for row in rows:
        member_id = str(row.get("MEMBER NO")).strip() if row.get("MEMBER NO") else None
        if not member_id:
            continue  # Skip if no member_id

        # Member basic info
        member_name = row.get("NAME OF MEMBER")
        type_of_borrower = row.get("TYPE OF BORROWER")
        mobile_no = row.get("MOB NO")
        gender = row.get("GENDER")
        email = ""
        dob = row.get("DOB")
        entry_age = row.get("ENTRY AGE")
        completed_age = row.get("COMPLETED AGE")
        occupation = row.get("OCCUPATION")
        address = row.get("ADDRESS")
        state = row.get("STATE")
        country = "India"
        city = row.get("CITY")
        pincode = row.get("PIN CODE")
        nominee_name = row.get("NOMINEE FULL NAME")
        relation = str(row.get("RELATIONSHIP OF NOMINEE WITH BORROWER")).title()
        nominee_dob = row.get("NOMINEE DATE OF BIRTH")

        # Group and branch info
        group_id = str(row.get("GROUP CODE")).strip() if row.get("GROUP CODE") else None
        group_name = row.get("NAME OF GROUP")
        branch_code = str(row.get("BRANCH CODE")).strip() if row.get("BRANCH CODE") else None
        branch_name = row.get("BRANCH NAME")

        # 1️⃣ Create Loan Group if not exists
        if group_id and not frappe.db.exists("Loan Group", {"group_id": group_id}):
            print("in group_id ...", group_id)
            grp_doc = frappe.new_doc("Loan Group")
            grp_doc.group_id = group_id
            grp_doc.group_name = group_name
            grp_doc.insert(ignore_permissions=True)
            created_groups.append(group_id)

        # 2️⃣ Create Branch if not exists
        if branch_code and not frappe.db.exists("Branch", {"branch": branch_code}):
            print("in branch_code ...", branch_code, 'branch_name ....',branch_name)
            br_doc = frappe.new_doc("Branch")
            br_doc.branch = branch_code
            br_doc.branch_name = branch_name
            br_doc.insert(ignore_permissions=True)
            print('br_doc ....',br_doc)
            created_branches.append(branch_code)

        # 3️⃣ Create Occupation if not exists
        occupation_link = None
        if occupation:
            occupation = occupation.strip()
            if not frappe.db.exists("Occupation", {"occupation": occupation}):
                occ_doc = frappe.new_doc("Occupation")
                occ_doc.occupation = occupation
                occ_doc.insert(ignore_permissions=True)
                created_occupations.append(occupation)
                print("Created new Occupation:", occupation)
            occupation_link = frappe.db.get_value("Occupation", {"occupation": occupation})

        # 4️⃣ Skip if Loan Member already exists
        if frappe.db.exists("Loan Member", {"member_id": member_id}):
            skipped.append(member_id)
            continue
        print("member ....", member_id, 'entry_age ....',entry_age, 'relation ...',relation)
        if type_of_borrower == 'BORROWER':
            type_of_borrower ='Borrower'
        else:
            type_of_borrower = 'Co-Borrower'
		
        print('dob ....', dob, 'nominee_dob ...',nominee_dob, type(nominee_dob))
        if isinstance(nominee_dob, str):
            try:
              nominee_dob = datetime.strptime(str(nominee_dob), "%d-%m-%Y").date()
            except:
                try:
                   nominee_dob = datetime.strptime(str(nominee_dob), "%d/%m/%Y").date()
                except Exception as e:
                   print('error ....', e)
              
        print('nominee_dob ....', nominee_dob, type(nominee_dob))

        # 5️⃣ Create Loan Member
        doc = frappe.new_doc("Loan Member")
        doc.member_id = member_id
        doc.member_name = member_name
        doc.type_of_borrower = type_of_borrower
        doc.mobile_no = str(mobile_no) if mobile_no else None
        doc.gender = gender
        doc.email = email
        doc.dob = dob
        doc.entry_age = entry_age
        doc.completed_age = completed_age
        doc.occupation = occupation_link
        doc.address = address
        doc.state = state
        doc.country = country
        doc.city = city
        doc.pincode = pincode
        doc.nominee_name = nominee_name
        doc.relation = relation if str(relation)not in['None', None, ""] else ""
        doc.nominee_dob = nominee_dob

        # Link fields
        if group_id:
            group_id=frappe.db.exists("Loan Group", {"group_id": group_id})
            print('group_id .....',group_id)
            doc.group = group_id
        if branch_code:
            branch_code = frappe.db.exists("Branch", {"branch_code": branch_code})
            doc.branch_code = branch_code

        doc.insert(ignore_permissions=True)
        created_members.append(member_id)

    frappe.db.commit()

    # Prepare Summary
    msg = f"✅ Created {len(created_members)} Loan Members."
    if created_groups:
        msg += f"\n🏷 Created {len(created_groups)} Loan Groups: {', '.join(created_groups)}"
    if created_branches:
        msg += f"\n🏢 Created {len(created_branches)} Branches: {', '.join(created_branches)}"
    if created_occupations:
        msg += f"\n💼 Created {len(created_occupations)} Occupations: {', '.join(created_occupations)}"
    if skipped:
        msg += f"\n⏩ Skipped {len(skipped)} existing members: {', '.join(skipped)}"

    return msg




    