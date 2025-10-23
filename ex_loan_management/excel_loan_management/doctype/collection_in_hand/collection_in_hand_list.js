



frappe.listview_settings['Collection In Hand'] = {
	onload: function(listview) {
        // Get logged-in user roles
        filters = []
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "User",
                filters: { name: frappe.session.user },
                fields: ["role_profile_name"]
            },
            callback: function(r) {
                const roles = frappe.user_roles; // already available
                alert("roles ....."+roles)

                // Admin or Loan Manager sees all records
                if (roles.includes("System Manager") 
                    // || roles.includes("Loan Manager")
                ) {
                    // No filter
                    listview.filters.clear_filters();
                } else {
                    // Non-admin users: filter where employee OR amount_given_emp = current user employee
                    frappe.call({
                        method: "frappe.client.get_value",
                        args: {
                            doctype: "Employee",
                            filters: { user_id: frappe.session.user },
                            fieldname: "name"
                        },
                        callback: function(emp_r) {
                            if (emp_r.message) {
                                const emp = emp_r.message.name;
                                alert("emp ..."+emp)

                                // Apply filters to list view
                                // listview.filter_area.add_filter('employee', '=', emp);
                                // listview.filter_area.add_or_filter('amount_given_emp', '=', emp);

                                // listview.filters.clear_filters()

                                // Add first filter
                                filters.append({
                                    fieldname: "employee",
                                    label: "Employee",
                                    fieldtype: "Link",
                                    options: "Employee",
                                    operator: "=",
                                    value: emp
                                });

                                // Add OR filter
                                filters.append({
                                    fieldname: "amount_given_emp",
                                    label: "Amount Given Employee",
                                    fieldtype: "Link",
                                    options: "Employee",
                                    operator: "=",
                                    value: emp,
                                    is_or: 1
                                });


                                listview.refresh(); // reload filtered list
                            }
                        }
                    });
                }
            }
        });
    }
};
