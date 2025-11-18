// Copyright (c) 2025, Rutuja Somvanshi and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Member', {
    onload: function(frm) {
        // Apply filter on "group" field → show only Approved groups
        frm.set_query("group", function() {
            return {
                filters: {
                    workflow_state: "Approved"
                }
            };
        });
        // Make field read-only
        frm.toggle_enable("country", false);
        frm.toggle_enable("state", false);
    },

    refresh(frm) {
        // --- Custom Buttons ---
        // Import new Loan Members
        frm.add_custom_button('Import Loan Member', () => {
            open_import_dialog(frm);
        });
        // Update existing Loan Members
        frm.add_custom_button('Update Loan Member', () => {
            open_import_dialog_to_update_records(frm);
        });

        // --- Default Status Handling ---
        // Set default status as Draft for new records
        if (frm.is_new()) {
            frm.doc.status = "Draft";
            frm.set_df_property("status", "hidden", 1);
        }

        // --- Role-based Restrictions for Agent ---
        if (frappe.user.has_role("Agent") && !frappe.user.has_role("Administrator")) {
            // Make form read-only if status = Pending
            if (!frm.is_new() && frm.doc.status == "Pending") {
                frm.disable_form();
            }

            console.log("frm.doc.status ....", frm.doc.status);

            // Limit status options for Agent
            if (frm.doc.status === "Draft") {
                frm.set_df_property("status", "hidden", 0);
                frm.set_df_property("status", "options", ["Draft", "Pending"]);
            } else {
                // Hide status field after submission
                frm.set_df_property("status", "hidden", 1);
            }
        }

        // --- Status Reversion Logic ---
        // If record is reopened after verification/rejection → revert to Pending
        if (frm.doc.status === "Verified" || frm.doc.status === "Rejected") {
            frm.doc.status = "Pending";
        }

        // --- Mobile Number Prefix Handling ---
        // Add +91 prefix automatically if missing
        if (!frm.doc.mobile_no) {
            frm.set_value("mobile_no", "+91");
        }
        if (!frm.doc.mobile_no_2) {
            frm.set_value("mobile_no_2", "+91");
        }

        // Make field read-only
        frm.toggle_enable("country", false);
        frm.toggle_enable("state", false);

    },

    validate(frm) {
        frm.meta.fields.forEach(df => {
            // Only convert text-based fields
            if (["Data", "Small Text", "Text", "Text Editor", ].includes(df.fieldtype)) {
                let fieldname = df.fieldname;

                if (fieldname != 'email'){
                    if (frm.doc[fieldname] && typeof frm.doc[fieldname] === "string") {
                        frm.set_value(fieldname, frm.doc[fieldname].toUpperCase());
                    }
                }
            }
        });
    },
    address_doc_type: function(frm) {
        // Clear dependent fields when address changes
        frm.set_value("consumer_no", "");
        frm.set_value("address_image", "");

        frm.refresh_fields();
    }
});


// -----------------------------------------------------------------------------
// Dialog to Import Loan Members
// -----------------------------------------------------------------------------
function open_import_dialog() {
    const d = new frappe.ui.Dialog({
        title: 'Import Loan Member',
        fields: [
            {
                label: 'File Type',
                fieldname: 'file_type',
                fieldtype: 'Select',
                options: ['CSV', 'Excel'],
                reqd: 1
            },
            {
                label: 'File',
                fieldname: 'file_url',
                fieldtype: 'Attach',
                reqd: 1
            }
        ],
        primary_action_label: 'Import',
        primary_action(values) {
            // Call server-side method to import members
            frappe.call({
                method: "ex_loan_management.excel_loan_management.doctype.loan_member.loan_member.import_loan_members",
                args: {
                    file_url: values.file_url,
                    file_type: values.file_type
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frappe.listview.refresh();  // Refresh list view after import
                    }
                    d.hide();
                }
            });
        }
    });

    d.show();
}


// -----------------------------------------------------------------------------
// Dialog to Update Existing Loan Members
// -----------------------------------------------------------------------------
function open_import_dialog_to_update_records() {
    const d = new frappe.ui.Dialog({
        title: 'Update Loan Member',
        fields: [
            {
                label: 'File Type',
                fieldname: 'file_type',
                fieldtype: 'Select',
                options: ['CSV', 'Excel'],
                reqd: 1
            },
            {
                label: 'File',
                fieldname: 'file_url',
                fieldtype: 'Attach',
                reqd: 1
            }
        ],
        primary_action_label: 'Import',
        primary_action(values) {
            // Call server-side method to update records
            frappe.call({
                method: "ex_loan_management.excel_loan_management.doctype.loan_member.loan_member.import_update_loan_members",
                args: {
                    file_url: values.file_url,
                    file_type: values.file_type
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frappe.listview.refresh();  // Refresh list view after update
                    }
                    d.hide();
                }
            });
        }
    });

    d.show();
}


// -----------------------------------------------------------------------------
// Utility function to update status via server call
// -----------------------------------------------------------------------------
function update_status(frm, status) {
    frappe.call({
        method: "ex_loan_management.excel_loan_management.doctype.loan_member.loan_member.update_status",
        args: {
            docname: frm.doc.name,
            status: status
        },
        callback: function() {
            frm.reload_doc(); // Reload document after status update
        }
    });
}


