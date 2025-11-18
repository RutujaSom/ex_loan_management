// Copyright (c) 2025, Rutuja Somvanshi and contributors
// For license information, please see license.txt


frappe.ui.form.on('Loan Group', {
    refresh(frm) {
        frm.add_custom_button('Import Loan Group', () => {
            open_import_dialog(frm);
        });
    },
    group_name(frm) {
        // alert("frm.doc.group_name ....",frm.doc.group_name)
        if (frm.doc.group_name) {
            frm.set_value("group_name", frm.doc.group_name.toUpperCase());
        }
    }
});



function open_import_dialog() {
    const d = new frappe.ui.Dialog({
        title: 'Import Loan Group',
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
                method: "ex_loan_management.excel_loan_management.doctype.loan_group.loan_group.import_loan_groups",
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
