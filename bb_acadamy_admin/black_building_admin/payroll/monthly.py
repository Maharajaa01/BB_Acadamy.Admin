import frappe
from frappe.utils import get_first_day, get_last_day, add_months, today, getdate


def create_attendance_deductions(month_date=None):
	"""
	Aggregate late + early-exit minutes from Employee Checkin for each active employee.
	Creates Additional Salary deduction records (idempotent — safe to re-run).

	Triggered automatically: 28th of each month at 9 AM (cron in hooks.py)

	Manual trigger via bench console:
	  frappe.enqueue(
	      'bb_acadamy_admin.black_building_admin.payroll.monthly.create_attendance_deductions',
	      month_date='2026-04-30'
	  )
	  frappe.db.commit()
	"""
	if not month_date:
		month_date = add_months(today(), -1)

	month_date = getdate(month_date)
	month_start = get_first_day(month_date)
	month_end = get_last_day(month_date)

	frappe.logger("payroll").info(
		f"BB Academy: Processing attendance deductions for {month_start} → {month_end}"
	)

	from bb_acadamy_admin.black_building_admin.payroll.employee import get_per_minute_salary

	active_employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "company"]
	)

	processed, skipped = 0, 0

	for emp in active_employees:
		per_minute = get_per_minute_salary(emp.name)

		if not per_minute:
			frappe.logger("payroll").warning(
				f"Skipping {emp.employee_name}: no salary assignment or timing config"
			)
			skipped += 1
			continue

		_process_late_deduction(emp, per_minute, month_start, month_end)
		_process_early_exit_deduction(emp, per_minute, month_start, month_end)
		processed += 1

	frappe.logger("payroll").info(
		f"BB Academy deduction run done. Processed: {processed}, Skipped: {skipped}"
	)

	return {"processed": processed, "skipped": skipped, "period": str(month_start)}


def _process_late_deduction(emp, per_minute, month_start, month_end):
	result = frappe.db.sql("""
		SELECT COALESCE(SUM(custom_late_minutes), 0) AS total
		FROM `tabEmployee Checkin`
		WHERE employee = %(emp)s
		  AND log_type = 'IN'
		  AND DATE(time) BETWEEN %(start)s AND %(end)s
		  AND custom_late_minutes > 0
	""", {"emp": emp.name, "start": month_start, "end": month_end}, as_dict=True)

	minutes = float(result[0].total) if result else 0
	if minutes <= 0:
		return

	amount = round(minutes * per_minute, 2)
	_upsert_deduction(
		employee=emp.name,
		component="Late Entry Deduction",
		amount=amount,
		payroll_date=month_end,
		company=emp.company,
		notes=f"Late Entry: {minutes:.0f} min × ₹{per_minute:.6f}/min = ₹{amount:.2f}"
	)


def _process_early_exit_deduction(emp, per_minute, month_start, month_end):
	result = frappe.db.sql("""
		SELECT COALESCE(SUM(custom_early_exit_minutes), 0) AS total
		FROM `tabEmployee Checkin`
		WHERE employee = %(emp)s
		  AND log_type = 'OUT'
		  AND DATE(time) BETWEEN %(start)s AND %(end)s
		  AND custom_early_exit_minutes > 0
	""", {"emp": emp.name, "start": month_start, "end": month_end}, as_dict=True)

	minutes = float(result[0].total) if result else 0
	if minutes <= 0:
		return

	amount = round(minutes * per_minute, 2)
	_upsert_deduction(
		employee=emp.name,
		component="Early Exit Deduction",
		amount=amount,
		payroll_date=month_end,
		company=emp.company,
		notes=f"Early Exit: {minutes:.0f} min × ₹{per_minute:.6f}/min = ₹{amount:.2f}"
	)


def _upsert_deduction(employee, component, amount, payroll_date, company, notes):
	"""
	Idempotent: cancel-and-recreate if a record already exists for this
	employee + component + payroll_date combination.
	Allows safe re-runs if checkin data is corrected later.
	"""
	existing = frappe.db.get_value(
		"Additional Salary",
		{
			"employee": employee,
			"salary_component": component,
			"payroll_date": payroll_date,
			"docstatus": ["!=", 2]
		},
		"name"
	)

	if existing:
		old = frappe.get_doc("Additional Salary", existing)
		if old.docstatus == 1:
			try:
				old.cancel()
			except frappe.LinkExistsError:
				# Already pulled into a submitted Salary Slip — leave it as-is
				frappe.logger("payroll").warning(
					f"Skipping upsert for {employee}/{component}: "
					f"{existing} is linked to a submitted Salary Slip"
				)
				return
		old.delete()

	doc = frappe.new_doc("Additional Salary")
	doc.employee = employee
	doc.salary_component = component
	doc.type = "Deduction"
	doc.amount = amount
	doc.payroll_date = payroll_date
	doc.company = company
	doc.insert(ignore_permissions=True)
	doc.submit()
