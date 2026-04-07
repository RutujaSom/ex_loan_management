# Copyright (c) 2026, Rutuja Somvanshi and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):

    # -----------------------------
    # Columns (MANDATORY)
    # -----------------------------
    columns = [
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Data",
            "width": 220
        },
        {
            "label": "Expected Collection",
            "fieldname": "expected",
            "fieldtype": "Currency",
            "width": 160
        },
        {
            "label": "Actual Collection",
            "fieldname": "collected",
            "fieldtype": "Currency",
            "width": 160
        },
    ]

    data = []
    labels = []
    expected_values = []
    collected_values = []
    
    
    # -----------------------------
    # Get Employees
    # -----------------------------
    employees = frappe.get_all(
        "Employee",
        fields=["name", "employee_name"]
    )
    print("employees ...",employees)

    for emp in employees:

        # -----------------------------
        # Loan Groups assigned to Employee
        # -----------------------------
        loan_groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": emp.name},
            pluck="loan_group"
        )
        print("loan_groups ...",loan_groups)

        if not loan_groups:
            continue

        # -----------------------------
        # Loan Applications for Loan Groups
        # -----------------------------
        loan_apps = frappe.get_all(
            "Loan Application",
            filters={"custom_group": ["in", loan_groups]},
            pluck="name"
        )
        print("loan_apps ...",loan_apps)

        if not loan_apps:
            continue

        # -----------------------------
        # Loans created from Loan Applications
        # -----------------------------
        loans = frappe.get_all(
            "Loan",
            filters={"loan_application": ["in", loan_apps]},
            pluck="name"
        )
        print("loans ...",loans)

        if not loans:
            continue

        # -----------------------------
        # Expected Amount (Repayment Schedule child table)
        # -----------------------------
        expt_conditions = ""
        expt_values = {}
        print("from_date ..",filters.get("from_date"),'to_date ....',filters.get("to_date"))

        if filters.get("from_date"):
            expt_conditions += " AND rs.payment_date >= %(from_date)s"
            expt_values["from_date"] = filters.get("from_date")

        if filters.get("to_date"):
            expt_conditions += " AND rs.payment_date <= %(to_date)s"
            expt_values["to_date"] = filters.get("to_date")

        expected_amount = frappe.db.sql("""
            SELECT COALESCE(SUM(rs.total_payment), 0)
            FROM `tabLoan Repayment Schedule` lrs
            INNER JOIN `tabRepayment Schedule` rs
                ON rs.parent = lrs.name
            WHERE lrs.loan IN %(loans)s
            {conditions}
        """.format(conditions=expt_conditions),
        {
            "loans": tuple(loans),
            **expt_values
        },
        as_list=True)[0][0]


        col_conditions = ""
        col_values = {}

        if filters.get("from_date"):
            col_conditions += " AND value_date >= %(from_date)s"
            col_values["from_date"] = filters.get("from_date")

        if filters.get("to_date"):
            col_conditions += " AND value_date <= %(to_date)s"
            col_values["to_date"] = filters.get("to_date")
        # -----------------------------
        # Collected Amount (Loan Repayment)
        # -----------------------------
        # collected_amount = frappe.db.sql("""
        #     SELECT COALESCE(SUM(amount_paid), 0)
        #     FROM `tabLoan Repayment`
        #     WHERE against_loan IN %(loans)s
        #       AND workflow_state = 'Approved'
        # """, {"loans": tuple(loans)}, as_list=True)[0][0]

        collected_amount = frappe.db.sql("""
            SELECT COALESCE(SUM(amount_paid), 0)
            FROM `tabLoan Repayment`
            WHERE against_loan IN %(loans)s
            AND workflow_state = 'Approved'
            {conditions}
        """.format(conditions=col_conditions),
        {
            "loans": tuple(loans),
            **col_values
        },
        as_list=True)[0][0]

        print("collected_amount ...", collected_amount)

        # -----------------------------
        # Table Data
        # -----------------------------
        data.append({
            "employee": emp.employee_name,
            "expected": expected_amount,
            "collected": collected_amount
        })

        # -----------------------------
        # Chart Data
        # -----------------------------
        labels.append(emp.employee_name)
        expected_values.append(expected_amount)
        collected_values.append(collected_amount)

    # -----------------------------
    # Bar Chart (Double Bar)
    # -----------------------------
    chart = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Expected Collection",
                    "values": expected_values
                },
                {
                    "name": "Actual Collection",
                    "values": collected_values
                }
            ]
        },
        "type": "bar"
    }

    # -----------------------------
    # REQUIRED RETURN
    # -----------------------------
    return columns, data, chart