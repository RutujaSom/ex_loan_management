// Copyright (c) 2025, Rutuja Somvanshi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Loan Member", {
// 	refresh(frm) {

// 	},
// });



// frappe.ui.form.on('Loan Member', {
//     refresh(frm) {
//         if (!frm.is_new()) {
//             frm.add_custom_button(__('Import Loan Members'), function () {
//                 frappe.prompt([
//                     {
//                         fieldname: 'file_url',
//                         label: 'File URL (from File Manager)',
//                         fieldtype: 'Data',
//                         reqd: 1
//                     }
//                 ],
//                 function(values){
//                     frappe.call({
//                         method: "ex_loan_management.excel_loan_management.doctype.loan_member.loan_member.import_loan_members",
//                         args: {
//                             file_url: values.file_url
//                         },
//                         callback: function(r) {
//                             frappe.msgprint(r.message);
//                         }
//                     });
//                 },
//                 __('Import Loan Members'),
//                 __('Start Import'));
//             });
//         }
//     }
// });



frappe.ui.form.on('Loan Member', {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button('Import Loan Member', () => {
                open_import_dialog(frm);
            });
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
