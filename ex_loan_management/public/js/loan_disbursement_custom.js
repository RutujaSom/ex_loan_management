// ========================================================
// Loan Disbursement – Custom JS
// Developer: Rutuja Somvanshi
// ========================================================

frappe.ui.form.on("Loan Disbursement", {
    // ----------------------------------------------------
    // Refresh
    // ----------------------------------------------------
    refresh(frm) {
        if (frm.is_new()) {
            frm.add_custom_button("Import Loan Disbursement", () => {
                open_import_dialog(frm);
            });
        }
    },
});


// ========================================================
// Import Dialog
// ========================================================
function open_import_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: "Import Loan Disbursement",
        fields: [
            {
                label: "File Type",
                fieldname: "file_type",
                fieldtype: "Select",
                options: ["CSV", "Excel"],
                reqd: 1
            },
            {
                label: "File",
                fieldname: "file_url",
                fieldtype: "Attach",
                reqd: 1
            }
        ],
        primary_action_label: "Import",
        primary_action(values) {
            frappe.call({
                method: "lending.loan_management.doctype.loan_disbursement.loan_disbursement.import_and_submit_disbursement",
                args: values,
                callback(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frappe.listview.refresh();
                    }
                    d.hide();
                }
            });
        }
    });

    d.show();
}