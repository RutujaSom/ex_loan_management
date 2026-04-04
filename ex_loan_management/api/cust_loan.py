



import frappe
import pandas as pd
from datetime import datetime
from ex_loan_management.api.utils import get_paginated_data

import frappe
from frappe.model.naming import make_autoname

# def set_loan_id(doc, method):
#     """
#     Auto-generate Loan ID like GL001, GL002...
#     Works with Naming Series = By field name → custom_loan_id
#     """

#     if doc.custom_loan_id:
#         return  # already set (import / manual)

#     # Generate next sequence
#     doc.custom_loan_id = make_autoname("GL.###")


def set_loan_id(doc, method=None):
    if doc.custom_loan_id:
        return

    last_number = frappe.db.sql(
        """
        SELECT
            MAX(CAST(SUBSTRING(name, 3) AS UNSIGNED))
        FROM `tabLoan`
        WHERE name LIKE 'GL%'
        """,
        as_list=True,
    )[0][0]

    next_number = int(last_number) + 1 if last_number else 1

    doc.custom_loan_id = f"GL{next_number:04d}"
    doc.name = f"GL{next_number:04d}"


@frappe.whitelist()
def bulk_import_loans(file_url):
    # Get File doc
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()   # full path to file in sites/private/files/ or sites/{sitename}/public/files/

    # Read file with pandas
    if file_url.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    print('file_path ...', file_path, 'df ....', df)

    success = []
    errors = []

    for idx, row in df.iterrows():
        # print('row ....', row)
        try:
            if str(row.get('TYPE OF BORROWER')).strip() == "CO-BORROWER":
                continue
            # print('row.get("ROI")...',row.get("ROI"), type(row.get("ROI")))
            # --- Get Loan Product ---
            loan_product = frappe.get_value("Loan Product", {"rate_of_interest": row.get("ROI")}, "name")
            if not loan_product:
                raise Exception(f"Loan Product '{row.get('ROI')}' not found")

            # --- Get Applicant ---
            print('row.get("MEMBER NO") ...',row.get("MEMBER NO"))
            applicant = frappe.get_value("Member", {"member_id": row.get("MEMBER NO")}, "name")
            if not applicant:
                raise Exception(f"Applicant '{row.get('MEMBER NO')}' not found")

            loan_application = frappe.get_value("Loan Application", {"custom_loan_id":row.get("LOAN ID")}, "name")
            if not loan_application:
                raise Exception(f"Applicant '{row.get('MEMBER NO')}' not found")
			
			
            loan_doc = frappe.get_doc("Loan Application", loan_application)

            # print("Loan Amount from Loan Application:", loan_amount)

            print('loan_application ...',loan_application,'  ...loan_amount ...',loan_doc.loan_amount,'row.get("LOAN ID") ...',row.get("LOAN ID"))
            # --- Parse Date ---
            loan_date = row.get("LOAN SANCTION DATE/ trasancation date")
            if isinstance(loan_date, str):
                for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
                    try:
                        loan_date = datetime.strptime(loan_date, fmt).date()
                        break
                    except:
                        continue

            print('loan_product .....', loan_product, row.get("ROI"),'row.get("ROI")')

            # Prepare data
            loan_data = {
                "doctype": "Loan",
                "applicant_type": "Member",
                "applicant": loan_doc.applicant,
                "company": "Tejraj Micro Association",
                "loan_product": loan_doc.loan_product,
                "loan_amount": loan_doc.loan_amount,
                "is_secured_loan": 0,
                "is_term_loan": 1,
                "repayment_method": "Repay Over Number of Periods",
                "repayment_periods": row.get("TERM IN MONTHS"),
                "repayment_amount": row.get("EMI"),
                "rate_of_interest": row.get("ROI"),
                "posting_date": loan_date,
				"custom_loan_id": row.get("LOAN ID"),
				"loan_application":loan_application
            }
            print('loan_data ...',loan_data)

            loan_doc = frappe.get_doc(loan_data)
            loan_doc.insert()
            loan_doc.submit()
            print('loan_doc.name ...',loan_doc.name)
            print()

            success.append(loan_doc.name)

        except Exception as e:
            print('e .....',e)
            # return f'{e}'
            frappe.log_error(f"Bulk Loan Import Error (Row {idx+1}): {str(e)}")
            errors.append(f"Row {idx+1}: {str(e)}")

    return f"success_count: {len(success)}, error_count: {len(errors)}"






update_fields = [
    "name",
    "custom_loan_id",
	"applicant_type",
	"applicant",
	"applicant_name",
	"loan_application",
	"company",
	"posting_date",
	"status",
	"loan_product",
	"loan_amount",
	"loan_partner",
	"loan_category",
	"repayment_schedule_type",
	"cancellation_date",
	"settlement_date",
	"rate_of_interest",
	"penalty_charges_rate",
	"disbursement_date",
	"disbursed_amount",
	"closure_date",
	"maximum_loan_amount",
	"is_secured_loan",
	"is_term_loan",
	"repayment_start_date",
	"repayment_method",
	"repayment_periods",
	"monthly_repayment_amount",
	"moratorium_type",
	"moratorium_tenure",
	"repayment_frequency",
	"treatment_of_interest",
	"repayment_days",
	"limit_applicable_start",
	"maximum_limit_amount",
	"limit_applicable_end",
	"utilized_limit_amount",
	"available_limit_amount",
	"days_past_due",
	"loan_restructure_count",
	"watch_period_end_date",
	"tenure_post_restructure",
	"cost_center",
	"disbursement_account",
	"payment_account",
	"loan_account",
	"interest_income_account",
	"penalty_income_account",
	"total_payment",
	"total_interest_payable",
	"total_principal_paid",
	"total_amount_paid",
]

"""
	Get Loan List (with optional pagination, search & sorting)
"""
@frappe.whitelist(allow_guest=False)
def loan_list(page=1, page_size=10, search=None, sort_by="name", sort_order="asc", is_pagination=False, loan_group=None, **kwargs):
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

    if "Agent" in frappe.get_roles(user):
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

    return get_paginated_data(
        doctype="Loan",
        fields=update_fields,
        filters=filters,   # ✅ Now includes applicant filter if loan_group provided
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["applicant_name"],
        is_pagination=is_pagination,
        base_url=base_url,
        extra_params=extra_params,
        # link_fields={"applicant": "member_name"},  # 👈 you can also expand Member fields if needed
    )

