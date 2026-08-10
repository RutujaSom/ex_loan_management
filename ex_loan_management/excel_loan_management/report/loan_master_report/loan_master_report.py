# Loan Master Report - loan_master_report.py
# Place this inside: apps/<your_app>/<your_app>/excel_loan_management/report/loan_master_report/loan_master_report.py
#
# Produces TWO rows per loan (where a co-borrower exists): one row with
# "Type of Borrower" = BORROWER (applicant's details), one row with
# "Type of Borrower" = CO-BORROWER (co-borrower's details). Loan-level
# fields (amount, tenure, dates, charges, paid/pending) repeat on both rows.
#
# ASSUMED FIELDNAMES - adjust if yours differ:
#   Member:      member_name, mobile_no, address, aadhar, pancard, dob,
#                completed_age, entry_age, occupation, gender, city,
#                state, country, pincode
#   Loan Group:  group_head (Link -> Member), group_name
#
# CHARGE CODES - adjust the lists below to match your actual "Item" codes
# used as the "charge" link in Loan Disbursement Charge rows.
PROCESSING_FEE_CHARGES = ["PROS-FEES", "Prossesing Fees", "CGST", "SGST"]
INSURANCE_CHARGES = ["INSURANCE", "INS-FEES", "INSURANCE-FEE", "Insurance"]

import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Type of Borrower", "fieldname": "borrower_type", "fieldtype": "Data", "width": 130},
		{"label": "Loan ID", "fieldname": "loan_id", "fieldtype": "Link", "options": "Loan", "width": 130},
		{"label": "Loan Group", "fieldname": "loan_group", "fieldtype": "Link", "options": "Loan Group", "width": 120},
		{"label": "Loan Group Name", "fieldname": "group_name", "fieldtype": "Data", "width": 220},
		{"label": "Group Head Code", "fieldname": "group_head", "fieldtype": "Data", "width": 180},
		{"label": "Group Head Name", "fieldname": "group_head_name", "fieldtype": "Data", "width": 180},
		{"label": "Group Head Mobile", "fieldname": "group_head_mobile", "fieldtype": "Data", "width": 130},
		{"label": "Group Head Address", "fieldname": "group_head_address", "fieldtype": "Data", "width": 200},

		{"label": "Member ID", "fieldname": "member_id", "fieldtype": "Link", "options": "Member", "width": 130},
		{"label": "Member Name", "fieldname": "member_name", "fieldtype": "Data", "width": 200},
		{"label": "Mobile No", "fieldname": "mobile_no", "fieldtype": "Data", "width": 120},
		{"label": "Gender", "fieldname": "gender", "fieldtype": "Data", "width": 90},
		{"label": "Date of Birth", "fieldname": "dob", "fieldtype": "Date", "width": 110},
		{"label": "Entry Age", "fieldname": "entry_age", "fieldtype": "Int", "width": 90},
		{"label": "Completed Age", "fieldname": "completed_age", "fieldtype": "Int", "width": 110},
		{"label": "Occupation", "fieldname": "occupation", "fieldtype": "Data", "width": 130},
		{"label": "Aadhar Number", "fieldname": "aadhar", "fieldtype": "Data", "width": 140},
		{"label": "PAN Number", "fieldname": "pancard", "fieldtype": "Data", "width": 120},
		{"label": "Voter Id", "fieldname": "voter_id", "fieldtype": "Data", "width": 120},
		{"label": "Address", "fieldname": "address", "fieldtype": "Data", "width": 250},
		{"label": "City", "fieldname": "city", "fieldtype": "Data", "width": 120},
		{"label": "State", "fieldname": "state", "fieldtype": "Data", "width": 120},
		{"label": "Country", "fieldname": "country", "fieldtype": "Data", "width": 120},
		{"label": "Pincode", "fieldname": "pincode", "fieldtype": "Data", "width": 100},

		{"label": "Bank Name", "fieldname": "bank_name", "fieldtype": "Data", "width": 150},
		{"label": "Account Number", "fieldname": "account_number", "fieldtype": "Data", "width": 150},
		{"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 130},
		{"label": "Bank Address", "fieldname": "bank_address", "fieldtype": "Data", "width": 200},
		{"label": "Account Holder Name", "fieldname": "holder_name", "fieldtype": "Data", "width": 180},
		{"label": "IFSC Code", "fieldname": "ifsc_code", "fieldtype": "Data", "width": 120},
		{"label": "Account Type", "fieldname": "account_type", "fieldtype": "Data", "width": 120},

		{"label": "Nominee Code", "fieldname": "nominee_code", "fieldtype": "Link", "options": "Member", "width": 130},
		{"label": "Nominee Name", "fieldname": "nominee_name", "fieldtype": "Data", "width": 180},
		{"label": "Nominee Relation", "fieldname": "nominee_relation", "fieldtype": "Data", "width": 130},

		{"label": "Loan Amount", "fieldname": "loan_amount", "fieldtype": "Currency", "width": 130},
		{"label": "Tenure", "fieldname": "tenure", "fieldtype": "Int", "width": 90},
		{"label": "Monthly Repayment Amount", "fieldname": "monthly_repayment_amount", "fieldtype": "Currency", "width": 150},
		{"label": "Sanction Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": "Disbursement Date", "fieldname": "disbursement_date", "fieldtype": "Date", "width": 130},
		{"label": "Loan Application", "fieldname": "loan_application", "fieldtype": "Link", "options": "Loan Application", "width": 150},

		{"label": "Processing Fee (incl. GST)", "fieldname": "processing_fee", "fieldtype": "Currency", "width": 160},
		{"label": "Insurance Amount", "fieldname": "insurance_amount", "fieldtype": "Currency", "width": 130},
		{"label": "Other Charges", "fieldname": "other_charges", "fieldtype": "Currency", "width": 130},

		{"label": "Paid Amount", "fieldname": "total_amount_paid", "fieldtype": "Currency", "width": 150},
		{"label": "Pending Amount", "fieldname": "pending_amount", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	conditions = ""
	values = {}

	if filters.get("company"):
		conditions += " AND l.company = %(company)s"
		values["company"] = filters.get("company")

	if filters.get("status"):
		conditions += " AND l.status = %(status)s"
		values["status"] = filters.get("status")

	if filters.get("loan_group"):
		conditions += " AND COALESCE(l.custom_loan_group, m_applicant.group) = %(loan_group)s"
		values["loan_group"] = filters.get("loan_group")

	if filters.get("applicant"):
		conditions += " AND la.applicant = %(applicant)s"
		values["applicant"] = filters.get("applicant")

	if filters.get("posting_date"):
		conditions += " AND l.posting_date = %(posting_date)s"
		values["posting_date"] = filters.get("posting_date")

	processing_fee_charges = tuple(PROCESSING_FEE_CHARGES) or ("",)
	insurance_charges = tuple(INSURANCE_CHARGES) or ("",)
	values["processing_fee_charges"] = processing_fee_charges
	values["insurance_charges"] = insurance_charges

	loans = frappe.db.sql(
		f"""
		SELECT
			l.name AS loan_id,
			l.loan_amount AS loan_amount,
			l.repayment_periods AS tenure,
			l.monthly_repayment_amount AS monthly_repayment_amount,
			l.posting_date AS posting_date,
			l.disbursement_date AS disbursement_date,
			l.loan_application AS loan_application,
			l.total_principal_paid AS total_principal_paid,
			l.total_amount_paid As total_amount_paid,
			(l.total_payment - IFNULL(l.total_amount_paid, 0)) AS pending_amount,

			COALESCE(l.custom_loan_group, m_applicant.group) AS loan_group,
			lg.group_name AS group_name,
			lg.group_head AS group_head,
			m_group_head.member_name AS group_head_name,
			m_group_head.mobile_no AS group_head_mobile,
			m_group_head.address AS group_head_address,

			l.applicant AS applicant,
			m_applicant.member_name AS applicant_name,
			m_applicant.mobile_no AS applicant_mobile_no,
			m_applicant.address AS applicant_address,
			m_applicant.aadhar AS applicant_aadhar_number,
			m_applicant.pancard AS applicant_pan_number,
			m_applicant.voter_id AS applicant_voter_id,
			m_applicant.dob AS applicant_date_of_birth,
			m_applicant.completed_age AS applicant_completed_age,
			m_applicant.entry_age AS applicant_entry_age,
			m_applicant.occupation AS applicant_occupation,
			m_applicant.gender AS applicant_gender,
			m_applicant.city AS applicant_city,
			m_applicant.state AS applicant_state,
			m_applicant.country AS applicant_country,
			m_applicant.pincode AS applicant_pincode,
			m_applicant.bank_name AS applicant_bank_name,
			m_applicant.account_number AS applicant_account_number,
			m_applicant.branch AS applicant_branch,
			m_applicant.bank_address AS applicant_bank_address,
			m_applicant.holder_name AS applicant_holder_name,
			m_applicant.ifsc_code AS applicant_ifsc_code,
			m_applicant.account_type AS applicant_account_type,

			la.custom_co_borrower AS co_borrower,
			m_co_borrower.member_name AS co_borrower_name,
			m_co_borrower.mobile_no AS co_borrower_mobile_no,
			m_co_borrower.address AS co_borrower_address,
			m_co_borrower.aadhar AS co_borrower_aadhar_number,
			m_co_borrower.pancard AS co_borrower_pan_number,
			m_co_borrower.voter_id AS co_borrower_voter_id,
			m_co_borrower.dob AS co_borrower_date_of_birth,
			m_co_borrower.completed_age AS co_borrower_completed_age,
			m_co_borrower.entry_age AS co_borrower_entry_age,
			m_co_borrower.occupation AS co_borrower_occupation,
			m_co_borrower.gender AS co_borrower_gender,
			m_co_borrower.city AS co_borrower_city,
			m_co_borrower.state AS co_borrower_state,
			m_co_borrower.country AS co_borrower_country,
			m_co_borrower.pincode AS co_borrower_pincode,
			m_co_borrower.bank_name AS co_borrower_bank_name,
			m_co_borrower.account_number AS co_borrower_account_number,
			m_co_borrower.branch AS co_borrower_branch,
			m_co_borrower.bank_address AS co_borrower_bank_address,
			m_co_borrower.holder_name AS co_borrower_holder_name,
			m_co_borrower.ifsc_code AS co_borrower_ifsc_code,
			m_co_borrower.account_type AS co_borrower_account_type,

			la.custom_nominee AS nominee_code,
			m_nominee.member_name AS nominee_name,
			la.custom_nominee_relation AS nominee_relation,

			-- First submitted Loan Disbursement against this loan
			-- (mirrors the Jinja template's frappe.get_list(..., limit=1))
			(
				SELECT ld.name FROM `tabLoan Disbursement` ld
				WHERE ld.against_loan = l.name AND ld.docstatus = 1
				ORDER BY ld.creation ASC LIMIT 1
			) AS first_disbursement,

			(
				SELECT SUM(ldc.amount)
				FROM `tabLoan Disbursement Charge` ldc
				WHERE ldc.parent = (
					SELECT ld.name FROM `tabLoan Disbursement` ld
					WHERE ld.against_loan = l.name AND ld.docstatus = 1
					ORDER BY ld.creation ASC LIMIT 1
				)
				AND ldc.charge IN %(processing_fee_charges)s
			) AS processing_fee,

			(
				SELECT SUM(ldc.amount)
				FROM `tabLoan Disbursement Charge` ldc
				WHERE ldc.parent = (
					SELECT ld.name FROM `tabLoan Disbursement` ld
					WHERE ld.against_loan = l.name AND ld.docstatus = 1
					ORDER BY ld.creation ASC LIMIT 1
				)
				AND ldc.charge IN %(insurance_charges)s
			) AS insurance_amount,

			(
				SELECT SUM(ldc.amount)
				FROM `tabLoan Disbursement Charge` ldc
				WHERE ldc.parent = (
					SELECT ld.name FROM `tabLoan Disbursement` ld
					WHERE ld.against_loan = l.name AND ld.docstatus = 1
					ORDER BY ld.creation ASC LIMIT 1
				)
				AND ldc.charge NOT IN %(processing_fee_charges)s
				AND ldc.charge NOT IN %(insurance_charges)s
			) AS other_charges

		FROM `tabLoan` l

		LEFT JOIN `tabLoan Application` la
			ON la.name = l.loan_application

		-- Resolve the applicant's Member row whether or not a Loan
		-- Application exists (la.applicant if present, else l.applicant).
		LEFT JOIN `tabMember` m_applicant
			ON m_applicant.name = COALESCE(la.applicant, l.applicant)

		LEFT JOIN `tabMember` m_co_borrower
			ON m_co_borrower.name = la.custom_co_borrower

		LEFT JOIN `tabMember` m_nominee
			ON m_nominee.name = la.custom_nominee

		LEFT JOIN `tabLoan Group` lg
			ON lg.name = COALESCE(l.custom_loan_group, m_applicant.group)

		LEFT JOIN `tabMember` m_group_head
			ON m_group_head.name = lg.group_head

		WHERE l.docstatus < 2
		{conditions}
		ORDER BY l.posting_date DESC
		""",
		values,
		as_dict=1,
	)

	return build_rows(loans)


def normalize_state(state):
	"""MH or blank/None should display as the full state name."""
	if not state or str(state).strip().upper() == "MH":
		return "Maharashtra"
	return state


def build_rows(loans):
	"""Turn one row-per-loan into two rows-per-loan (borrower + co-borrower)."""
	rows = []

	loan_level_fields = [
		"loan_id", "loan_amount", "tenure", "monthly_repayment_amount",
		"posting_date", "disbursement_date", "loan_application",
		"total_principal_paid","total_amount_paid", "pending_amount",
		"loan_group", "group_name", "group_head", "group_head_name",
		"group_head_mobile", "group_head_address",
		"processing_fee", "insurance_amount", "other_charges",
	]

	for loan in loans:
		base = {f: (loan.get(f) or 0 if f in (
			"processing_fee", "insurance_amount", "other_charges"
		) else loan.get(f)) for f in loan_level_fields}
		base["total_upfront_charges"] = (
			(base.get("processing_fee") or 0)
			+ (base.get("insurance_amount") or 0)
			+ (base.get("other_charges") or 0)
		)

		# Borrower row
		rows.append({
			**base,
			"borrower_type": "BORROWER",
			"member_id": loan.get("applicant"),
			"member_name": loan.get("applicant_name"),
			"mobile_no": loan.get("applicant_mobile_no"),
			"address": loan.get("applicant_address"),
			"aadhar": loan.get("applicant_aadhar_number"),
			"pancard": loan.get("applicant_pan_number"),
			"voter_id": loan.get("applicant_voter_id"),
			"dob": loan.get("applicant_date_of_birth"),
			"completed_age": loan.get("applicant_completed_age"),
			"entry_age": loan.get("applicant_entry_age"),
			"occupation": loan.get("applicant_occupation"),
			"gender": loan.get("applicant_gender"),
			"city": loan.get("applicant_city"),
			"state": normalize_state(loan.get("applicant_state")),
			"country": loan.get("applicant_country"),
			"pincode": loan.get("applicant_pincode"),
			"nominee_code": loan.get("nominee_code"),
			"nominee_name": loan.get("nominee_name"),
			"nominee_relation": loan.get("nominee_relation"),
			"bank_name": loan.get("applicant_bank_name"),
			"account_number": loan.get("applicant_account_number"),
			"branch": loan.get("applicant_branch"),
			"bank_address": loan.get("applicant_bank_address"),
			"holder_name": loan.get("applicant_holder_name"),
			"ifsc_code": loan.get("applicant_ifsc_code"),
			"account_type": loan.get("applicant_account_type"),
		})

		# Co-borrower row (only if one exists on this loan)
		if loan.get("co_borrower"):
			rows.append({
				**base,
				"borrower_type": "CO-BORROWER",
				"member_id": loan.get("co_borrower"),
				"member_name": loan.get("co_borrower_name"),
				"mobile_no": loan.get("co_borrower_mobile_no"),
				"address": loan.get("co_borrower_address"),
				"aadhar": loan.get("co_borrower_aadhar_number"),
				"pancard": loan.get("co_borrower_pan_number"),
				"voter_id":loan.get("co_borrower_voter_id"),
				"dob": loan.get("co_borrower_date_of_birth"),
				"completed_age": loan.get("co_borrower_completed_age"),
				"entry_age": loan.get("co_borrower_entry_age"),
				"occupation": loan.get("co_borrower_occupation"),
				"gender": loan.get("co_borrower_gender"),
				"city": loan.get("co_borrower_city"),
				"state": normalize_state(loan.get("co_borrower_state")),
				"country": loan.get("co_borrower_country"),
				"pincode": loan.get("co_borrower_pincode"),
				"bank_name": loan.get("co_borrower_bank_name"),
				"account_number": loan.get("co_borrower_account_number"),
				"branch": loan.get("co_borrower_branch"),
				"bank_address": loan.get("co_borrower_bank_address"),
				"holder_name": loan.get("co_borrower_holder_name"),
				"ifsc_code": loan.get("co_borrower_ifsc_code"),
				"account_type": loan.get("co_borrower_account_type"),
			})

	return rows