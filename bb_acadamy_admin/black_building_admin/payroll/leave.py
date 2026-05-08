import frappe
from frappe.utils import get_first_day, get_last_day, getdate


EXEMPT_LEAVE_TYPES = ["Compensatory Off", "Privilege Leave", "Annual Leave"]


def create_leave_deduction(doc, method=None):
	"""
	Deduction rules:
	  - MD Approved leave    → 1× per_day_salary per leave day
	  - 1st leave in month   → 1× per_day_salary per leave day
	  - 2nd+ leave in month  → 2× per_day_salary per leave day

	per_day_salary is calculated live: monthly_salary / 26 working days.
	Triggered: Leave Application → On Submit
	"""
	if doc.leave_type in EXEMPT_LEAVE_TYPES:
		return

	from bb_acadamy_admin.black_building_admin.payroll.employee import get_per_day_salary
	per_day_salary = get_per_day_salary(doc.employee)

	if not per_day_salary:
		frappe.log_error(
			f"No active Salary Structure Assignment for {doc.employee_name} ({doc.employee}). "
			"Leave deduction skipped.",
			"Leave Deduction - No Salary"
		)
		return

	is_md_approved = int(doc.get("custom_md_approved") or 0)
	leave_days = float(doc.total_leave_days or 1)

	if is_md_approved:
		multiplier = 1
		note_tag = "MD Approved"
	else:
		prior_count = _count_prior_leaves_this_month(doc)
		if prior_count == 0:
			multiplier = 1
			note_tag = "1st Leave"
		else:
			multiplier = 2
			note_tag = f"Leave #{prior_count + 1} (2× rule)"

	deduction_amount = round(leave_days * per_day_salary * multiplier, 2)

	_upsert_additional_salary(
		employee=doc.employee,
		component="Leave Deduction",
		amount=deduction_amount,
		payroll_date=doc.from_date,
		company=doc.company,
		ref_doctype="Leave Application",
		ref_docname=doc.name,
		notes=(
			f"{note_tag}: {leave_days:.1f} day(s) × "
			f"₹{per_day_salary:.2f} × {multiplier}× = ₹{deduction_amount:.2f}"
		)
	)

	frappe.msgprint(
		f"Leave deduction <b>₹{deduction_amount:.2f}</b> created for {doc.employee_name} "
		f"({note_tag}, {leave_days:.1f} day(s))",
		alert=True,
		indicator="orange"
	)


def cancel_leave_deduction(doc, method=None):
	"""Cancel linked Additional Salary when leave application is cancelled."""
	records = frappe.get_all(
		"Additional Salary",
		filters={
			"ref_doctype": "Leave Application",
			"ref_docname": doc.name,
			"docstatus": 1
		},
		fields=["name"]
	)
	for record in records:
		frappe.get_doc("Additional Salary", record.name).cancel()
	if records:
		frappe.msgprint(
			f"Leave deduction cancelled for {doc.employee_name}",
			alert=True
		)


def _count_prior_leaves_this_month(doc):
	"""Count submitted non-MD-approved leaves this month, excluding current doc."""
	month_start = get_first_day(getdate(doc.from_date))
	month_end = get_last_day(getdate(doc.from_date))

	return frappe.db.count(
		"Leave Application",
		filters={
			"employee": doc.employee,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["between", [month_start, month_end]],
			"name": ["!=", doc.name],
			"leave_type": ["not in", EXEMPT_LEAVE_TYPES],
			"custom_md_approved": 0,
		}
	)


def _upsert_additional_salary(
	employee, component, amount, payroll_date,
	company, ref_doctype, ref_docname, notes
):
	"""Cancel-and-recreate if already exists (idempotent)."""
	existing = frappe.db.get_value(
		"Additional Salary",
		{
			"ref_doctype": ref_doctype,
			"ref_docname": ref_docname,
			"salary_component": component,
			"docstatus": ["!=", 2]
		},
		"name"
	)
	if existing:
		old = frappe.get_doc("Additional Salary", existing)
		if old.docstatus == 1:
			old.cancel()
		old.delete()

	add_sal = frappe.new_doc("Additional Salary")
	add_sal.employee = employee
	add_sal.salary_component = component
	add_sal.type = "Deduction"
	add_sal.amount = amount
	add_sal.payroll_date = payroll_date
	add_sal.company = company
	add_sal.ref_doctype = ref_doctype
	add_sal.ref_docname = ref_docname
	add_sal.insert(ignore_permissions=True)
	add_sal.submit()
