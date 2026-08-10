// Copyright (c) 2026, Rutuja Somvanshi and contributors
// For license information, please see license.txt

// frappe.query_reports["Loan Master Report"] = {
// 	"filters": [

// 	]
// };

frappe.query_reports["Loan Master Report"] = {
	"filters": [
		{
			fieldname: "loan_group",
			label: __("Loan Group"),
			fieldtype: "Link",
			options: "Loan Group",
		},
		{
			fieldname: "applicant",
			label: __("Borrower"),
			fieldtype: "Link",
			options: "Member",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				"",
				"Sanctioned",
				"Partially Disbursed",
				"Disbursed",
				"Loan Closure Requested",
				"Closed",
			],
		},
		{
			fieldname: "posting_date",
			label: __("Sanction Date"),
			fieldtype: "Date",
		},
		// {
		// 	fieldname: "to_date",
		// 	label: __("Sanction Date (To)"),
		// 	fieldtype: "Date",
		// },
	],
};