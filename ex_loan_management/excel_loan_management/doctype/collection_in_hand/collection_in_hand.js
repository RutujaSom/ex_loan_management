// Copyright (c) 2025, Rutuja Somvanshi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Collection In Hand", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on("Collection In Hand", {
    onload: function(frm) {
        // Check if current user has "Agent" role
        if (frappe.user_roles.includes("Agent") && !frappe.user_roles.includes("Administrator")) {
            // Hide the employee field
            frm.toggle_display("employee", false);

            // Fetch linked employee for logged in user
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Employee",
                    filters: { user_id: frappe.session.user },
                    fields: ["name"]
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value("employee", r.message[0].name);
                    }
                }
            });
        }
    }
});
