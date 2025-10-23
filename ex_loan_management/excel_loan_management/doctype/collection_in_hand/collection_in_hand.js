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




frappe.ui.form.on("Collection In Hand", {
    refresh(frm) {
        // Clear buttons on refresh to avoid duplicates
        frm.clear_custom_buttons();

        // Only show buttons when record exists (not new)
        if (!frm.is_new()) {
            // Check if the logged-in user is the assigned employee
            const current_user = frappe.session.user;
            const assigned_emp = frm.doc.amount_given_emp;

            if (assigned_emp) {
                frappe.db.get_value("Employee", assigned_emp, "user_id")
                    .then(r => {
                        const emp_user_id = r.message.user_id;
                        if (emp_user_id === current_user) {
                            // ✅ Show Approve and Reject buttons
                            frm.add_custom_button("Approve", () => {
                                frappe.call({
                                    method: "your_app.your_module.doctype.collection_in_hand.collection_in_hand.approve_or_reject_collection",
                                    args: {
                                        name: frm.doc.name,
                                        action: "approve"
                                    },
                                    callback: (r) => {
                                        frappe.show_alert({ message: r.message, indicator: 'green' });
                                        frm.reload_doc();
                                    }
                                });
                            }, "Actions");

                            frm.add_custom_button("Reject", () => {
                                frappe.call({
                                    method: "your_app.your_module.doctype.collection_in_hand.collection_in_hand.approve_or_reject_collection",
                                    args: {
                                        name: frm.doc.name,
                                        action: "reject"
                                    },
                                    callback: (r) => {
                                        frappe.show_alert({ message: r.message, indicator: 'red' });
                                        frm.reload_doc();
                                    }
                                });
                            }, "Actions");
                        }
                    });
            }
        }
    }
});









