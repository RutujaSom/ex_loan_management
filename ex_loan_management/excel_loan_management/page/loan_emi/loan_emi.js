
frappe.pages['loan-emi'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Loan EMI',
        single_column: true
    });

    let current_sort = { field: null, order: null }; // keep track of current sorting
    $(page.body).append(`
        <div class="mb-4 d-flex justify-content-between align-items-center flex-wrap">
            <!-- Left Side -->
            <div class="d-flex gap-3 align-items-center flex-wrap">

                <div class="d-flex flex-column" style="margin-right: 1.5rem;">
                    <label for="emi-date" class="form-label" style="font-weight: 500;">Upto Date</label>
                    <input type="date" id="emi-date" class="input-with-feedback form-control" style="width:180px;" />
                </div>

                <div class="d-flex flex-column" style="margin-right: 1.5rem;">
                    <label for="selected-date" class="form-label" style="font-weight: 500;">Selected Date</label>
                    <input type="date" id="selected-date" class="input-with-feedback form-control" style="width:180px;" />
                </div>

                <div class="d-flex flex-column" style="margin-right: 1.5rem;">
                    <label for="emi-employee" class="form-label" style="font-weight: 500;">Employee</label>
                    <select id="emi-employee" class="form-control" style="width:220px; display:none;">
                        <option value="">-- All Employees --</option>
                    </select>
                </div>

                <div class="d-flex flex-column">
                    <label for="emi-loan-group" class="form-label" style="font-weight: 500;">Loan Group</label>
                    <select id="emi-loan-group" class="form-control" style="width:220px; display:none;">
                        <option value="">-- All Loan Groups --</option>
                    </select>
                </div>
            </div>

            <!-- Right Side -->
            <div class="d-flex gap-2 align-items-end flex-wrap">
                <div class="d-flex flex-column" style="margin-right: 1rem;">
                    <label for="emi-search" class="form-label" style="font-weight: 500;">Search</label>
                    <input type="text" id="emi-search" class="input-with-feedback form-control" style="width:200px;" placeholder="Search loan/applicant" />
                </div>
                <button class="btn btn-primary btn-sm" id="filter-emi" style="height:38px;">Search</button>
            </div>
        </div>

        <div class="emi-container mt-4">
            <h3>EMIs</h3>
            <div id="emi-list"></div>
        </div>
    `);


    // Set today's date by default
    let today = frappe.datetime.get_today();
    $("#emi-date").val(today);
    // $("#selected-date").val(today);

    // ✅ Employee & Loan Group filter
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { user_id: frappe.session.user },
            fieldname: ["name"]
        },
        callback: function(res) {
            let employee_id = res.message ? res.message.name : null;

            // If Admin/System Manager → Show all employees & loan groups
            if (frappe.user_roles.includes("Administrator") || frappe.user_roles.includes("System Manager")) {
                $("#emi-employee").show();
                $("#emi-loan-group").show();

                // Load employees
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee",
                        fields: ["name", "employee_name"],
                        limit_page_length: 500
                    },
                    callback: function(res) {
                        if (res.message) {
                            res.message.forEach(emp => {
                                $("#emi-employee").append(
                                    `<option value="${emp.name}">${emp.employee_name} (${emp.name})</option>`
                                );
                            });
                        }
                    }
                });

                // Load all Loan Groups
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Loan Group",
                        fields: ["name","group_name"],
                        limit_page_length: 500
                    },
                    callback: function(res) {
                        if (res.message) {
                            res.message.forEach(lg => {
                                $("#emi-loan-group").append(
                                    `<option value="${lg.name}">${lg.group_name}</option>`
                                );
                            });
                        }
                    }
                });

            } else if (employee_id) {
                // Normal Employee → Load only assigned Loan Groups
                $("#emi-loan-group").show();
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Loan Group Assignment",
                        filters: { employee: employee_id },
                        fields: ["loan_group"],
                        limit_page_length: 500
                    },
                    callback: function(res) {
                        if (res.message) {
                            let loan_groups = res.message.map(r => r.loan_group);

                            if (loan_groups.length) {
                                // fetch loan group names from Loan Group doctype
                                frappe.call({
                                    method: "frappe.client.get_list",
                                    args: {
                                        doctype: "Loan Group",
                                        filters: { name: ["in", loan_groups] },
                                        fields: ["name", "group_name"],   // 👈 adjust to actual field
                                        limit_page_length: 500
                                    },
                                    callback: function(r2) {
                                        if (r2.message) {
                                            r2.message.forEach(lg => {
                                                $("#emi-loan-group").append(
                                                    `<option value="${lg.name}">${lg.group_name || lg.name}</option>`
                                                );
                                            });
                                        }
                                    }
                                });
                            }
                        }
                    }
                });

            }
        }
    });

    function load_emis(upto_date=null, search_text=null, sort_by=null, sort_order=null, employee=null, loan_group=null, selected_date=null) {
        frappe.call({
            method: "lending.loan_management.doctype.repayment_schedule.repayment_schedule.get_todays_emis",
            args: { 
                upto_date: upto_date,
                search_text: search_text,
                sort_by: sort_by,
                sort_order: sort_order,
                employee: employee,
                loan_group: loan_group,
                selected_date: selected_date
            },
            callback: function(r) {
                if (!r.message || r.message.length === 0) {
                    $('#emi-list').html('<p>No EMIs for this date 🎉</p>');
                    return;
                }

                let html = `<table class="table table-bordered table-striped">
                    <thead>
                        <tr>
                            <th data-field="lrs.loan">Loan</th>
                            <th data-field="lm.member_name">Applicant</th>
                            <th data-field="rs.payment_date">Payment Date</th>
                            <th data-field="rs.principal_amount">Principal</th>
                            <th data-field="rs.interest_amount">Interest</th>
                            <th data-field="rs.total_payment">Total Payment</th>
                            <th data-field="rs.balance_loan_amount">Balance</th>
                            <th>Status</th>
                            <th>Remaining</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>`;

                r.message.forEach(row => {
                    html += `
                        <tr>
                            <td>${row.loan}</td>
                            <td>${row.member_name || row.applicant}</td>
                            <td>${row.payment_date}</td>
                            <td>${row.principal_amount}</td>
                            <td>${row.interest_amount}</td>
                            <td>${row.total_payment}</td>
                            <td>${row.balance_loan_amount}</td>
                            <td>${row.payment_status}</td>
                            <td>${row.remaining_amount}</td>
                            <td>
                                <button class="btn btn-sm btn-primary update-repayment" 
                                        data-loan="${row.loan}" data-payment_date="${row.payment_date}" 
                                        data-applicant="${row.member_name}">
                                    Update
                                </button>
                            </td>
                        </tr>`;
                });

                html += `</tbody></table>`;
                $('#emi-list').html(html);

                // 🔄 Update button
                $(".update-repayment").off("click").on("click", function() {
                    let loan_id = $(this).data("loan");
                    let posting_date = $(this).data("payment_date");

                    frappe.new_doc("Loan Repayment", {
                        against_loan: loan_id,
                        posting_date: posting_date
                    });
                });

                // Sorting logic stays same...
            }
        });
    }

    // Load today's EMIs on page load
    load_emis();

    // Filter events
    $(document).on("click", "#filter-emi", function() {
        let upto_date = $("#emi-date").val();
        let search_text = $("#emi-search").val();
        let employee = $("#emi-employee").val();
        let loan_group = $("#emi-loan-group").val();
        let selected_date = $("#selected-date").val();
        load_emis(upto_date, search_text, current_sort.field, current_sort.order, employee, loan_group, selected_date);
    });

    $(document).on("change", "#emi-date, #emi-employee, #emi-loan-group, #selected-date", function(e) {
        let upto_date = $("#emi-date").val();
        let search_text = $("#emi-search").val();
        let employee = $("#emi-employee").val();
        let loan_group = $("#emi-loan-group").val();
        let selected_date = $("#selected-date").val();

        // 👉 If emi-date changed → clear selected-date
        if (e.target.id === "emi-date" && upto_date) {
            $("#selected-date").val("");
            selected_date = "";
        }
        if (e.target.id === "selected-date" && selected_date) {
            $("#emi-date").val("");
            upto_date = "";
        }
        load_emis(upto_date, search_text, current_sort.field, current_sort.order, employee, loan_group, selected_date);
    });

};

