// Copyright (c) 2026, Maha Raja and contributors
// For license information, please see license.txt

frappe.ui.form.on("Admission Inquiry", {
    after_save(frm) {
        // Show confirmation message
        if (frm.doc.__islocal === false) {
            frappe.msgprint({
                title: __("Success"),
                message: __("Admission Inquiry has been created and Sales Manager has been notified."),
                indicator: "green"
            });
        }
    }
});