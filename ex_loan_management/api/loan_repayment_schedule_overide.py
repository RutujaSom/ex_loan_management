


# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, date_diff, flt, get_last_day, getdate
from lending.loan_management.doctype.loan_repayment_schedule.loan_repayment_schedule import (
    LoanRepaymentSchedule as CoreLoanRepaymentSchedule
)

class LoanRepaymentSchedule(CoreLoanRepaymentSchedule):
	def validate(self):
		print("in cust ...........")
		self.validate_repayment_method()
		self.set_missing_fields()
		self.make_repayment_schedule()
		self.set_repayment_period()

	def set_missing_fields(self):
		if self.repayment_method == "Repay Over Number of Periods":
			self.monthly_repayment_amount = get_monthly_repayment_amount(
				self.loan_amount, self.rate_of_interest, self.repayment_periods
			)

	def set_repayment_period(self):
		if self.repayment_method == "Repay Fixed Amount per Period":
			repayment_periods = len(self.repayment_schedule)

			self.repayment_periods = repayment_periods

	def make_repayment_schedule(self):
		if not self.repayment_start_date:
			frappe.throw(_("Repayment Start Date is mandatory for term loans"))

		schedule_type_details = frappe.db.get_value(
			"Loan Product", self.loan_product, ["repayment_schedule_type", "repayment_date_on"], as_dict=1
		)

		self.repayment_schedule = []
		payment_date = self.repayment_start_date
		balance_amount = self.loan_amount
		broken_period_interest_days = date_diff(add_months(payment_date, -1), self.posting_date)
		carry_forward_interest = self.adjusted_interest
		
		is_first_emi = True # This is custom logic from Rutuja on 22-APR-2026
		previous_payment_date = None # This is custom logic from Rutuja on 22-APR-2026

		while balance_amount > 0:
			interest_amount, principal_amount, balance_amount, total_payment, days = self.get_amounts(
				payment_date,
				balance_amount,
				schedule_type_details.repayment_schedule_type,
				schedule_type_details.repayment_date_on,
				broken_period_interest_days,
				carry_forward_interest,
				is_first_emi,
				previous_payment_date
			)

			if schedule_type_details.repayment_schedule_type == "Pro-rated calendar months":
				next_payment_date = get_last_day(payment_date)
				if schedule_type_details.repayment_date_on == "Start of the next month":
					next_payment_date = add_days(next_payment_date, 1)

				payment_date = next_payment_date

			self.add_repayment_schedule_row(
				payment_date, principal_amount, interest_amount, total_payment, balance_amount, days
			)

			if (
				self.repayment_method == "Repay Over Number of Periods"
				and len(self.get("repayment_schedule")) >= self.repayment_periods
			):
				self.get("repayment_schedule")[-1].principal_amount += balance_amount
				self.get("repayment_schedule")[-1].balance_loan_amount = 0
				self.get("repayment_schedule")[-1].total_payment = (
					self.get("repayment_schedule")[-1].interest_amount
					+ self.get("repayment_schedule")[-1].principal_amount
				)
				balance_amount = 0

			if (
				schedule_type_details.repayment_schedule_type
				in ["Monthly as per repayment start date", "Monthly as per cycle date"]
				or schedule_type_details.repayment_date_on == "End of the current month"
			):
				is_first_emi = False
				previous_payment_date = payment_date
				
				next_payment_date = add_single_month(payment_date)
				payment_date = next_payment_date

			bmi_days = 0
			carry_forward_interest = 0

	def validate_repayment_method(self):
		if self.repayment_method == "Repay Over Number of Periods" and not self.repayment_periods:
			frappe.throw(_("Please enter Repayment Periods"))

		if self.repayment_method == "Repay Fixed Amount per Period":
			if not self.monthly_repayment_amount:
				frappe.throw(_("Please enter repayment Amount"))
			if self.monthly_repayment_amount > self.loan_amount:
				frappe.throw(_("Monthly Repayment Amount cannot be greater than Loan Amount"))

	def get_amounts(
		self,
		payment_date,
		balance_amount,
		schedule_type,
		repayment_date_on,
		additional_days,
		carry_forward_interest=0,
		is_first_emi=False, # This is custom logic from Rutuja on 22-APR-2026
		previous_payment_date=None # This is custom logic from Rutuja on 22-APR-2026
	):
		if schedule_type == "Monthly as per repayment start date":
			days = 1   # This is core logic
			months = 12  # This is core logic
			
            # This is custom logic from Rutuja on 22-APR-2026
            # ✅ FIRST EMI → posting_date → payment_date
			if is_first_emi:
				interest_amount, principal_amount, balance_amount, total_payment, days = self.get_first_emi_amounts(
                    payment_date,
                    balance_amount,
                    carry_forward_interest,
                )
				return interest_amount, principal_amount, balance_amount, total_payment, days
				
            # ✅ NEXT EMIs → previous_payment_date → payment_date
			else:
				payment_date = adjust_repayment_date_for_holidays(self.company, payment_date)
				days = date_diff(payment_date, previous_payment_date)
				months = 365   # This is core logic
				
            
		else:
			expected_payment_date = get_last_day(payment_date)
			if repayment_date_on == "Start of the next month":
				expected_payment_date = add_days(expected_payment_date, 1)

			if schedule_type == "Monthly as per cycle date":
				days = date_diff(payment_date, add_months(payment_date, -1))
				if additional_days < 0:
					days = date_diff(self.repayment_start_date, self.posting_date)
					additional_days = 0

				months = 365
				if additional_days:
					days += additional_days
					additional_days = 0
			elif expected_payment_date == payment_date:
				# using 30 days for calculating interest for all full months
				days = 30
				months = 365
			else:
				days = date_diff(get_last_day(payment_date), payment_date)
				months = 365
        
        
		interest_amount = flt(balance_amount * flt(self.rate_of_interest) * days / (months * 100))
		print('interest_amount......',interest_amount, '....',balance_amount,'days ...',days, '...months',months)
		principal_amount = self.monthly_repayment_amount - flt(interest_amount)
		balance_amount = flt(balance_amount + interest_amount - self.monthly_repayment_amount)
		if balance_amount < 0:
			principal_amount += balance_amount
			balance_amount = 0.0

		if carry_forward_interest:
			interest_amount += carry_forward_interest

		total_payment = principal_amount + interest_amount

		return interest_amount, principal_amount, balance_amount, total_payment, days
	


	def get_first_emi_amounts(
		self,
		payment_date,
		balance_amount,
		carry_forward_interest,
	):
		days = 1   # This is core logic
		months = 12  # This is core logic
        
        # This is custom logic from Rutuja on 22-APR-2026
		payment_date = adjust_repayment_date_for_holidays(self.company, payment_date)
		custom_months = 365
		# ✅ FIRST EMI → posting_date → payment_date
		custom_days = date_diff(payment_date, self.posting_date)           
		
        # Calculate interest as per core logic
		interest_amount = flt(balance_amount * flt(self.rate_of_interest) * days / (months * 100))
		
        # Calculate interest as per custom logic
		day_wise_interest_amount = flt(balance_amount * flt(self.rate_of_interest) * custom_days / (custom_months * 100))
		
		principal_amount = self.monthly_repayment_amount - flt(interest_amount)
		balance_amount = flt(balance_amount + interest_amount - self.monthly_repayment_amount)
		if balance_amount < 0:
			principal_amount += balance_amount
			balance_amount = 0.0

		if carry_forward_interest:
			interest_amount += carry_forward_interest

		total_payment = principal_amount + day_wise_interest_amount # Get total from custom interest

		return day_wise_interest_amount, principal_amount, balance_amount, total_payment, days

	def add_repayment_schedule_row(
		self, payment_date, principal_amount, interest_amount, total_payment, balance_loan_amount, days
	):
		self.append(
			"repayment_schedule",
			{
				"number_of_days": days,
				"payment_date": payment_date,
				"principal_amount": principal_amount,
				"interest_amount": interest_amount,
				"total_payment": total_payment,
				"balance_loan_amount": balance_loan_amount,
			},
		)


def add_single_month(date):
	if getdate(date) == get_last_day(date):
		return get_last_day(add_months(date, 1))
	else:
		return add_months(date, 1)


def get_monthly_repayment_amount(loan_amount, rate_of_interest, repayment_periods):
	if rate_of_interest:
		monthly_interest_rate = flt(rate_of_interest) / (12 * 100)
		monthly_repayment_amount = math.ceil(
			(loan_amount * monthly_interest_rate * (1 + monthly_interest_rate) ** repayment_periods)
			/ ((1 + monthly_interest_rate) ** repayment_periods - 1)
		)
	else:
		monthly_repayment_amount = math.ceil(flt(loan_amount) / repayment_periods)
	return monthly_repayment_amount




def adjust_repayment_date_for_holidays(company, payment_date):
    print("in cust valid .......")
    """
    Adjust EMI dates if they fall on holidays
    """

    if not company:
        return
    

    company_data = frappe.db.get_value(
        "Company",
        company,
        ["custom_skip_holiday_on_loan_schedule", "default_holiday_list"],
        as_dict=True
    )

    if (
        not company_data
        or not company_data.custom_skip_holiday_on_loan_schedule
        or not company_data.default_holiday_list
    ):
        return
    
    payment_date = getdate(payment_date)

    while frappe.db.exists(
        "Holiday",
        {
            "parent": company_data.default_holiday_list,
            "holiday_date": payment_date
        }
    ):
        payment_date = add_days(payment_date, -1)
    print("payment_date ....",payment_date)
    return payment_date