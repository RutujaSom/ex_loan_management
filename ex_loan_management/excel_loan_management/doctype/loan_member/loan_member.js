// Copyright (c) 2025, Rutuja Somvanshi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Loan Member", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Loan Member', {
    refresh(frm) {
        frm.add_custom_button('Import Loan Member', () => {
            open_import_dialog(frm);
        });
        frm.add_custom_button('Update Loan Member', () => {
            open_import_dialog_to_update_records(frm);
        });


        if (frappe.user.has_role("Agent") && !frappe.user.has_role("Administrator")) {
            // Hide status field for Agents
            frm.set_df_property("status", "hidden", 1);

            // If status is Pending → make the whole form read-only
            if (!frm.is_new() && frm.doc.status == "Pending") {
                frm.disable_form();
            }
        }
        if (frm.doc.status === "Verified" || frm.doc.status === "Rejected") {
            // If record is updated after Approved/Rejected → go back to Pending
            frm.doc.status = "Pending";
        }
        // If Draft → keep it Draft until explicitly changed
        if (frm.is_new()) {
            frm.doc.status = "Pending";
        }
    }
});



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
            frappe.call({
                method: "ex_loan_management.excel_loan_management.doctype.loan_member.loan_member.import_loan_members",
                args: {
                    file_url: values.file_url,
                    file_type: values.file_type
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frappe.listview.refresh();  // refresh the list view
                    }
                    d.hide();
                }
            });
        }
    });

    d.show();
}



function open_import_dialog_to_update_records() {
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
            frappe.call({
                method: "ex_loan_management.excel_loan_management.doctype.loan_member.loan_member.import_update_loan_members",
                args: {
                    file_url: values.file_url,
                    file_type: values.file_type
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frappe.listview.refresh();  // refresh the list view
                    }
                    d.hide();
                }
            });
        }
    });

    d.show();
}



function update_status(frm, status) {
    frappe.call({
        method: "ex_loan_management.excel_loan_management.doctype.loan_member.loan_member.update_status",
        args: {
            docname: frm.doc.name,
            status: status
        },
        callback: function() {
            frm.reload_doc();
        }
    });
}
