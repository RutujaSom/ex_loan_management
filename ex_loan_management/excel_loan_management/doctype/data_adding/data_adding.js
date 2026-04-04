// Copyright (c) 2026, Rutuja Somvanshi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Data adding", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Data adding', {
    refresh(frm) {
        // --- Custom Buttons ---
        // Import new Members
        frm.add_custom_button('Import Data', () => {
            open_import_dialog(frm);
        });
        
    }
})



// -----------------------------------------------------------------------------
// Dialog to Import Members
// -----------------------------------------------------------------------------
function open_import_dialog() {
    const d = new frappe.ui.Dialog({
        title: 'Import Member',
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
                method: "ex_loan_management.excel_loan_management.doctype.data_adding.data_adding.update_loan_amount_from_excel",
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
