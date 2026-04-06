import frappe
import pandas as pd
from datetime import datetime
from ex_loan_management.api.utils import get_paginated_data, api_error

def validate_loan_application(doc, method=None):
    if doc.custom_co_borrower:
        # Step 1: get all approved loan applications with same co_borrower
        applications = frappe.get_all(
            "Loan Application",
            filters={
                "custom_co_borrower": doc.custom_co_borrower,
                "status": "Approved"
            },
            fields=["name"]
        )
        if applications:
            application_names = [app.name for app in applications]

            # Step 2: get all Loans linked to these applications
            loans = frappe.get_all(
                "Loan",
                filters={
                    "loan_application": ["in", application_names],
                    "status": ["not in", ["Closed", "Loan Closure Requested", "Written Offs"]]
                },
                fields=["name", "status", "applicant", "loan_application"]
            )
            if len(loans)>0:
                frappe.throw("Selected co-borrower is already associated with active loan(s). Please select another co-borrower.")
               



def get_permission_query_conditions(user):

    doctype = frappe.form_dict.get("doctype")
    if not user or user == "Administrator":
        return None

    if "Agent" in frappe.get_roles(user):
        # Get employee ID linked to logged-in user
        employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_id:
            return None  # No employee mapped

        # Fetch groups assigned to this employee
        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee_id},
            pluck="loan_group"
        )
        if not groups:
            return "1=2"

        groups_str = "', '".join(groups)

        if frappe.form_dict.get("doctype") == "Collection In Hand":
			# Filter only records where employee matches logged-in user's employee
            return f"`tabCollection In Hand`.`employee` = '{employee_id}'"

        
        # For Loan Repayment Schedule → restrict indirectly via Loan → Member → Group
        if frappe.form_dict.get("doctype") == "Loan Repayment Schedule":
            return f"""
                loan IN (
                    SELECT name FROM `tabLoan`
                    WHERE applicant IN (
                        SELECT name FROM `tabMember`
                        WHERE `group` in ('{groups_str}')
                    )
                )
            """
        else:
            
            return f"""
                `tab{doctype}`.`applicant`  IN (
                    SELECT name FROM `tabMember`
                    WHERE `group` in ('{groups_str}')
                )
            """

    return None


def has_permission(doc, user):
    if not user or user == "Administrator":
        return True

    if "Agent" in frappe.get_roles(user):
        employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_id:
            return False
		
        if frappe.form_dict.get("doctype") == "Collection In Hand":
			# Filter only records where employee matches logged-in user's employee
            return doc.employee == employee_id

        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee_id},
            pluck="loan_group"
        )
        if not groups:
            return False
            

        # Case 2: Loan Repayment Schedule → check group via linked Loan
        if doc.doctype == "Loan Repayment Schedule":
            loan_member_group = frappe.db.get_value(
                "Member",
                {"name": frappe.db.get_value("Loan", doc.loan, "applicant")},
                "group"
            )
            return loan_member_group in groups
        else:
            return doc.group in groups

    return True




@frappe.whitelist()
def bulk_import_loan_applications(file_url):
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    if file_url.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path).fillna("")

    success, errors = [], []

    last_loan_application = None  # ⭐ store borrower loan application
    for idx, row in df.iterrows():
        try:
            type_of_borrower = row.get("TYPE OF BORROWER")
            loan_id = row.get("LOAN ID")
            print("loan id ....",loan_id,' .... amount... ', row.get("LOAN AMOUNT"))

            # ----------------------------------------
            # BORROWER → CREATE LOAN APPLICATION
            # ----------------------------------------
            if type_of_borrower != "CO-BORROWER":

                loan_product = frappe.get_value(
                    "Loan Product",
                    {"rate_of_interest": row.get("ROI")},
                    "name"
                )
                if not loan_product:
                    raise Exception(f"Loan Product '{row.get('ROI')}' not found")

                applicant = frappe.get_value(
                    "Member",
                    {"member_id": row.get("MEMBER NO")},
                    "name"
                )
                if not applicant:
                    raise Exception(f"Applicant '{row.get('MEMBER NO')}' not found")

                nominee_name = row.get("NOMINEE FULL NAME")
                nominee = frappe.get_value(
                    "Member",
                    {"member_name": nominee_name},
                    "name"
                )

                relation = str(row.get("RELATIONSHIP OF NOMINEE WITH BORROWER")).upper()

                loan_date = row.get("LOAN SANCTION DATE/ trasancation date")
                if isinstance(loan_date, str):
                    for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
                        try:
                            loan_date = datetime.strptime(loan_date, fmt).date()
                            break
                        except:
                            pass
                print("loan_date ....",loan_date)
                loan_doc = frappe.get_doc({
                    "doctype": "Loan Application",
                    "applicant_type": "Member",
                    "applicant": applicant,
                    "company": "Tejraj Micro Association",
                    "loan_product": loan_product,
                    "loan_amount": row.get("LOAN AMOUNT"),
                    "repayment_method": "Repay Over Number of Periods",
                    "repayment_periods": row.get("TERM IN MONTHS"),
                    "repayment_amount": row.get("EMI"),
                    "rate_of_interest": row.get("ROI"),
                    "posting_date": loan_date,
                    "status": "Approved",
                    "custom_nominee": nominee,
                    "custom_nominee_relation": relation,
                    "custom_loan_id": loan_id
                })

                loan_doc.insert()
                print("loan_doc ....",loan_doc)
                # loan_doc.db_set("workflow_state", "Approved", update_modified=False)

                last_loan_application = loan_doc.name  # ⭐ SAVE IT
                success.append(loan_doc.name)

            # ----------------------------------------
            # CO-BORROWER → ATTACH TO PREVIOUS LOAN
            # ----------------------------------------
            else:
                if not last_loan_application:
                    raise Exception("Co-Borrower found without Borrower")

                coborrower = frappe.get_value(
                    "Member",
                    {"member_id": row.get("MEMBER NO")},
                    "name"
                )
                print("Co Borrower name:", coborrower)
                if not coborrower:
                    raise Exception(f"Co-Borrower '{row.get('MEMBER NO')}' not found")

                loan_doc = frappe.get_doc("Loan Application", last_loan_application)

                loan_doc.custom_co_borrower = coborrower

                loan_doc.save(ignore_permissions=True)
                print("loan_doc.co_borrower .....",loan_doc.custom_co_borrower)

                # loan_doc.db_set("workflow_state", "Approved", update_modified=False)

        except Exception as e:
            print("e .....",e)
            frappe.log_error(
                f"Bulk Loan Import Error (Row {idx+1}): {str(e)}"
            )
            errors.append(f"Row {idx+1}: {str(e)}")

    return {
        "success_count": len(success),
        "error_count": len(errors),
        "errors": errors
    }










import frappe

@frappe.whitelist()
def create_loan_application():
    try:
        data = frappe.form_dict  # works for JSON body and form-data
        user_doc = frappe.get_doc("User", frappe.session.user)
        print('user_doc ......',user_doc)
        try:
            emp_details = frappe.get_doc("Employee", {"user_id": user_doc.name})
            company = emp_details.company
        except:
            company = ""

        # Step 1: Prepare Loan Application doc
        doc = frappe.get_doc({
            "doctype": "Loan Application",
            "applicant_type": data.get("applicant_type", "Member"),
            "applicant": data.get("applicant"),
            "applicant_name": data.get("applicant_name"),
            "custom_co_borrower": data.get("custom_co_borrower"),
            "custom_nominee":data.get("custom_nominee"),
            "custom_nominee_relation":data.get("custom_nominee_relation"),
            "company": company,
            "loan_product": data.get("loan_product"),
            "loan_amount": data.get("loan_amount"),
            "is_term_loan": data.get("is_term_loan") or 0,
            "rate_of_interest": data.get("rate_of_interest"),
            "description": data.get("description"),
            "repayment_method": "Repay Over Number of Periods",
            "repayment_periods": data.get("repayment_periods"),
            "status": "Open",
        })

        
        # Step 3: Insert Loan Application (runs validate() automatically)
        doc.insert(ignore_permissions=True)
        new_doc = apply_workflow(doc, "Submit for verification")
        frappe.db.commit()

        return {
            "status": "success",
            "status_code": 201,
            "msg": "Loan Application Created Successfully"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Loan Application API Error")
        # return {"status": "error", "message": str(e)}
        return api_error(e)




from frappe.model.workflow import apply_workflow

# @frappe.whitelist()
# def send_for_verification(application_name):
#     """
#     Trigger workflow action 'Submit for verification'
#     """
#     try:
#         # Load the Loan Application
#         doc = frappe.get_doc("Loan Application", application_name)

#         # Apply workflow transition
#         new_doc = apply_workflow(doc, "Submit for verification")

#         frappe.db.commit()

#         return {
#             "status": "success",
#             "status_code": 201,
#             "msg": f"Loan Application {application_name} submitted for verification",
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Send for Verification API Error")
#         # return {"status": "error", "message": str(e)}
#         return api_error(e)







update_fields = [
    "name",
    "applicant_type",
	"applicant",
	"applicant_name",
    "custom_co_borrower",
	"company",
	"posting_date",
	"status",
	"loan_product",
	"is_term_loan",
	"loan_amount",
	"rate_of_interest",
	"description",
	"maximum_loan_amount",
	"repayment_method",
	"total_payable_amount",
	"repayment_periods",
	"repayment_amount",
	"total_payable_interest",
	"amended_from",
    "workflow_state",
    "custom_nominee",
    "custom_nominee_relation",
    "is_secured_loan",
    "custom_loan_group",
]

"""
	Get Loan Application List (with optional pagination, search & sorting)
"""
@frappe.whitelist(allow_guest=True)
def loan_application_list(page=1, page_size=10, search=None, sort_by="name", sort_order="asc", is_pagination=False, loan_group=None, **kwargs):
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
        doctype="Loan Application",
        fields=update_fields,
        filters=filters,   # ✅ Now includes applicant filter if loan_group provided
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=int(page),
        page_size=int(page_size),
        search_fields=["applicant_name","applicant","name"],
        is_pagination=is_pagination,
        base_url=base_url,
        extra_params=extra_params, 
        link_fields={"custom_nominee": "member_name","custom_co_borrower": "member_name","applicant": "member_id"},  # 👈 you can also expand Member fields if needed
        link_images_fields={"applicant": "member_image"},  # 👈 you can also expand Member fields if needed
        dynamic_search_fields = {"applicant":{"doctype": "Member", "field": "member_id"},}
    )





@frappe.whitelist()
def get_loan_members_for_user(doctype, txt, searchfield, start, page_len, filters):
    user = frappe.session.user

    # Always prefer searching by member_name
    search_field = "member_name"
    print(f"Search on field: {search_field}, txt: {txt}")

    if user == "Administrator":
        return frappe.db.sql(f"""
            SELECT name, member_name
            FROM `tabMember`
            WHERE `{search_field}` LIKE %s
            ORDER BY member_name ASC
            LIMIT %s OFFSET %s
        """, (f"%{txt}%", page_len, start))

    if "Agent" in frappe.get_roles(user):
        employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_id:
            return []

        groups = frappe.get_all(
            "Loan Group Assignment",
            filters={"employee": employee_id},
            pluck="loan_group"
        )
        if not groups:
            return []

        # Use safe placeholders instead of string join
        placeholders = ", ".join(["%s"] * len(groups))
        query = f"""
            SELECT name, member_name
            FROM `tabMember`
            WHERE `group` IN ({placeholders})
            AND `{search_field}` LIKE %s
            ORDER BY member_name ASC
            LIMIT %s OFFSET %s
        """
        return frappe.db.sql(query, (*groups, f"%{txt}%", page_len, start))

    # Default for other users
    return frappe.db.sql(f"""
        SELECT name, member_name
        FROM `tabMember`
        WHERE `{search_field}` LIKE %s
        ORDER BY member_name ASC
        LIMIT %s OFFSET %s
    """, (f"%{txt}%", page_len, start))



@frappe.whitelist()
def loan_application_get(name):
    """
    Get Loan Application by name (primary key)
    Returns all fields same as in loan_application_list, including linked data and image URLs
    """
    if not name:
        frappe.throw("Loan Application name is required")

    # Fetch Loan Application with all fields from update_fields
    applications = frappe.get_all(
        "Loan Application",
        filters={"name": name},
        fields=update_fields
    )

    if not applications:
        return {}

    application = applications[0]

    # 🔹 Get linked data (same as list view)
    if application.get("custom_nominee"):
        nominee_name = frappe.get_value("Member", application["custom_nominee"], "member_name")
        application["custom_nominee_member_name"] = nominee_name or ""
    
    if application.get("custom_co_borrower"):
        co_borrower_name = frappe.get_value("Member", application["custom_co_borrower"], "member_name")
        application["custom_co_borrower_member_name"] = co_borrower_name or ""
    
    if application.get("applicant"):
        applicant_member_id = frappe.get_value("Member", application["applicant"], "member_id")
        application["applicant_member_id"] = applicant_member_id or ""

    # 🔹 Full URL for image fields (same as list view)
    host_url = frappe.request.host_url.rstrip("/")
    image_fields = ["member_image"]  # From link_images_fields in list
    
    # Get applicant's member image
    if application.get("applicant"):
        member_image = frappe.get_value("Member", application["applicant"], "member_image")
        if member_image:
            application["applicant_member_image"] = host_url + "/" + member_image.lstrip("/")
        else:
            application["applicant_member_image"] = ""

    return application





