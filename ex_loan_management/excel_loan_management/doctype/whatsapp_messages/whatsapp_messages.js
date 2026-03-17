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
    },

    refresh: function(frm) {
        // Option A: Use standard ERPNext/Bootstrap Primary (Blue)
        frm.set_df_property('open_url', 'class', 'btn-primary');

        // Option B: Hardcode a specific custom color via CSS
        setTimeout(() => {
            frm.fields_dict['open_url'].$wrapper.find('button').css({
                'background-color': '#007bff', // Blue Background
                'color': 'white',              // White Text
                'font-weight': 'bold'
            });
        }, 10);
    },

    open_url: function(frm) {
        if (frm.doc.external_link) {
            window.open(frm.doc.external_link, '_blank');
        } else {
            frappe.msgprint(__('Please enter a URL first.'));
        }
    }
});

frappe.listview_settings['Whatsapp Messages'] = {
    order_by: "creation desc"
};