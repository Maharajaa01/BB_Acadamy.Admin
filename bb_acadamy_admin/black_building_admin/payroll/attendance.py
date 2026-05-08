import frappe
from datetime import datetime, timedelta
from frappe.utils import get_datetime


def calculate_attendance_deviation(doc, method=None):
	"""
	Compute late_minutes (log_type=IN) or early_exit_minutes (log_type=OUT)
	against the employee's custom expected times.
	Triggered: Employee Checkin → Before Save
	"""
	if not doc.employee or not doc.time or not doc.log_type:
		return

	employee = frappe.get_cached_doc("Employee", doc.employee)

	if not employee.custom_expected_in_time or not employee.custom_expected_out_time:
		frappe.msgprint(
			f"Expected timings not configured for {employee.employee_name}. "
			"Skipping late/early calculation.",
			alert=True
		)
		return

	checkin_dt = get_datetime(doc.time)
	checkin_date = checkin_dt.date()

	in_td = _to_timedelta(employee.custom_expected_in_time)
	out_td = _to_timedelta(employee.custom_expected_out_time)

	expected_in_dt = datetime.combine(checkin_date, _td_to_time(in_td))
	expected_out_dt = datetime.combine(checkin_date, _td_to_time(out_td))

	if doc.log_type == "IN":
		grace_minutes = int(employee.custom_grace_minutes or 0)
		allowed_in_dt = expected_in_dt + timedelta(minutes=grace_minutes)

		if checkin_dt > allowed_in_dt:
			late_mins = (checkin_dt - expected_in_dt).seconds / 60
			doc.custom_late_minutes = round(late_mins, 2)
		else:
			doc.custom_late_minutes = 0

		doc.custom_early_exit_minutes = 0

	elif doc.log_type == "OUT":
		if checkin_dt < expected_out_dt:
			early_mins = (expected_out_dt - checkin_dt).seconds / 60
			doc.custom_early_exit_minutes = round(early_mins, 2)
		else:
			doc.custom_early_exit_minutes = 0

		doc.custom_late_minutes = 0


def _to_timedelta(val):
	if isinstance(val, timedelta):
		return val
	if isinstance(val, str):
		parts = val.split(":")
		h, m = int(parts[0]), int(parts[1])
		s = int(parts[2]) if len(parts) > 2 else 0
		return timedelta(hours=h, minutes=m, seconds=s)
	raise ValueError(f"Unsupported time type: {type(val)}")


def _td_to_time(td):
	total_seconds = int(td.total_seconds())
	return datetime.min.replace(
		hour=total_seconds // 3600,
		minute=(total_seconds % 3600) // 60,
		second=total_seconds % 60
	).time()
