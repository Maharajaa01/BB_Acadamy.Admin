# Copyright (c) 2026, Maha Raja and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AdmissionInquiry(Document):
    def after_insert(self):
        """Send email to Sales Manager when a new admission inquiry is created"""
        self.send_email_to_sales_manager()

    def send_email_to_sales_manager(self):
        """Send admission inquiry details to Sales Manager"""
        try:
            # Get all users with Sales Manager role
            sales_managers = frappe.db.get_list(
                "User",
                filters={"name": ["in", frappe.db.get_all("Has Role", 
                    filters={"role": "Sales Manager"}, 
                    pluck="parent")]},
                fields=["email", "full_name"]
            )

            if not sales_managers:
                frappe.log_error("No Sales Manager found for email notification")
                return

            # Prepare email content
            subject = f"New Admission Inquiry - {self.student_name}"
            
            html_content = f"""
            <h3>New Admission Inquiry Received</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Student Name</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{self.student_name}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Email</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><a href="mailto:{self.email}">{self.email}</a></td>
                </tr>
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Phone</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{self.phone}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Standard</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{self.standard}</td>
                </tr>
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Group</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{self.group or "N/A"}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Message</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{self.message or "N/A"}</td>
                </tr>
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid #ddd; padding: 8px;"><b>Status</b></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{self.status}</td>
                </tr>
            </table>
            <p><a href="{frappe.utils.get_url()}/app/admission-inquiry/{self.name}">View Full Details</a></p>
            """

            # Send email to each Sales Manager
            for manager in sales_managers:
                frappe.sendmail(
                    recipients=[manager.get("email")],
                    subject=subject,
                    message=html_content,
                    delayed=False
                )

        except Exception as e:
            frappe.log_error(f"Error sending email to Sales Manager: {str(e)}")