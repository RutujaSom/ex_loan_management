frappe.ui.form.on("Loan Application", {
    refresh(frm) {
        // add_import_button(frm);
        add_download_button(frm);
        set_applicant_query(frm);
    },

    applicant(frm) {
        set_group_based_filters(frm);
    },

    description(frm) {
        if (frm.doc.description) {
            frm.set_value("description", frm.doc.description.toUpperCase());
        }
    }
});

function add_import_button(frm) {
    frm.add_custom_button("Import Loan Application", () => {
        open_import_dialog();
    });
}

function open_import_dialog() {
    const d = new frappe.ui.Dialog({
        title: "Import Loan Application",
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
                method: "lending.loan_management.doctype.loan_application.loan_application.bulk_import_loan_applications",
                args: {
                    file_url: values.file_url,
                    file_type: values.file_type
                },
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
function set_group_based_filters(frm) {
    if (!frm.doc.applicant) return;

    frappe.db.get_value("Member", frm.doc.applicant, "group", (r) => {
        if (!r || !r.group) return;

        frm.set_query("co_borrower", () => ({
            filters: {
                group: r.group,
                name: ["!=", frm.doc.applicant]
            }
        }));

        frm.set_query("nominee", () => ({
            filters: {
                group: r.group,
                name: ["!=", frm.doc.applicant]
            }
        }));
    });
}

function set_group_based_filters(frm) {
    if (!frm.doc.applicant) return;

    frappe.db.get_value("Member", frm.doc.applicant, "group", (r) => {
        if (!r || !r.group) return;

        frm.set_query("co_borrower", () => ({
            filters: {
                group: r.group,
                name: ["!=", frm.doc.applicant]
            }
        }));

        frm.set_query("nominee", () => ({
            filters: {
                group: r.group,
                name: ["!=", frm.doc.applicant]
            }
        }));
    });
}

function add_download_button(frm) {
    frm.add_custom_button("Download PDF", () => {
        add_print_button(frm);
    });
}

function add_print_button(frm) {
    const d = new frappe.ui.Dialog({
        title: "Select Report Format",
        fields: [
            {
                label: "Report Format",
                fieldname: "format",
                fieldtype: "Select",
                options: [
                    { label: "Demand Promissory Note", value: "demand promissory note" },
                    { label: "DP Note Waiver Letter", value: "dp note cum waiver letter" },
                    { label: "Sanction Letter", value: "Sanction Letter" },
                    { label: "Policy Apply Letter", value: "Policy Apply Letter" },
                    { label: "Individual Declaration", value: "Individual Decleration and Terms and Conditions version jan 24" },
                    { label: "Group Declaration", value: "Group Declaration And Terms And Consition VERSION JAN 24" },
                    { label: "Group Loan Agreement", value: "GROUP LOAN AGREEMENT version jan 24" },
                    { label: "Fact Sheet", value: "Fact Sheet" },
                    { label: "Individual Loan Agreement For Borrower", value: "Individual Loan Agremeent" },
                    { label: "Individual Loan Agreement For Co-borrower", value: "Individual Loan Agremeent For Co-borrower" }
                ]
            }
        ],
        primary_action_label: "Download",
        primary_action(values) {
            const url = `/api/method/frappe.utils.print_format.download_pdf?doctype=Loan Application&name=${frm.doc.name}&format=${values.format}`;
            window.open(url, "_blank");
            d.hide();
        }
    });

    d.show();
}