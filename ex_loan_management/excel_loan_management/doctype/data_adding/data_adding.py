# # Copyright (c) 2026, Rutuja Somvanshi and contributors
# # For license information, please see license.txt

# # import frappe
# from frappe.model.document import Document


# class Dataadding(Document):
# 	pass




from frappe.model.document import Document
import frappe
import pandas as pd
from datetime import datetime, date
from frappe.utils import add_days, getdate



class Dataadding(Document):
    pass


# -----------------------------
# HELPERS
# -----------------------------
def safe(val):
    """Convert NaN / NaT to None (MySQL safe)"""
    return None if pd.isna(val) else val


# 🔴 CUTOFF: AFTER 21-03-2026 ONLY
MIN_EMI_DATE = date(2026, 3, 21)

import pandas as pd
from datetime import datetime, date

def parse_dd_mm_yyyy(value):
    """
    Guaranteed DD-MM-YYYY parsing.
    Handles:
    - Excel date cells
    - Strings like 9-5-2026, 09-05-2026
    - NaN safely
    """
    if value is None or value == "" or pd.isna(value):
        return None

    # Pandas Timestamp
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()

    # String date
    try:
        return getdate(str(value).strip())
    except Exception:
        return None

def safe_getdate(value):
    if value is None or value == "" or pd.isna(value):
        return None

    # Pandas Timestamp
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()

    # String date
    try:
        return getdate(str(value).strip())
    except Exception:
        return None
	

@frappe.whitelist()
def import_data_adding(file_url):

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    # df = pd.read_excel(file_path)
    df = pd.read_excel(
		file_path,
		dtype=str,          # 🔥 CRITICAL
		engine="openpyxl"   # ensures no Excel auto-date coercion
	)
    df.columns = df.columns.str.strip()

    # -----------------------------
    # SAFE DATE PARSING
    # -----------------------------
    df["Start Date"] = df["Start Date"].apply(parse_dd_mm_yyyy)
    df["Payment Date"] = df["Payment Date"].apply(parse_dd_mm_yyyy)
    
    inserted = []
    skipped = []
    errors = []

    # -----------------------------
    # GROUP BY LOAN
    # -----------------------------
    for loan, rows in df.groupby("Loan"):
        print("in loan .....", rows["Payment Date"], '.......',pd.isna(rows["Payment Date"]))
        try:
            # -----------------------------
            # VALID ROWS: Payment Date > 21-03-2026
            # -----------------------------
            # valid_rows = rows[
            #     safe_getdate(rows["Payment Date"]).notna() &
            #     (safe_getdate(rows["Payment Date"] )> MIN_EMI_DATE)
            # ]
            # # print('valid_rows ...',valid_rows)

            # skipped_rows = rows[
            #     (safe_getdate(rows["Payment Date"]).isna()) |
            #     (safe_getdate(rows["Payment Date"]) <= MIN_EMI_DATE)
            # ]

            valid_rows = rows[
                rows["Payment Date"].notna() &
                (rows["Payment Date"] > MIN_EMI_DATE)
            ]

            skipped_rows = rows[
                rows["Payment Date"].isna() |
                (rows["Payment Date"] <= MIN_EMI_DATE)
            ]
            # print("skipped_rows ...",skipped_rows)

            for _, row in skipped_rows.iterrows():
                skipped.append({
                    "app_id ......": loan,
                    "payment_date": safe_getdate(row["Payment Date"])
                })
            print("valid_rows .........")
            if valid_rows.empty:
                continue
            print("after valid_rows ...")

            # -----------------------------
            # TERMS = COUNT OF VALID ROWS
            # -----------------------------
            terms = len(valid_rows)

            # -----------------------------
            # START DATE (SAFE)
            # -----------------------------
            start_date = safe_getdate(valid_rows.iloc[0]["Payment Date"])
            if pd.isna(start_date) or start_date <= MIN_EMI_DATE:
                start_date = MIN_EMI_DATE
            # print("start_date ...",start_date,'terms ...',terms)

            # -----------------------------
            # INSERT RECORDS
            # -----------------------------
            for _, row in valid_rows.iterrows():
                # print('...... row["Payment Date"] .......',row["Payment Date"], type(row["Payment Date"]))
                try:
                    doc = frappe.new_doc("Data adding")

                    doc.app_id = loan
                    doc.loan_id = safe(row["LOAN ID"])
                    doc.start_date = start_date
                    doc.emi_date = safe_getdate(row["Payment Date"])
                    doc.terms = terms

                    doc.loan_amount = safe(row["Loan Amount"])
                    doc.roi = safe(row["Rate Of Interest"])
                    doc.principal_amount = safe(row["Principal Amount"])
                    doc.int_amount = safe(row["Interest Amount"])
                    doc.bal_amount = safe(row["Balance Loan Amount"])
                    doc.total_amount = safe(row["Total Payment"])

                    doc.insert(ignore_permissions=True)
                    inserted.append(doc.name)
                except Exception as e:
                    print("e ......",e)

        except Exception as e:
            errors.append({
                "app_id": loan, 
                "error": str(e)
            })

    frappe.db.commit()

    return f"inserted_count: {len(inserted)}, . .. skipped_count: {len(skipped)}, . ... skipped_records: {skipped}, . .. errors: {errors}"






@frappe.whitelist()
def import_update_loan_and_member(file_url):
    """
    Update existing Data adding records using another Excel sheet.
    Match by app_id, update loan_id, member_id, member_name.
    """

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()

    updated = []
    skipped = []
    errors = []

    for _, row in df.iterrows():
        try:
            app_id = safe(row.get("ID"))
            member_id = safe(row.get("Applicant"))
            loan_id = safe(row.get("Loan Id"))

            if not app_id:
                skipped.append({"reason": "Missing app_id", "row": row.to_dict()})
                continue

            # -----------------------------
            # FETCH EXISTING RECORDS
            # -----------------------------
            records = frappe.get_all(
                "Data adding",
                filters={"app_id": app_id},
                pluck="name"
            )
            print('records ....',records)

            if not records:
                skipped.append({"app_id": app_id, "reason": "No Data adding records"})
                continue

            # -----------------------------
            # GET MEMBER NAME
            # -----------------------------
            member_name = None
            if member_id:
                member_name = frappe.db.get_value(
                    "Member",
                    member_id,
                    "member_name"
                )
            print("member_name ....",member_name)

            # -----------------------------
            # UPDATE RECORDS
            # -----------------------------
            for docname in records:
                doc = frappe.get_doc("Data adding", docname)
                doc.loan_id = loan_id
                doc.member_id = member_id
                doc.member_name = member_name
                doc.save(ignore_permissions=True)
                updated.append(docname)

        except Exception as e:
            errors.append({
                "app_id": row.get("ID"),
                "error": str(e)
            })

    frappe.db.commit()

    return {
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "skipped_records": skipped,
        "errors": errors,
    }



@frappe.whitelist(allow_guest=True)
def sync_start_date_from_emi():
    """
    For each (app_id, loan_id):
    - Find earliest emi_date
    - Update start_date for all matching records
    """

    updated = []
    skipped = []
    errors = []

    # -----------------------------
    # GET DISTINCT app_id + loan_id
    # -----------------------------
    groups = frappe.db.sql("""
        SELECT app_id, loan_id
        FROM `tabData adding`
        WHERE emi_date IS NOT NULL
        GROUP BY app_id, loan_id
    """, as_dict=True)

    for grp in groups:
        try:
            app_id = grp.app_id
            loan_id = grp.loan_id

            # -----------------------------
            # GET FIRST EMI DATE
            # -----------------------------
            first_emi = frappe.db.sql("""
                SELECT MIN(emi_date)
                FROM `tabData adding`
                WHERE app_id = %s
                  AND loan_id = %s
                  AND emi_date IS NOT NULL
            """, (app_id, loan_id))[0][0]

            if not first_emi:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": "No EMI date"
                })
                continue

            # -----------------------------
            # UPDATE ALL RECORDS
            # -----------------------------
            frappe.db.sql("""
                UPDATE `tabData adding`
                SET start_date = %s
                WHERE app_id = %s
                  AND loan_id = %s
            """, (first_emi, app_id, loan_id))

            updated.append({
                "app_id": app_id,
                "loan_id": loan_id,
                "start_date": first_emi
            })

        except Exception as e:
            errors.append({
                "app_id": grp.app_id,
                "loan_id": grp.loan_id,
                "error": str(e)
            })

    frappe.db.commit()

    return {
        "updated_groups": len(updated),
        "updated_records": updated,
        "skipped": skipped,
        "errors": errors
    }


@frappe.whitelist()
def update_loan_amount_from_excel(file_url):
    """
    Update loan amount in Loan doctype from Excel sheet.
    Match loan by custom_loan_id field with "LOAN" column in Excel.
    Update loan_amount from "Amount" column in Excel.
    """
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    df = pd.read_excel(
        file_path,
        dtype=str,
        engine="openpyxl"
    )
    df.columns = df.columns.str.strip()

    updated = []
    skipped = []
    errors = []

    for _, row in df.iterrows():
        try:
            loan_id = safe(row.get("LOAN ID NEW"))
            amount = safe(row.get("Amount"))

            if not loan_id:
                skipped.append({"reason": "Missing LOAN ID", "row": row.to_dict()})
                continue

            if amount is None:
                skipped.append({"reason": "Missing Amount", "loan_id": loan_id, "row": row.to_dict()})
                continue

            # Convert amount to float
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                skipped.append({"reason": f"Invalid amount value: {amount}", "loan_id": loan_id, "row": row.to_dict()})
                continue

            # Find Loan with matching custom_loan_id
            loan_name = frappe.db.get_value("Loan", {"name": loan_id}, "name")

            if not loan_name:
                skipped.append({"reason": f"Loan with name '{loan_id}' not found", "loan_id": loan_id, "row": row.to_dict()})
                continue

            # Update loan amount
            loan_doc = frappe.get_doc("Loan", loan_name)

            if loan_doc.docstatus == 0:
                # ✅ Draft → directly update
                frappe.db.set_value(
                    "Loan",
                    loan_doc.name,
                    "loan_amount",
                    amount
                )

            loan_doc.loan_amount = amount
            loan_doc.save(ignore_permissions=True)
            updated.append({"loan_name": loan_name, "loan_id": loan_id, "new_amount": amount})

        except Exception as e:
            errors.append({
                "loan_id": row.get("LOAN"),
                "error": str(e),
                "row": row.to_dict()
            })

    frappe.db.commit()

    return {
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "updated_records": updated,
        "skipped_records": skipped,
        "errors": errors
    }


@frappe.whitelist(allow_guest=True)
def sync_data_adding_to_loan():
    print("in data ......")
    """
    Sync data from 'Data adding' doctype to 'Loan' doctype.
    
    For each unique combination of (app_id, loan_id) in Data adding:
    - Check if a Loan with the same custom_app_id and custom_loan_id already exists
    - If exists: skip
    - If not exists: create a new Loan document with the aggregated data
    - Submit the loan to trigger repayment schedule creation (normal flow like web)
    
    Field mapping:
    - app_id -> custom_app_id
    - loan_id -> custom_loan_id
    - loan_amount -> loan_amount
    - roi -> rate_of_interest
    - terms -> repayment_periods
    - start_date -> repayment_start_date
    - total_amount -> total_payment
    - member_id -> applicant (Member)
    - member_name -> applicant_name
    """
    
    inserted = []
    skipped = []
    errors = []
    
    # -----------------------------
    # GET DISTINCT app_id + loan_id FROM Data adding
    # -----------------------------
    groups = frappe.db.sql("""
        SELECT 
            app_id, 
            loan_id
        FROM `tabData adding`
        WHERE app_id IS NOT NULL 
          AND loan_id IS NOT NULL
        GROUP BY app_id, loan_id
    """, as_dict=True)
    print("groups ....", len(groups))
    
    for grp in groups:
        try:
            app_id = grp.app_id
            loan_id = grp.loan_id
            
            # -----------------------------
            # CHECK IF LOAN ALREADY EXISTS
            # -----------------------------
            existing_loan = frappe.db.exists(
                "Loan",
                {
                    "custom_app_id": app_id,
                    "custom_loan_id": loan_id
                }
            )
            
            if existing_loan:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": f"Loan {existing_loan} already exists"
                })
                continue
            
            # -----------------------------
            # GET AGGREGATED DATA FOR THIS LOAN
            # -----------------------------
            loan_data = frappe.db.sql("""
                SELECT 
                    loan_amount,
                    roi,
                    terms,
                    MIN(start_date) as start_date,
                    SUM(total_amount) as total_amount,
                    member_id,
                    member_name
                FROM `tabData adding`
                WHERE app_id = %s
                  AND loan_id = %s
                GROUP BY app_id, loan_id
            """, (app_id, loan_id), as_dict=True)
            print("loan_data ....",len(loan_data))
            
            if not loan_data or len(loan_data) == 0:
                errors.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": "No data found in Data adding"
                })
                continue
            
            data = loan_data[0]
            
            # -----------------------------
            # GET APPLICANT (MEMBER)
            # -----------------------------
            applicant = None
            if data.member_id:
                applicant = frappe.db.get_value("Member", {"member_id": data.member_id}, "name")
            
            if not applicant:
                errors.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": f"Member with member_id '{data.member_id}' not found"
                })
                continue
            
            # -----------------------------
            # GET LOAN PRODUCT BY ROI
            # -----------------------------
            loan_product = None
            if data.roi:
                loan_product = frappe.db.get_value("Loan Product", {"rate_of_interest": data.roi}, "name")
            
            if not loan_product:
                errors.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": f"Loan Product with ROI '{data.roi}' not found"
                })
                continue
            
            # -----------------------------
            # CREATE LOAN DOCUMENT
            # -----------------------------
            loan_doc = frappe.get_doc({
                "doctype": "Loan",
                "applicant_type": "Member",
                "applicant": applicant,
                "applicant_name": data.member_name,
                "company": "Tejraj Micro Association",
                "loan_product": loan_product,
                "loan_amount": data.loan_amount or 0,
                "rate_of_interest": data.roi or 0,
                "is_term_loan": 1,
                "repayment_method": "Repay Over Number of Periods",
                "repayment_periods": data.terms or 0,
                "repayment_start_date": data.start_date,
                "posting_date": data.start_date,
                "custom_app_id": app_id,
                "custom_loan_id": loan_id,
                "total_payment": data.total_amount or 0,
            })
            
            loan_doc.insert(ignore_permissions=True)
            
            # -----------------------------
            # SUBMIT LOAN (triggers repayment schedule creation - normal flow)
            # -----------------------------
            # loan_doc.submit()
            
            inserted.append({
                "app_id": app_id,
                "loan_id": loan_id,
                "loan_name": loan_doc.name,
                "status": loan_doc.status
            })
            
        except Exception as e:
            errors.append({
                "app_id": grp.app_id,
                "loan_id": grp.loan_id,
                "error": str(e)
            })
    
    frappe.db.commit()
    
    return {
        "inserted_count": len(inserted),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors
    }


@frappe.whitelist(allow_guest=True)
def update_loan_repayment_schedule_from_data_adding():
    """
    Update Loan Repayment Schedule from Data adding records.
    
    For each unique combination of (app_id, loan_id) in Data adding:
    - Find the corresponding Loan with matching custom_app_id and custom_loan_id
    - Find the Loan Repayment Schedule for that loan
    - Update the repayment_schedule table with data from Data adding
      matching by payment_date (emi_date)
    
    This function forcefully updates the repayment schedule dates and amounts
    regardless of the loan status (Sanctioned, Disbursed, etc.)
    
    Field mapping from Data adding to Repayment Schedule:
    - emi_date -> payment_date
    - principal_amount -> principal_amount
    - int_amount -> interest_amount
    - total_amount -> total_payment
    - bal_amount -> balance_loan_amount
    """
    updated = []
    skipped = []
    errors = []
    
    # -----------------------------
    # GET DISTINCT app_id + loan_id FROM Data adding
    # -----------------------------
    groups = frappe.db.sql("""
        SELECT 
            app_id, 
            loan_id
        FROM `tabData adding`
        WHERE app_id IS NOT NULL 
          AND loan_id IS NOT NULL
          AND emi_date IS NOT NULL
        GROUP BY app_id, loan_id
    """, as_dict=True)
    print("groups for schedule update ....", len(groups))
    
    for grp in groups:
        try:
            app_id = grp.app_id
            loan_id = grp.loan_id
            
            # -----------------------------
            # FIND LOAN
            # -----------------------------
            loan_name = frappe.db.get_value("Loan", {
                "custom_app_id": app_id,
                "custom_loan_id": loan_id,
                "docstatus": 0
            }, "name")
            print("loan_name ....",loan_name)
            
            if not loan_name:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": "Loan not found"
                })
                continue
            
            # -----------------------------
            # FIND LOAN REPAYMENT SCHEDULE
            # -----------------------------
            repayment_schedule_name = frappe.db.get_value("Loan Repayment Schedule", {
                "loan": loan_name
            }, "name")
            
            if not repayment_schedule_name:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "loan_name": loan_name,
                    "reason": "Loan Repayment Schedule not found"
                })
                continue
            
            # -----------------------------
            # GET REPAYMENT SCHEDULE DOC
            # -----------------------------
            rs_doc = frappe.get_doc("Loan Repayment Schedule", repayment_schedule_name)
            
            # -----------------------------
            # GET DATA ADDING RECORDS FOR THIS LOAN
            # -----------------------------
            data_records = frappe.db.sql("""
                SELECT 
                    emi_date,
                    principal_amount,
                    int_amount,
                    total_amount,
                    bal_amount
                FROM `tabData adding`
                WHERE app_id = %s
                  AND loan_id = %s
                  AND emi_date IS NOT NULL
                ORDER BY emi_date
            """, (app_id, loan_id), as_dict=True)
            
            if not data_records:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": "No Data adding records with emi_date"
                })
                continue
            
            # -----------------------------
            # UPDATE REPAYMENT SCHEDULE (FORCE UPDATE)
            # Even if loan is Sanctioned, we update the schedule
            # -----------------------------
            updated_count = 0
            for data_row in data_records:
                emi_date = data_row.emi_date
                
                # Find matching row in repayment_schedule table
                for row in rs_doc.repayment_schedule:
                    if row.payment_date == emi_date:
                        # Force update all fields
                        row.principal_amount = data_row.principal_amount or 0
                        row.interest_amount = data_row.int_amount or 0
                        row.total_payment = data_row.total_amount or 0
                        row.balance_loan_amount = data_row.bal_amount or 0
                        updated_count += 1
                        updated.append({
                            "app_id": app_id,
                            "loan_id": loan_id,
                            "payment_date": emi_date,
                            "principal": data_row.principal_amount,
                            "interest": data_row.int_amount,
                            "total": data_row.total_amount,
                            "balance": data_row.bal_amount
                        })
                        break
            
            if updated_count > 0:
                # Save without validation to allow force update
                rs_doc.flags.ignore_validate = True
                rs_doc.save(ignore_permissions=True)
            
        except Exception as e:
            errors.append({
                "app_id": grp.app_id,
                "loan_id": grp.loan_id,
                "error": str(e)
            })
    
    frappe.db.commit()
    
    return {
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "updated_records": updated,
        "skipped_records": skipped,
        "errors": errors
    }



@frappe.whitelist(allow_guest=True)
def update_loan_repayment_schedule_from_data_adding_test():

    updated = []
    skipped = []
    errors = []

    groups = frappe.db.sql("""
        SELECT app_id, loan_id
        FROM `tabData adding`
        WHERE app_id IS NOT NULL
          AND loan_id IS NOT NULL
          AND emi_date IS NOT NULL
        GROUP BY app_id, loan_id
    """, as_dict=True)

    for grp in groups:
        try:
            app_id = grp.app_id
            loan_id = grp.loan_id

            # -----------------------------
            # FIND LOAN
            # -----------------------------
            loan_name = frappe.db.get_value(
                "Loan",
                {"custom_app_id": app_id, "custom_loan_id": loan_id,},
                "name"
            )
            if not loan_name:
                skipped.append({"app_id": app_id, "loan_id": loan_id, "reason": "Loan not found"})
                continue

            # -----------------------------
            # FIND REPAYMENT SCHEDULE
            # -----------------------------
            rs_name = frappe.db.get_value(
                "Loan Repayment Schedule",
                {"loan": loan_name},
                "name"
            )
            if not rs_name:
                skipped.append({"app_id": app_id, "loan_id": loan_id, "reason": "Schedule not found"})
                continue

            rs_doc = frappe.get_doc("Loan Repayment Schedule", rs_name)

            # -----------------------------
            # FETCH DATA ADDING (ORDERED)
            # -----------------------------
            data_rows = frappe.db.sql("""
                SELECT
                    emi_date,
                    principal_amount,
                    int_amount,
                    total_amount,
                    bal_amount
                FROM `tabData adding`
                WHERE app_id = %s AND loan_id = %s
                ORDER BY emi_date ASC
            """, (app_id, loan_id), as_dict=True)

            if not data_rows:
                continue

            # -----------------------------
            # FETCH SCHEDULE ROWS (ORDERED BY IDX)
            # -----------------------------
            schedule_rows = rs_doc.repayment_schedule

            limit = min(len(data_rows), len(schedule_rows))

            # -----------------------------
            # UPDATE USING POSITION (IDX)
            # -----------------------------
            for i in range(limit):
                data = data_rows[i]
                row = schedule_rows[i]

                # 🔥 FORCE DB UPDATE
                row.db_set("payment_date", data.emi_date, update_modified=False)
                row.db_set("principal_amount", data.principal_amount or 0, update_modified=False)
                row.db_set("interest_amount", data.int_amount or 0, update_modified=False)
                row.db_set("total_payment", data.total_amount or 0, update_modified=False)
                row.db_set("balance_loan_amount", data.bal_amount or 0, update_modified=False)

                updated.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "idx": row.idx,
                    "payment_date": data.emi_date
                })

        except Exception as e:
            errors.append({
                "app_id": grp.app_id,
                "loan_id": grp.loan_id,
                "error": str(e)
            })

    frappe.db.commit()

    return {
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "updated_records": updated,
        "errors": errors
    }

@frappe.whitelist(allow_guest=True)
def create_loan_disbursement_from_loans():
    """
    Create Loan Disbursement directly from Loan documents.
    
    For each unique combination of (app_id, loan_id) in Data adding:
    - Find the corresponding Loan with matching custom_app_id and custom_loan_id
    - Check if Loan Disbursement already exists
    - If not exists: create a new Loan Disbursement document directly from Loan
    
    Uses the loan's repayment_start_date as disbursement date.
    """
    inserted = []
    skipped = []
    errors = []
    
    # -----------------------------
    # GET DISTINCT app_id + loan_id FROM Data adding
    # -----------------------------
    groups = frappe.db.sql("""
        SELECT 
            app_id, 
            loan_id
        FROM `tabData adding`
        WHERE app_id IS NOT NULL 
          AND loan_id IS NOT NULL
        GROUP BY app_id, loan_id
    """, as_dict=True)
    print("groups for disbursement ....", len(groups))
    
    for grp in groups:
        try:
            app_id = grp.app_id
            loan_id = grp.loan_id
            
            # -----------------------------
            # FIND LOAN
            # -----------------------------
            loan_name = frappe.db.get_value("Loan", {
                "custom_app_id": app_id,
                "custom_loan_id": loan_id
            }, "name")
            
            if not loan_name:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": "Loan not found"
                })
                continue
            
            # -----------------------------
            # CHECK IF DISBURSEMENT ALREADY EXISTS
            # -----------------------------
            existing_disbursement = frappe.db.exists("Loan Disbursement", {
                "against_loan": loan_name
            })
            
            if existing_disbursement:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": f"Disbursement {existing_disbursement} already exists"
                })
                continue
            
            # -----------------------------
            # GET LOAN DETAILS
            # -----------------------------
            loan_doc = frappe.get_doc("Loan", loan_name)
            
            # -----------------------------
            # GET DISBURSEMENT DATE (use repayment_start_date from loan)
            # -----------------------------
            disbursement_date = loan_doc.posting_date
            
            if not disbursement_date:
                skipped.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": "No date found for disbursement"
                })
                continue
            
            # -----------------------------
            # GET APPLICANT (MEMBER)
            # -----------------------------
            applicant = loan_doc.applicant
            
            if not applicant:
                errors.append({
                    "app_id": app_id,
                    "loan_id": loan_id,
                    "reason": "Applicant not found"
                })
                continue
            
            # -----------------------------
            # CALCULATE DISBURSED AMOUNT
            # Disbursed amount = loan amount (can be modified for processing fees)
            # -----------------------------
            disbursed_amount = loan_doc.loan_amount or 0
            
            # -----------------------------
            # CREATE LOAN DISBURSEMENT DOCUMENT DIRECTLY FROM LOAN
            # -----------------------------
            disbursement_doc = frappe.get_doc({
                "doctype": "Loan Disbursement",
                "against_loan": loan_name,
                "disbursement_date": disbursement_date,
                "disbursed_amount": disbursed_amount,
                "company": "Tejraj Micro Association",
                "applicant_type": "Member",
                "applicant": applicant,
                "sanctioned_loan_amount": loan_doc.loan_amount or 0,
                "current_disbursed_amount": disbursed_amount,
                "monthly_repayment_amount": loan_doc.monthly_repayment_amount or 0,
                "loan_product": loan_doc.loan_product if loan_doc.loan_product else None,
                "posting_date": disbursement_date,
            })
            
            disbursement_doc.save(ignore_permissions=True)
            
            inserted.append({
                "app_id": app_id,
                "loan_id": loan_id,
                "loan_name": loan_name,
                "disbursement_name": disbursement_doc.name
            })
            
        except Exception as e:
            errors.append({
                "app_id": grp.app_id,
                "loan_id": grp.loan_id,
                "error": str(e)
            })
    
    frappe.db.commit()
    
    return {
        "inserted_count": len(inserted),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors
    }






