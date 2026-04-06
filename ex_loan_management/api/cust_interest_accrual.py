import frappe
from frappe.utils import add_days, cint, date_diff, flt, get_datetime, getdate, nowdate
from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
    get_interest_amount,
    # get_no_of_days_for_interest_accural,
)
from lending.loan_management.doctype.loan_repayment.loan_repayment import (
    get_pending_principal_amount,
)

def after_submit(doc, method=None):
    print("in after .........")
    """
    Fallback accrual for TERM LOANS when posting_date
    is not part of repayment schedule.
    """

    if not doc.loan:
        return

    loan = frappe.get_doc("Loan", doc.loan)

    # ✅ Only for TERM loans
    if not loan.is_term_loan:
        return

    # ✅ Prevent duplicate accrual
    if frappe.db.exists(
        "Loan Interest Accrual",
        {
            "loan": loan.name,
            "posting_date": doc.posting_date,
            "docstatus": 1,
        },
    ):
        return

    # ✅ Run fallback accrual
    accrue_term_loan_till_date(
        loan,
        doc.posting_date,
        doc.name,
        doc.accrual_type,
    )


def get_no_of_days_for_interest_accural(loan, posting_date):
    print("in data ......")
    last_interest_accrual_date = get_last_accrual_date(loan.name, posting_date)
    print("last_interest_accrual_date ....",last_interest_accrual_date)
    no_of_days = date_diff(posting_date or nowdate(), last_interest_accrual_date) + 1
    print("no_of_days ...",no_of_days)

    return no_of_days



def get_last_accrual_date(loan, posting_date):
	last_posting_date = frappe.db.sql(
		""" SELECT MAX(posting_date) from `tabLoan Interest Accrual`
		WHERE loan = %s and docstatus = 1""",
		(loan),
	)

	if last_posting_date[0][0]:
		last_interest_accrual_date = last_posting_date[0][0]
		# interest for last interest accrual date is already booked, so add 1 day
		last_disbursement_date = get_last_disbursement_date(loan, posting_date)

		if last_disbursement_date and getdate(last_disbursement_date) > add_days(
			getdate(last_interest_accrual_date), 1
		):
			last_interest_accrual_date = last_disbursement_date

		return add_days(last_interest_accrual_date, 1)
	else:
         return get_interest_start_date(loan)
		# return frappe.db.get_value("Loan", loan, "disbursement_date")


def get_last_disbursement_date(loan, posting_date):
	last_disbursement_date = frappe.db.get_value(
		"Loan Disbursement",
		{"docstatus": 1, "against_loan": loan, "posting_date": ("<", posting_date)},
		"MAX(posting_date)",
	)

	return last_disbursement_date


def get_interest_start_date(loan):
    values = frappe.db.get_value(
        "Loan",
        loan,
        ["custom_last_repayment_date", "disbursement_date"],
        as_dict=True
    )

    if (
        values
        and values.custom_last_repayment_date
        and getdate(values.custom_last_repayment_date) < getdate(values.disbursement_date)
    ):
        return values.custom_last_repayment_date
    print("values.disbursement_date ....",values.disbursement_date)
    return values.disbursement_date



def accrue_term_loan_till_date(loan, posting_date, process_name, accrual_type):
    print('in accurla llll.....')
    no_of_days = get_no_of_days_for_interest_accural(
        loan, posting_date
    )
    print(no_of_days ,'........ no_of_days')

    if no_of_days <= 0:
        return

    pending_principal = get_pending_principal_amount(loan)
    print("pending_principal .....",pending_principal)

    interest = get_interest_amount(
        no_of_days,
        pending_principal,
        loan.rate_of_interest,
        loan.company,
        posting_date,
    )
    print("interest .....",interest)

    if interest <= 0:
        return
    

    accrual = frappe.new_doc("Loan Interest Accrual")
    accrual.loan = loan.name
    accrual.applicant_type = loan.applicant_type
    accrual.applicant = loan.applicant
    accrual.interest_income_account = loan.interest_income_account
    accrual.loan_account = loan.loan_account
    # accrual.pending_principal_amount = pending_principal
    accrual.payable_principal_amount = pending_principal
    accrual.interest_amount = interest
    accrual.posting_date = posting_date
    accrual.due_date = posting_date
    accrual.accrual_type = accrual_type
    accrual.process_loan_interest_accrual = process_name
    accrual.paid_interest_amount = 0
    accrual.paid_principal_amount = 0

    accrual.save(ignore_permissions=True)
    accrual.submit()

    # args = frappe._dict(
	# 		{
	# 			"loan": loan.name,
	# 			"applicant_type": loan.applicant_type,
	# 			"applicant": loan.applicant,
	# 			"interest_income_account": loan.interest_income_account,
	# 			"loan_account": loan.loan_account,
	# 			"interest_amount": loan.interest_amount,
	# 			"payable_principal": loan.principal_amount,
	# 			"process_loan_interest": process_loan_interest,
	# 			"repayment_schedule_name": loan.payment_entry,
	# 			"posting_date": posting_date,
	# 			"accrual_type": accrual_type,
	# 			"due_date": loan.payment_date,
	# 		}
	# 	)

	# 	make_loan_interest_accrual_entry(args)




import frappe
from frappe.utils import getdate
from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
    calculate_accrual_amount_for_demand_loans,
)
from lending.loan_management.doctype.loan_repayment.loan_repayment import (
    calculate_amounts,
)

def on_int_submit(doc, method=None):
    """
    Create interest accrual for LOAN CLOSURE DATE
    using core ERPNext logic.
    """

    if not doc.loan:
        return

    loan = frappe.get_doc("Loan", doc.loan)

    posting_date = doc.posting_date

    # 🔴 STOP if core already created accrual
    if frappe.db.exists(
        "Loan Interest Accrual",
        {
            "loan": loan.name,
            "posting_date": posting_date,
            # "process_loan_interest_accrual": doc.name,
            "docstatus": 1,
        }
    ):
        return
    
    accrual_type = "Repayment"
    

    # ✅ Demand loans
    if not loan.is_term_loan:
        calculate_accrual_amount_for_demand_loans(
            loan=loan,
            posting_date=posting_date,
            process_loan_interest=doc.name,
            accrual_type=accrual_type,
        )
        return

    # ✅ Term loans (no schedule match case)
    pending_amounts = calculate_amounts(
        loan.name,
        posting_date,
        payment_type="Loan Closure",
    )

    if pending_amounts.get("interest_amount") <= 0:
        return

    args = frappe._dict({
        "loan": loan.name,
        "applicant_type": loan.applicant_type,
        "applicant": loan.applicant,
        "interest_income_account": loan.interest_income_account,
        "loan_account": loan.loan_account,
        "pending_principal_amount": pending_amounts["pending_principal_amount"],
        "interest_amount": pending_amounts["interest_amount"],
        "total_pending_interest_amount": pending_amounts["interest_amount"],
        "penalty_amount": pending_amounts.get("penalty_amount", 0),
        "process_loan_interest": doc.name,
        "posting_date": posting_date,
        "due_date": posting_date,
        "accrual_type": accrual_type,
        "payable_principal": pending_amounts.get("payable_principal_amount"),
    })

    # 🔥 THIS IS THE KEY
    from lending.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import (
        make_loan_interest_accrual_entry,
    )

    make_loan_interest_accrual_entry(args)




def process_loan_interest_accrual(posting_date=None, loan_product=None, loan=None):

	if not term_loan_accrual_pending(posting_date or nowdate(), loan=loan):
		return

	loan_process = frappe.new_doc("Process Loan Interest Accrual")
	loan_process.posting_date = posting_date or nowdate()
	loan_process.loan_product = loan_product
	loan_process.process_type = "Term Loans"
	loan_process.loan = loan

	loan_process.submit()

	return loan_process.name


def term_loan_accrual_pending(date, loan=None):
	filters = {"payment_date": ("<=", date), "is_accrued": 0}

	if loan:
		loan_repayment_schedule = frappe.db.get_value(
			"Loan Repayment Schedule", {"loan": loan, "status": "Active"}
		)
		filters.update({"parent": loan_repayment_schedule})

	pending_accrual = frappe.db.get_value("Repayment Schedule", filters)

	return pending_accrual


@frappe.whitelist()
def process_selected_emis(emis):
	"""
	Process loan interest accrual for selected EMIs from the frontend.
	
	Args:
	    emis: List of dictionaries containing loan, payment_date, and amount
	
	Returns:
	    Dictionary with success status and processed count
	"""
	import json
	
	if isinstance(emis, str):
		emis = json.loads(emis)
	
	if not emis or not isinstance(emis, list):
		frappe.throw("No EMIs provided for processing")
	
	successful = 0
	failed = 0
	errors = []
	
	for emi in emis:
		try:
			loan = emi.get("loan")
			payment_date = emi.get("payment_date")
			
			if not loan or not payment_date:
				failed += 1
				errors.append(f"Missing loan or payment_date for EMI: {emi}")
				continue
			
			# Process accrual for this loan
			interest_accrual = process_loan_interest_accrual(
				posting_date=payment_date,
				loan=loan
			)
			if interest_accrual:
				successful += 1
			
		except Exception as e:
			failed += 1
			errors.append(f"Error processing loan {emi.get('loan')}: {str(e)}")
			frappe.log_error(
				title="Loan Accrual Processing Error",
				message=f"Failed to process EMI: {json.dumps(emi)}\nError: {str(e)}"
			)
	
	# Prepare result message
	message = f"Successfully processed {successful} EMI(s)"
	if failed > 0:
		message += f". Failed: {failed}"
	
	if errors:
		frappe.log_error(
			title="Loan Accrual Processing Summary",
			message=f"Processed: {successful}, Failed: {failed}\nErrors:\n" + "\n".join(errors)
		)
	
	return {
		"message": message,
		"successful": successful,
		"failed": failed
	}
