import frappe
from frappe.utils import add_days, getdate
from ex_loan_management.api.utils import get_paginated_data


def get_previous_working_day(payment_date, holiday_list):
    """
    Move payment_date backward until it is not a holiday
    """

    payment_date = getdate(payment_date)

    while frappe.db.exists(
        "Holiday",
        {
            "parent": holiday_list,
            "holiday_date": payment_date
        }
    ):
        payment_date = add_days(payment_date, -1)

    return payment_date

def adjust_repayment_schedule_for_holidays(doc, method):
    """
    Adjust EMI dates if they fall on holidays
    """

    if not doc.company or not doc.repayment_schedule:
        return
    
    repayment_date = getdate(doc.repayment_start_date)

    company_data = frappe.db.get_value(
        "Company",
        doc.company,
        ["custom_skip_holiday_on_loan_schedule", "default_holiday_list"],
        as_dict=True
    )

    if (
        not company_data
        or not company_data.custom_skip_holiday_on_loan_schedule
        or not company_data.default_holiday_list
    ):
        return
    
    is_holiday = frappe.db.exists(
        "Holiday",
        {
            "parent": company_data.default_holiday_list,
            "holiday_date": repayment_date
        }
    )

    if is_holiday:
        frappe.throw(
            (
                "The selected Repayment Start Date {0} is a holiday as per Holiday List {1}. "
                "Please choose another date."
            ).format(
                frappe.bold(repayment_date),
                frappe.bold(company_data.default_holiday_list)
            )
        )

    for row in doc.repayment_schedule:
        if not row.payment_date:
            continue

        row.payment_date = get_previous_working_day(
            row.payment_date,
            company_data.default_holiday_list
        )




import frappe
import pandas as pd
from frappe.utils import getdate

@frappe.whitelist()
def bulk_update_repayment_dates(file_url):
    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = file_doc.get_full_path()
        df = pd.read_excel(file_path)

        success = []
        errors = []

        grouped = df.groupby("LOAN ID")

        for loan_id, loan_rows in grouped:
            loan_id = str(loan_id).strip()

            try:
                loan = frappe.get_doc("Loan", {"loan_id": loan_id})

                schedules = frappe.get_all(
                    "Loan Repayment Schedule",
                    filters={"loan": loan.name},
                    pluck="name"
                )

                if not schedules:
                    errors.append(f"Loan {loan_id}: No repayment schedule found")
                    continue

                doc = frappe.get_doc("Loan Repayment Schedule", schedules[0])

                # Cancel if submitted
                if doc.docstatus == 1:
                    doc.cancel()

                # IMPORTANT: stop ERPNext recalculation
                doc.flags.ignore_validate = True
                doc.flags.ignore_mandatory = True
                doc.flags.ignore_links = True

                # Update EMI rows
                # print("loan_rows ....",loan_rows)
                for _, row in loan_rows.iterrows():
                    emi_no = int(row.get("EMI NO"))
                    new_date = safe_getdate(row.get("EMI DATE"))
                    print("new_date ....",new_date)

                    if not new_date:
                        errors.append(f"Loan {loan_id}: Invalid EMI DATE for EMI {emi_no}")
                        continue

                    principal_amount = float(row.get("Principle") or 0)
                    interest_amount = float(row.get("Interest") or 0)
                    total_payment = float(row.get("EMI(ACTUAL AS PER SHEET)") or 0)
                    balanace = float(row.get("ClosingBALANCE") or 0)
                    days = float(row.get("days") or 0)

                    matched = False
                    # print("doc.repayment_schedule ....",doc.repayment_schedule)
                    for emi in doc.repayment_schedule:
                        # print("emi.idx == ...",emi.idx,' emi_no ...' ,emi_no)
                        if emi.idx == emi_no:
                            print(loan_id, "in if ....",new_date, ' principal_amount....',principal_amount,'total_payment ...',total_payment)
                            # ⚠️ USE CORRECT FIELD NAME
                            emi.payment_date = new_date
                            emi.principal_amount = principal_amount
                            emi.interest_amount = interest_amount
                            emi.total_payment = total_payment
                            emi.balance_loan_amount = balanace
                            emi.number_of_days = days
                            matched = True
                            break

                    if not matched:
                        errors.append(f"Loan {loan_id}: EMI {emi_no} not found")
                
                # Sort EMIs
                doc.repayment_schedule.sort(key=lambda x: x.idx)

                # Update parent dates
                doc.repayment_start_date = doc.repayment_schedule[0].payment_date
                print("doc.repayment_schedule[-1].repayment_date ....",doc.repayment_schedule[-1].payment_date)
                doc.maturity_date = doc.repayment_schedule[-1].payment_date

                # Save & Submit
                doc.save(ignore_permissions=True)
                # doc.submit()

                success.append(f"Loan {loan_id}: Updated successfully")

            except Exception as e:
                errors.append(f"Loan {loan_id}: {str(e)}")

        frappe.db.commit()

        return {
            "success_count": len(success),
            "error_count": len(errors),
            "errors": errors
        }

    except Exception:
        print("e .....",e)
        frappe.log_error(frappe.get_traceback(), "Bulk Update Repayment Dates Error")
        return "Unexpected error occurred"

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
	
update_fields = [
    "name",
    "loan",
	"loan_disbursement",
	"loan_amount",
	"current_principal_amount",
	"rate_of_interest",
	"company",
	"posting_date",
	"repayment_frequency",
	"repayment_start_date",
	"maturity_date",
	"total_installments_paid",
	"total_installments_raised",
	"total_installments_overdue",
	"loan_product",
	"repayment_method",
	"repayment_periods",
	"repayment_schedule_type",
	"repayment_date_on",
	"disbursed_amount",
	"monthly_repayment_amount",
	"partner_monthly_repayment_amount",
	"loan_restructure",
	"restructure_type",
	"broken_period_interest",
	"status",
	"amended_from",
	"moratorium_type",
	"moratorium_tenure",
	"treatment_of_interest",
	"moratorium_end_date",
	"adjusted_interest",
	"broken_period_interest_days",
]

"""
	Get Loan Repayment Schedule List (with optional pagination, search & sorting)
"""
@frappe.whitelist()
def loan_payment_schedule_list(page=1, page_size=10, search=None, sort_by="loan", sort_order="asc", is_pagination=False,**kwargs):
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
    base_url = frappe.request.host_url.rstrip("/") + frappe.request.path
    print("base_url .....",base_url)
    print("sort_by ..",sort_by,'sort_order ....',sort_order)
    parent_data =  get_paginated_data(
        doctype="Loan Repayment Schedule",
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
    )

    if isinstance(parent_data, dict):
        parent_results = parent_data.get("results", [])
    else:
        parent_results = parent_data

    parent_names = [doc["name"] for doc in parent_results]


    # Fetch all child rows for these parents at once
    all_child_rows = frappe.get_all(
        "Repayment Schedule",
        filters={"parent": ["in", parent_names], "parenttype": "Loan Repayment Schedule"},
        fields=[
            "parent",
            "payment_date",
            "number_of_days",
            "principal_amount",
            "interest_amount",
            "total_payment",
            "balance_loan_amount",
            "demand_generated",
            "idx"
        ],
        order_by="parent, idx asc"
    )
    
    # Group child rows by parent
    children_map = {}
    for row in all_child_rows:
        children_map.setdefault(row["parent"], []).append(row)
    
    # Attach child rows to parents
    for doc in parent_results:
        doc["repayment_schedule"] = children_map.get(doc["name"], [])


    return parent_data