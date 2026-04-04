// frappe.ui.form.on('Loan Repayment', {
//     repayment_type: function(frm) {
//         if (frm.doc.posting_date) {
//             frm.trigger('calculate_repayment_amounts');
//         }
//     },

//     calculate_repayment_amounts: function(frm) {
//         console.log(frm.doc.repayment_type); // should NOT be undefined

//         frappe.call({
//             method: 'lending.loan_management.doctype.loan_repayment.loan_repayment.calculate_amounts',
//             args: {
//                 against_loan: frm.doc.against_loan,
//                 posting_date: frm.doc.posting_date,
//                 payment_type: frm.doc.repayment_type   // 👈 pass correct value
//             },
//             callback: function(r) {
//                 let amounts = r.message;

//                 frm.set_value('amount_paid', 0.0);
               
//                 frm.set_value('pending_principal_amount', amounts.pending_principal_amount);

//                 // ✅ EXISTING DOC → always trust DB
//                 if (!frm.is_new()) {
//                     frappe.db.get_value(
//                         'Loan Repayment',
//                         frm.doc.name,
//                         'amount_paid'
//                     ).then(r => {
//                         if (r && r.message) {
//                             frm.set_value('amount_paid', r.message.amount_paid);
//                         }
//                     });
//                     return; // ⛔ stop further calculation
//                 }

//                 if (frm.doc.is_term_loan || frm.doc.repayment_type === "Loan Closure") {
//                     frm.set_value('payable_principal_amount', amounts.payable_principal_amount);
//                     frm.set_value('amount_paid', amounts.payable_amount);
//                 }

//                 frm.set_value('interest_payable', amounts.interest_amount);
//                 frm.set_value('penalty_amount', amounts.penalty_amount);
//                 frm.set_value('payable_amount', amounts.payable_amount);
//                 frm.set_value('total_charges_payable', amounts.total_charges_payable);
//             }
//         });
//     }
// });



frappe.ui.form.on('Loan Repayment', {
    repayment_type(frm) {
        if (frm.doc.posting_date) {
            frm.trigger('calculate_repayment_amounts');
        }
    },

    custom_mode_of_payment(frm) {
        frm.trigger('set_repayment_account_from_loan_product');
    },

    custom_mode_of_payment(frm) {
        frm.trigger('set_repayment_account_from_loan_product');
    },

    set_repayment_account_from_loan_product(frm) {
        if (!frm.doc.loan_product || !frm.doc.custom_mode_of_payment) return;

        frappe.db.get_value(
            'Loan Product',
            frm.doc.loan_product,
            ['custom_online_repayment_account', 'payment_account']
        ).then(r => {
            if (!r || !r.message) return;

            let mode = (frm.doc.custom_mode_of_payment || '').toUpperCase();

            // ✅ ONLINE payment
            if (mode === 'ONLINE') {
                if (r.message.custom_online_repayment_account) {
                    frm.set_value(
                        'payment_account',
                        r.message.custom_online_repayment_account
                    );
                }
            }

            // ✅ CASH payment
            if (mode === 'CASH') {
                if (r.message.payment_account) {
                    frm.set_value(
                        'payment_account',
                        r.message.payment_account
                    );
                }
            }
        });
    },

    calculate_repayment_amounts(frm) {
        frappe.call({
            method: 'lending.loan_management.doctype.loan_repayment.loan_repayment.calculate_amounts',
            args: {
                against_loan: frm.doc.against_loan,
                posting_date: frm.doc.posting_date,
                payment_type: frm.doc.repayment_type
            },
            callback(r) {
                let amounts = r.message;

                frm.set_value('amount_paid', 0.0);
                frm.set_value('pending_principal_amount', amounts.pending_principal_amount);

                // ✅ EXISTING DOC → trust DB
                if (!frm.is_new()) {
                    frappe.db.get_value(
                        'Loan Repayment',
                        frm.doc.name,
                        'amount_paid'
                    ).then(res => {
                        if (res && res.message) {
                            frm.set_value('amount_paid', res.message.amount_paid);
                        }
                    });
                    return;
                }

                if (frm.doc.is_term_loan || frm.doc.repayment_type === "Loan Closure") {
                    frm.set_value('payable_principal_amount', amounts.payable_principal_amount);
                    frm.set_value('amount_paid', amounts.payable_amount);
                }

                frm.set_value('interest_payable', amounts.interest_amount);
                frm.set_value('penalty_amount', amounts.penalty_amount);
                frm.set_value('payable_amount', amounts.payable_amount);
                frm.set_value('total_charges_payable', amounts.total_charges_payable);
            }
        });
    }
});