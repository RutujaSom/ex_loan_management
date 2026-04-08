
import frappe
import pandas as pd
from datetime import datetime
from ex_loan_management.api.utils import get_paginated_data


@frappe.whitelist()
def bulk_import_loan_disbursement(file_url):
    print('bulk_import_loan_disbursement ....')
    # Get File doc
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    # Read file with pandas
    if file_url.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    success = []
    errors = []

    for idx, row in df.iterrows():
        try:
            print('loan .....',row.get("LOAN ID"))
            # --- Find Loan Application ---
            loan_name = frappe.get_doc("Loan", {"loan_id": row.get("LOAN ID")})
            if not loan_name:
                # raise Exception(f"Loan '{row.get('AGAINST LOAN')}' not found")
                print(f"Loan '{row.get('AGAINST LOAN')}' not found")
                continue
            print('loan_name .....',loan_name)

            # --- Parse Dates ---
            disbursement_date = row.get("LOAN SANCTION DATE/ trasancation date")
            if isinstance(disbursement_date, str):
                for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        disbursement_date = datetime.strptime(disbursement_date, fmt).date()
                        break
                    except:
                        continue

            # --- Get Applicant ---
            print('row.get("MEMBER NO") ...',row.get("MEMBER NO"), row.get("LOAN ACCOUNT"))
            applicant = frappe.get_value("Member", {"member_id": row.get("MEMBER NO")}, "name")
            if not applicant:
                raise Exception(f"Applicant '{row.get('MEMBER NO')}' not found")
			
            pros_fees = row.get("PROS FEES ")
            dis_amount = loan_name.loan_amount - pros_fees
            print("dis_amount ....",dis_amount)


            # --- Prepare Data ---
            disbursement_data = {
                "doctype": "Loan Disbursement",
                "against_loan": loan_name.name,
                "disbursement_date": disbursement_date,
                "disbursed_amount": dis_amount,
                "mode_of_payment": row.get("MODE OF PAYMENT"),
                "disbursement_account": row.get("DISBURSEMENT ACCOUNT"),
                "loan_account": row.get("LOAN ACCOUNT"),
                "company": "Tejraj Micro Association",
                "reference_number": row.get("REFERENCE NO"),
                "reference_date": row.get("REFERENCE DATE"),
				"applicant_type":"MEMBER",
				"applicant":applicant,
				"sanctioned_loan_amount":loan_name.loan_amount,
				"current_disbursed_amount":dis_amount,
				"monthly_repayment_amount":loan_name.monthly_repayment_amount,

            }

            # --- Create & Submit Loan Disbursement ---
            disb_doc = frappe.get_doc(disbursement_data)
            disb_doc.insert()
            # disb_doc.submit()
			# 🔒 Force update amounts AFTER insert
            frappe.db.set_value(
				"Loan Disbursement",
				disb_doc.name,
				{
					"disbursed_amount": dis_amount,
					"current_disbursed_amount": dis_amount
				},
				update_modified=False
			)

            # frappe.db.commit()
            print('disb_doc ...',disb_doc)

            success.append(disb_doc.name)

        except Exception as e:
            # return f"e ....{e}"
            frappe.log_error(f"Bulk Loan Disbursement Error (Row {idx+1}): {str(e)}")
            errors.append(f"Row {idx+1}: {str(e)}")

    return f"success_count: {len(success)}, error_count: {len(errors)}"







@frappe.whitelist()
def import_and_submit_disbursement(file_url):
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    # Read file with pandas
    if file_url.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
	# ✅ Keep only EMI No = 1 records for each Loan ID
    df = df[df["EMI NO"] == 1]
    print('df ...',df)

    success, errors = [], []

    for _, row in df.iterrows():
        try:
            loan_id = str(row.get("LOAN ID")).strip()
            repay_start = row.get("EMI DATE")

            print('loan .....',row.get("LOAN ID"), 'repay_start ....',repay_start)
			# --- Find Loan Application ---
            loan_name = frappe.get_doc("Loan", {"loan_id": loan_id})
            if not loan_name:
                # raise Exception(f"Loan '{row.get('AGAINST LOAN')}' not found")
                print(f"Loan '{row.get('AGAINST LOAN')}' not found")
                continue
            print('loan_name .....',loan_name)


            if not loan_id or not repay_start:
                raise Exception("Loan ID and Repayment Start Date are required")
            print('before ...')
            # --- Find matching Loan Disbursement (Draft only) ---
            disb_name = frappe.db.get_value(
                "Loan Disbursement",
                {
                    # "loan": loan_id,
					"against_loan": loan_name.name,
                    # "repayment_start_date": repay_start,
                    "docstatus": 0
                },
                "name"
            )
            print('disb_name ...',disb_name)

            if not disb_name:
                raise Exception(f"No Draft Loan Disbursement found for Loan {loan_id} with Repayment Start {repay_start}")

            # --- Load and Submit ---
            disb_doc = frappe.get_doc("Loan Disbursement", disb_name)
            disb_doc.repayment_start_date = repay_start  # <-- update repayment date
            disb_doc.save()
            # disb_doc.submit()

            success.append({
                # "against_loan": loan_name.name,
                "repayment_start_date": repay_start,
                "disbursement": disb_name,
                "status": "Submitted"
            })

        except Exception as e:
            # return f"e ....,{e}"
            frappe.log_error(f"Bulk Loan Disbursement Error (Row: {str(e)}")
            errors.append({"row": dict(row), "error": str(e)})

    return f"success_count: {len(success)}, error_count: {len(errors)}"





update_fields = [
    "name",
    "against_loan",
	"sanctioned_loan_amount",
	"current_disbursed_amount",
	"posting_date",
	"applicant_type",
	"loan_product",
	"monthly_repayment_amount",
	"loan_partner",
	"company",
	"applicant",
	"repayment_schedule_type",
	"repayment_frequency",
	"repayment_method",
	"tenure",
	"repayment_start_date",
	"is_term_loan",
	"withhold_security_deposit",
	"disbursement_date",
	"clearance_date",
	"bpi_difference_date",
	"broken_period_interest_days",
	"disbursed_amount",
	"broken_period_interest",
	"bpi_amount_difference",
	"principal_amount_paid",
	"mode_of_payment",
	"disbursement_account",
	"refund_account",
	"loan_account",
	"bank_account",
	"cost_center",
	"reference_date",
	"days_past_due",
	"status",
    "docstatus",
	"reference_number",
	"amended_from",
]

"""
	Get Loan Disbursement List (with optional pagination, search & sorting)
"""
@frappe.whitelist(allow_guest=False)
def loan_disbursement_list(page=1, page_size=10, search=None, sort_by="name", sort_order="asc",loan_group=None, is_pagination=False,**kwargs):
    is_pagination = frappe.utils.sbool(is_pagination)  # convert "true"/"false"/1/0 into bool
    extra_params = {"search": search} if search else {}
    if "cmd" in kwargs:
        del kwargs["cmd"]

    # 🔹 Collect filters from kwargs (all query params except the defaults)
    filters = {}
    for k, v in kwargs.items():
        if v not in [None, ""]:   # skip empty params
            filters[k] = v

	# 🔹 Handle loan_group filter (from Member)
    user = frappe.session.user
    if "Agent" in frappe.get_roles(user) and not ("Account Manager" in frappe.get_roles(user) or "Loan Manager" in frappe.get_roles(user)):
        employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_id:
            return None  # No employee mapped

        # Fetch loan groups assigned to this employee
        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee_id},
            pluck="loan_group"
        )

        if not groups:
            return {
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            }

        # 🔹 If agent selects a group → filter only that group
        if loan_group:
            groups = [loan_group] if loan_group in groups else []

        # If no valid group remains → no records
        if not groups:
            return {
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            }

        # Fetch Members belonging to allowed groups
        member_ids = frappe.get_all(
            "Member",
            filters={"group": ["in", groups]},
            pluck="name"
        )

        if member_ids:
            filters["applicant"] = ["in", member_ids]
        else:
            return {
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            }

    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path
    parent_data =  get_paginated_data(
        doctype="Loan Disbursement",
        fields=update_fields,
        filters=filters,   # ✅ Now includes applicant filter if loan_group provided
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["name"],
        is_pagination=is_pagination,
        base_url=base_url,
        extra_params=extra_params,
		link_fields={"applicant": "member_name","against_loan": "custom_loan_id","against_loan": "loan_amount", "against_loan": "repayment_start_date",
               "against_loan": "total_principal_paid"},
        link_fields_test = {
            "applicant": ["member_name"],
            "against_loan": [
                "custom_loan_id",
                "loan_amount",
                "repayment_start_date",
                "total_principal_paid"
            ]
        },
		link_images_fields={"applicant": "member_image"},
		dynamic_search_fields = {"applicant":{"doctype": "Member", "field": "member_id"},}
    )

    return parent_data