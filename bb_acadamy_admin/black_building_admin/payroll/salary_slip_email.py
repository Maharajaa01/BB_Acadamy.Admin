import frappe
from frappe.utils import formatdate


EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a3c5e 0%,#2d6a9f 100%);padding:30px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;letter-spacing:1px;">BLACK BUILDING ACADEMY</h1>
            <p style="margin:6px 0 0 0;color:#a8d4f0;font-size:13px;letter-spacing:2px;">SALARY SLIP NOTIFICATION</p>
          </td>
        </tr>

        <!-- Greeting -->
        <tr>
          <td style="padding:30px 40px 10px 40px;">
            <p style="margin:0;font-size:15px;color:#333;">Dear <strong>{{ employee_name }}</strong>,</p>
            <p style="margin:12px 0 0 0;color:#555;font-size:14px;line-height:1.6;">
              Your salary slip for <strong>{{ period }}</strong> has been generated and processed successfully.
              Please find your salary breakdown below.
            </p>
          </td>
        </tr>

        <!-- Salary Summary Card -->
        <tr>
          <td style="padding:20px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0e8f0;border-radius:8px;overflow:hidden;">

              <!-- Earnings Header -->
              <tr style="background:#e8f4f0;">
                <td colspan="2" style="padding:10px 16px;font-weight:bold;font-size:13px;color:#2e7d32;letter-spacing:0.5px;">
                  EARNINGS
                </td>
              </tr>
              {% for row in earnings %}
              <tr>
                <td style="padding:9px 16px;font-size:13px;color:#444;border-top:1px solid #f0f0f0;">{{ row.salary_component }}</td>
                <td style="padding:9px 16px;font-size:13px;color:#2e7d32;text-align:right;border-top:1px solid #f0f0f0;">
                  + &#8377; {{ "%.2f" | format(row.amount) }}
                </td>
              </tr>
              {% endfor %}

              <!-- Deductions Header -->
              <tr style="background:#fdecea;">
                <td colspan="2" style="padding:10px 16px;font-weight:bold;font-size:13px;color:#c62828;letter-spacing:0.5px;">
                  DEDUCTIONS
                </td>
              </tr>
              {% if deductions %}
                {% for row in deductions %}
                <tr>
                  <td style="padding:9px 16px;font-size:13px;color:#444;border-top:1px solid #f0f0f0;">
                    {{ row.salary_component }}
                    {% if row.notes %}
                    <br><span style="font-size:11px;color:#999;">{{ row.notes }}</span>
                    {% endif %}
                  </td>
                  <td style="padding:9px 16px;font-size:13px;color:#c62828;text-align:right;border-top:1px solid #f0f0f0;">
                    &minus; &#8377; {{ "%.2f" | format(row.amount) }}
                  </td>
                </tr>
                {% endfor %}
              {% else %}
                <tr>
                  <td colspan="2" style="padding:9px 16px;font-size:13px;color:#999;text-align:center;">No deductions this month</td>
                </tr>
              {% endif %}

              <!-- Net Pay -->
              <tr style="background:#1a3c5e;">
                <td style="padding:14px 16px;font-size:15px;font-weight:bold;color:#ffffff;">NET PAY</td>
                <td style="padding:14px 16px;font-size:18px;font-weight:bold;color:#7ec8e3;text-align:right;">
                  &#8377; {{ "%.2f" | format(net_pay) }}
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Credit Notice -->
        <tr>
          <td style="padding:0 40px 20px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0"
              style="background:#e8f5e9;border-left:4px solid #4caf50;border-radius:0 6px 6px 0;padding:16px;">
              <tr>
                <td>
                  <p style="margin:0;color:#1b5e20;font-size:14px;font-weight:bold;">
                    &#10003; &nbsp;Salary Credit Notice
                  </p>
                  <p style="margin:6px 0 0 0;color:#2e7d32;font-size:13px;">
                    Your salary of <strong>&#8377; {{ "%.2f" | format(net_pay) }}</strong> will be
                    credited to your registered bank account <strong>within 4 hours</strong>.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Slip Reference -->
        <tr>
          <td style="padding:0 40px 25px 40px;">
            <p style="margin:0;font-size:12px;color:#999;">
              Salary Slip Reference: <strong>{{ salary_slip_name }}</strong> &nbsp;|&nbsp;
              Period: {{ period }}
            </p>
            <p style="margin:8px 0 0 0;font-size:12px;color:#bbb;">
              For queries, contact the HR department. This is a system-generated email — do not reply.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f0f4f8;padding:18px 40px;text-align:center;border-top:1px solid #e0e8f0;">
            <p style="margin:0;font-size:12px;color:#888;">
              &copy; Black Building Academy &nbsp;|&nbsp; HR Department
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def send_salary_slip_email(doc, method=None):
	"""
	Triggered: Salary Slip → On Submit
	Sends a professional HTML salary notification to the employee.
	"""
	try:
		employee = frappe.get_doc("Employee", doc.employee)
		email = _get_employee_email(employee)

		if not email:
			frappe.log_error(
				f"No email address found for {employee.employee_name} ({doc.employee}). "
				"Configure personal_email or company_email on the Employee record.",
				"Salary Slip Email - No Recipient"
			)
			return

		earnings = _get_component_rows(doc.earnings)
		deductions = _get_component_rows_with_notes(doc.deductions, doc)
		period = formatdate(doc.start_date, "MMMM yyyy")

		email_body = frappe.render_template(EMAIL_TEMPLATE, {
			"employee_name": employee.employee_name,
			"period": period,
			"earnings": earnings,
			"deductions": deductions,
			"net_pay": float(doc.net_pay or 0),
			"salary_slip_name": doc.name
		})

		frappe.sendmail(
			recipients=[email],
			subject=f"Salary Slip – {period} | Black Building Academy",
			message=email_body,
			reference_doctype="Salary Slip",
			reference_name=doc.name,
			now=True
		)

		frappe.msgprint(
			f"Salary slip email sent to <b>{employee.employee_name}</b> at {email}",
			alert=True,
			indicator="green"
		)

	except Exception:
		frappe.log_error(frappe.get_traceback(), "Salary Slip Email Failed")
		frappe.msgprint(
			"Salary slip created but email failed to send. Check Error Log for details.",
			alert=True,
			indicator="orange"
		)


def _get_employee_email(employee):
	"""Return the best available email for the employee."""
	preferred = employee.get("prefered_email") or "Personal"

	if preferred == "Company" and employee.company_email:
		return employee.company_email
	if preferred == "User" and employee.user_id:
		return frappe.db.get_value("User", employee.user_id, "email")
	# Default to personal email, fallback to company email
	return employee.personal_email or employee.company_email or None


def _get_component_rows(child_table):
	return [
		{"salary_component": row.salary_component, "amount": float(row.amount or 0)}
		for row in child_table
		if float(row.amount or 0) > 0
	]


def _get_component_rows_with_notes(child_table, salary_slip_doc):
	rows = []
	for row in child_table:
		amount = float(row.amount or 0)
		if amount <= 0:
			continue
		rows.append({
			"salary_component": row.salary_component,
			"amount": amount,
			"notes": ""
		})
	return rows
