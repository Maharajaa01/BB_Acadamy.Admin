import frappe
from datetime import timedelta


WORKING_DAYS_PER_MONTH = 26


def calculate_salary_rates(doc, method=None):
	"""
	Updates the display-only working_hours field on Employee.
	per_day_salary and per_minute_salary are NOT stored — calculated on-the-fly
	wherever they are needed (leave.py, monthly.py).
	Triggered: Employee → Before Save
	"""
	if not doc.custom_expected_in_time or not doc.custom_expected_out_time:
		return

	in_td = _to_timedelta(doc.custom_expected_in_time)
	out_td = _to_timedelta(doc.custom_expected_out_time)

	if out_td <= in_td:
		frappe.throw("Expected Out Time must be later than Expected In Time.")

	working_minutes = (out_td - in_td).seconds / 60
	working_hours = round(working_minutes / 60, 2)

	# Only set fields that actually exist on this Employee
	for field in ("custom_working_hours_", "custom_working_hours"):
		if hasattr(doc, field):
			setattr(doc, field, working_hours)
			break


def get_per_day_salary(employee):
	"""
	Calculate per-day salary on the fly.
	= monthly_salary / WORKING_DAYS_PER_MONTH
	Used by leave.py and any other deduction logic.
	"""
	monthly = _get_monthly_salary(employee)
	if not monthly:
		return 0
	return round(float(monthly) / WORKING_DAYS_PER_MONTH, 4)


def get_per_minute_salary(employee):
	"""
	Calculate per-minute salary on the fly.
	= monthly_salary / (working_hours_per_day × 60 × WORKING_DAYS_PER_MONTH)
	Used by monthly.py for late/early-exit deductions.
	"""
	monthly = _get_monthly_salary(employee)
	if not monthly:
		return 0

	in_time = frappe.db.get_value("Employee", employee, "custom_expected_in_time")
	out_time = frappe.db.get_value("Employee", employee, "custom_expected_out_time")
	if not in_time or not out_time:
		return 0

	in_td = _to_timedelta(in_time)
	out_td = _to_timedelta(out_time)
	if out_td <= in_td:
		return 0

	working_minutes_per_day = (out_td - in_td).seconds / 60
	total_monthly_minutes = working_minutes_per_day * WORKING_DAYS_PER_MONTH

	return round(float(monthly) / total_monthly_minutes, 6) if total_monthly_minutes > 0 else 0


def _get_monthly_salary(employee):
	return frappe.db.get_value(
		"Salary Structure Assignment",
		filters={"employee": employee, "docstatus": 1},
		fieldname="base",
		order_by="from_date desc"
	) or 0


def _to_timedelta(val):
	if isinstance(val, timedelta):
		return val
	if isinstance(val, str):
		parts = val.split(":")
		h, m = int(parts[0]), int(parts[1])
		s = int(parts[2]) if len(parts) > 2 else 0
		return timedelta(hours=h, minutes=m, seconds=s)
	raise ValueError(f"Cannot convert {type(val)} to timedelta")
