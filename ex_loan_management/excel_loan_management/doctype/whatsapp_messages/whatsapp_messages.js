// Copyright (c) 2026, Rutuja Somvanshi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Whatsapp Messages", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Whatsapp Messages', {
    onload: function(frm) {
        if (!frm.doc.is_read) {
            frm.set_value('is_read', 1);
            frm.save();
        }
    }
});

frappe.listview_settings['Whatsapp Messages'] = {
    order_by: "creation desc"
};