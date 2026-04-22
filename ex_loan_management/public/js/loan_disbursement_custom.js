// ========================================================
// Loan Disbursement – Custom JS
// Developer: Rutuja Somvanshi
// ========================================================

frappe.ui.form.on("Loan Disbursement", {
    // ----------------------------------------------------
    // Refresh
    // ----------------------------------------------------
    refresh(frm) {
        // if (frm.is_new()) {
        //     frm.add_custom_button("Import Loan Disbursement", () => {
        //         open_import_dialog(frm);
        //     });
        // }

        // ✅ Trigger auto-fetch when opened via ➕ from Loan
        if (frm.is_new()) {
            frm.trigger("fetch_loan_charges");
        }
    },

    against_loan(frm) {
        frm.trigger("fetch_loan_charges");
    },

    disbursed_amount(frm) {
        frm.trigger("fetch_loan_charges");
    },

    fetch_loan_charges(frm) {
        // 🔒 Guard condition
        if (!frm.doc.against_loan || !frm.doc.disbursed_amount) {
            return;
        }

        frappe.call({
            method: "ex_loan_management.api.loan_dis_charges.get_loan_charges",
            args: {
                loan: frm.doc.against_loan,
                disbursed_amount: frm.doc.disbursed_amount
            },
            callback(r) {
                if (!r.message) return;

                frm.clear_table("loan_disbursement_charges");

                r.message.forEach(row => {
                    let d = frm.add_child("loan_disbursement_charges");
                    d.charge = row.charge_type;
                    d.amount = row.amount;
                    d.account = row.account;
                });

                frm.refresh_field("loan_disbursement_charges");
            }
        });
    }
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