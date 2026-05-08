"""
BB Academy POC Demo Setup
=========================
Creates complete test data for payroll POC demonstration.

Usage (bench console):
----------------------
from bb_acadamy_admin.black_building_admin.payroll.demo_setup import run_poc_demo, create_salary_slips_demo

# Step 1 — Create all master data, checkins, leaves, deductions
result = run_poc_demo()
frappe.db.commit()

# Step 2 — Create and submit salary slips (triggers email)
create_salary_slips_demo(result["emp1"], result["emp2"])
frappe.db.commit()
"""

import frappe
from frappe.utils import (
	get_first_day, get_last_day, today, getdate, now_datetime
)
from datetime import datetime


# ─────────────────────────────────────────────
# DEMO CONSTANTS
# ─────────────────────────────────────────────

STRUCTURE_NAME = "BB Academy Staff Structure"
LEAVE_TYPE = "Casual Leave"
WORKING_DAYS = 26

EMPLOYEES = {
	"Preethi": {
		"in_time": "16:30:00",
		"out_time": "22:00:00",
		"grace": 5,
		"salary": 15000,
		"email": "preethi@blackbuilding.com",
	},
	"Saranya": {
		"in_time": "17:00:00",
		"out_time": "22:00:00",
		"grace": 5,
		"salary": 12000,
		"email": "saranya@blackbuilding.com",
	},
}

# ── Full-month (May 2026) checkin config ─────────────────────────
# leave_days : set of day numbers with no checkin (on leave)
# late        : {day: extra_minutes_past_expected_in}
# early       : {day: minutes_before_expected_out}
# All other days → exact expected IN / OUT times

CHECKIN_CONFIG = {
	"Preethi": {
		"in_time":    "16:30:00",
		"out_time":   "22:00:00",
		"leave_days": {5, 7},
		"late": {
			1: 15,  2: 30,  6: 10,  9: 25,
			14: 12, 19: 20, 21: 8,  27: 35, 30: 15,
		},
		"early": {
			1: 15,  2: 30,  9: 10,
			15: 15, 23: 20, 28: 10,
		},
	},
	"Saranya": {
		"in_time":    "17:00:00",
		"out_time":   "22:00:00",
		"leave_days": {12},
		"late": {
			1: 10,  2: 25,  6: 15,
			11: 20, 18: 30, 26: 10, 29: 10,
		},
		"early": {
			1: 10,  7: 5,
			15: 15, 23: 20,
		},
	},
}

# Leave dates — (from_date, to_date, label)
PREETHI_LEAVES = [
	("2026-05-05", "2026-05-05", "1st Leave — 1× deduction"),
	("2026-05-07", "2026-05-07", "2nd Leave — 2× deduction"),
]
SARANYA_LEAVES = [
	("2026-05-12", "2026-05-12", "1st Leave — 1× deduction"),
]


# ─────────────────────────────────────────────
# MAIN ENTRY POINTS
# ─────────────────────────────────────────────

def run_poc_demo():
	"""
	Idempotent full setup. Safe to run multiple times.
	Returns {"emp1": "HR-EMP-001", "emp2": "HR-EMP-002"}
	"""
	company = frappe.defaults.get_global_default("company")
	if not company:
		frappe.throw("No default company set. Go to ERPNext Settings and set a default company.")

	_banner("BB Academy POC Demo Setup")
	_log(f"Company: {company}")

	_log("\n[1/8] Salary Components")
	_setup_salary_components()

	_log("\n[2/8] Salary Structure")
	_setup_salary_structure(company)

	_log("\n[3/8] Test Employees")
	emp1 = _setup_employee("Preethi", company)
	emp2 = _setup_employee("Saranya", company)

	_log("\n[4/8] Salary Structure Assignments")
	_setup_salary_assignment(emp1, EMPLOYEES["Preethi"]["salary"], company)
	_setup_salary_assignment(emp2, EMPLOYEES["Saranya"]["salary"], company)
	_refresh_salary_rates(emp1)
	_refresh_salary_rates(emp2)

	_log("\n[5/8] Leave Allocations")
	_setup_leave_allocation(emp1, company)
	_setup_leave_allocation(emp2, company)

	_log("\n[6/8] Employee Checkins (Late + Early Exit)")
	_setup_checkins(emp1, emp2)

	_log("\n[7/8] Leave Applications")
	_setup_leaves(emp1, emp2, company)

	_log("\n[8/8] Monthly Attendance Deductions")
	from bb_acadamy_admin.black_building_admin.payroll.monthly import create_attendance_deductions
	result = create_attendance_deductions(month_date=today())
	_log(f"  Processed: {result['processed']} employees")

	frappe.db.commit()
	_print_demo_summary(emp1, emp2)

	return {"emp1": emp1, "emp2": emp2}


def create_salary_slips_demo(emp1=None, emp2=None):
	"""
	Creates and submits Salary Slips for both demo employees.
	Submission triggers the email hook automatically.

	Call after run_poc_demo() and frappe.db.commit().
	"""
	company = frappe.defaults.get_global_default("company")
	month_start = get_first_day(today())
	month_end = get_last_day(today())

	if not emp1:
		emp1 = frappe.db.get_value("Employee", {"employee_name": "Preethi Demo"}, "name")
	if not emp2:
		emp2 = frappe.db.get_value("Employee", {"employee_name": "Saranya Demo"}, "name")

	if not emp1 or not emp2:
		frappe.throw("Demo employees not found. Run run_poc_demo() first.")

	_ensure_fiscal_year(month_start, company)
	created_slips = []

	for emp in [emp1, emp2]:
		emp_doc = frappe.get_doc("Employee", emp)
		_log(f"\nProcessing: {emp_doc.employee_name}")

		existing = frappe.db.get_value("Salary Slip", {
			"employee": emp,
			"start_date": month_start,
			"end_date": month_end,
			"docstatus": ["!=", 2]
		}, "name")

		if existing:
			existing_doc = frappe.get_doc("Salary Slip", existing)
			_log(f"  Found existing slip: {existing} (status={existing_doc.docstatus})")
			if existing_doc.docstatus == 0:
				_log("  Submitting existing draft...")
				existing_doc.submit()
				frappe.db.commit()
			created_slips.append(existing)
			continue

		ss = frappe.new_doc("Salary Slip")
		ss.employee = emp
		ss.start_date = month_start
		ss.end_date = month_end
		ss.posting_date = today()
		ss.company = company
		ss.payroll_frequency = "Monthly"
		ss.flags.ignore_permissions = True
		ss.insert()

		# Patch: if gross_pay is 0 (happens when salary structure formula can't evaluate
		# because payment_days=0 or structure link is missing), directly inject Basic Pay
		# from the Salary Structure Assignment base amount.
		if float(ss.gross_pay or 0) == 0:
			base_amount = float(frappe.db.get_value(
				"Salary Structure Assignment",
				filters={"employee": emp, "docstatus": 1},
				fieldname="base",
				order_by="from_date desc"
			) or 0)

			if base_amount > 0:
				if ss.earnings:
					for row in ss.earnings:
						if row.salary_component == "Basic Pay":
							row.amount = base_amount
							row.default_amount = base_amount
				else:
					ss.append("earnings", {
						"salary_component": "Basic Pay",
						"abbr": "BP",
						"amount": base_amount,
						"default_amount": base_amount,
					})

				ss.gross_pay = base_amount
				ss.net_pay = base_amount - float(ss.total_deduction or 0)
				ss.base_gross_pay = base_amount
				ss.base_net_pay = ss.net_pay
				ss.rounded_total = round(float(ss.net_pay or 0))
				ss.flags.ignore_permissions = True
				ss.save(ignore_permissions=True)

		_log(f"  Slip: {ss.name}")
		_log(f"  Gross Pay      : ₹{float(ss.gross_pay or 0):>10,.2f}")
		_log(f"  Total Deduction: ₹{float(ss.total_deduction or 0):>10,.2f}")
		_log(f"  Net Pay        : ₹{float(ss.net_pay or 0):>10,.2f}")

		ss.submit()
		frappe.db.commit()
		_log(f"  ✓ Submitted. Email triggered to {emp_doc.employee_name} at {emp_doc.personal_email}")
		created_slips.append(ss.name)

	_banner("Salary Slips Created & Emails Sent")
	return created_slips


# ─────────────────────────────────────────────
# MASTER DATA SETUP
# ─────────────────────────────────────────────

def _setup_salary_components():
	components = [
		{"name": "Basic Pay",            "abbr": "BP",  "type": "Earning",   "is_payable": 1},
		{"name": "Late Entry Deduction", "abbr": "LED", "type": "Deduction", "is_payable": 0},
		{"name": "Early Exit Deduction", "abbr": "EED", "type": "Deduction", "is_payable": 0},
		{"name": "Leave Deduction",      "abbr": "LD",  "type": "Deduction", "is_payable": 0},
	]

	for comp in components:
		if frappe.db.exists("Salary Component", comp["name"]):
			_log(f"  ✓ Exists: {comp['name']}")
			continue

		doc = frappe.new_doc("Salary Component")
		doc.salary_component = comp["name"]
		doc.salary_component_abbr = comp["abbr"]
		doc.type = comp["type"]
		doc.is_payable = comp.get("is_payable", 0)
		doc.insert(ignore_permissions=True)
		_log(f"  + Created: {comp['name']}")


def _setup_salary_structure(company):
	if frappe.db.exists("Salary Structure", STRUCTURE_NAME):
		_log(f"  ✓ Exists: {STRUCTURE_NAME}")
		return

	ss = frappe.new_doc("Salary Structure")
	ss.name = STRUCTURE_NAME
	ss.company = company
	ss.payroll_frequency = "Monthly"
	ss.is_active = "Yes"
	ss.salary_slip_based_on_timesheet = 0

	ss.append("earnings", {
		"salary_component": "Basic Pay",
		"abbr": "BP",
		"formula": "base",
		"depends_on_payment_days": 0,
	})

	ss.insert(ignore_permissions=True)
	ss.submit()
	_log(f"  + Created and submitted: {STRUCTURE_NAME}")


# ─────────────────────────────────────────────
# EMPLOYEE SETUP
# ─────────────────────────────────────────────

def _setup_employee(first_name, company):
	emp_data = EMPLOYEES[first_name]
	full_name = f"{first_name} Demo"

	existing = frappe.db.get_value("Employee", {"employee_name": full_name}, "name")
	if existing:
		_log(f"  ✓ Exists: {full_name} ({existing})")
		return existing

	company_holiday_list = frappe.db.get_value("Company", company, "default_holiday_list") or ""

	emp = frappe.new_doc("Employee")
	emp.first_name = first_name
	emp.last_name = "Demo"
	emp.employee_name = full_name
	emp.company = company
	emp.gender = "Female"
	emp.date_of_joining = "2026-01-01"
	emp.status = "Active"
	emp.personal_email = emp_data["email"]
	emp.prefered_email = "Personal"
	emp.holiday_list = company_holiday_list
	emp.custom_expected_in_time = emp_data["in_time"]
	emp.custom_expected_out_time = emp_data["out_time"]
	emp.custom_grace_minutes = emp_data["grace"]
	emp.flags.ignore_mandatory = True
	emp.insert(ignore_permissions=True)

	_log(f"  + Created: {full_name} ({emp.name})")
	return emp.name


def _setup_salary_assignment(employee, base_amount, company):
	month_start = get_first_day(today())

	existing = frappe.db.get_value("Salary Structure Assignment", {
		"employee": employee,
		"salary_structure": STRUCTURE_NAME,
		"docstatus": 1
	}, "name")

	if existing:
		_log(f"  ✓ Assignment exists for {employee}")
		return

	ssa = frappe.new_doc("Salary Structure Assignment")
	ssa.employee = employee
	ssa.salary_structure = STRUCTURE_NAME
	ssa.from_date = "2026-01-01"
	ssa.base = base_amount
	ssa.company = company
	ssa.flags.ignore_permissions = True
	ssa.insert()
	ssa.submit()
	_log(f"  + Assigned {STRUCTURE_NAME} to {employee} at ₹{base_amount:,.0f}")


def _refresh_salary_rates(employee):
	"""Log the calculated salary rates (nothing stored — computed live from salary assignment)."""
	from bb_acadamy_admin.black_building_admin.payroll.employee import (
		get_per_day_salary, get_per_minute_salary
	)
	emp_name = frappe.db.get_value("Employee", employee, "employee_name")
	per_day = get_per_day_salary(employee)
	per_min = get_per_minute_salary(employee)
	_log(f"  ✓ {emp_name}: ₹{per_day:.2f}/day | ₹{per_min:.6f}/min")


# ─────────────────────────────────────────────
# LEAVE ALLOCATION
# ─────────────────────────────────────────────

def _setup_leave_allocation(employee, company):
	if not frappe.db.exists("Leave Type", LEAVE_TYPE):
		lt = frappe.new_doc("Leave Type")
		lt.leave_type_name = LEAVE_TYPE
		lt.max_leaves_allowed = 12
		lt.allow_negative = 1
		lt.is_lwp = 0
		lt.insert(ignore_permissions=True)
		_log(f"  + Created Leave Type: {LEAVE_TYPE}")

	existing = frappe.db.get_value("Leave Allocation", {
		"employee": employee,
		"leave_type": LEAVE_TYPE,
		"from_date": ["<=", today()],
		"to_date": [">=", today()],
		"docstatus": 1
	}, "name")

	if existing:
		_log(f"  ✓ Leave allocation exists for {employee}")
		return

	alloc = frappe.new_doc("Leave Allocation")
	alloc.employee = employee
	alloc.leave_type = LEAVE_TYPE
	alloc.from_date = "2026-01-01"
	alloc.to_date = "2026-12-31"
	alloc.new_leaves_allocated = 12
	alloc.company = company
	alloc.flags.ignore_permissions = True
	alloc.insert()
	alloc.submit()
	_log(f"  + Allocated 12 days {LEAVE_TYPE} to {employee}")


# ─────────────────────────────────────────────
# EMPLOYEE CHECKINS
# ─────────────────────────────────────────────

def add_full_month_checkins(emp1=None, emp2=None):
	"""
	Standalone: create full-month checkins + recalculate deductions.
	Safe to call at any time — skips records that already exist.

	bench console:
	  from bb_acadamy_admin.black_building_admin.payroll.demo_setup import add_full_month_checkins
	  add_full_month_checkins("HR-EMP-00014", "HR-EMP-00015")
	  frappe.db.commit()
	"""
	if not emp1:
		emp1 = frappe.db.get_value("Employee", {"employee_name": "Preethi Demo"}, "name")
	if not emp2:
		emp2 = frappe.db.get_value("Employee", {"employee_name": "Saranya Demo"}, "name")

	_log("\nAdding full-month checkins for May 2026...")
	_setup_checkins(emp1, emp2)

	_log("\nRecalculating monthly attendance deductions...")
	from bb_acadamy_admin.black_building_admin.payroll.monthly import create_attendance_deductions
	result = create_attendance_deductions(month_date=today())
	_log(f"  Done: {result}")
	frappe.db.commit()


def _setup_checkins(emp1, emp2):
	"""
	Creates Employee Checkin records for all 31 days of May 2026.
	Skips leave days. Idempotent — already-existing records are skipped.
	before_save hook fires on insert → auto-calculates late/early minutes.
	"""
	emp_map = {
		emp1: CHECKIN_CONFIG["Preethi"],
		emp2: CHECKIN_CONFIG["Saranya"],
	}

	for emp, cfg in emp_map.items():
		emp_name = frappe.db.get_value("Employee", emp, "employee_name")
		in_h, in_m = int(cfg["in_time"][:2]), int(cfg["in_time"][3:5])
		out_h, out_m = int(cfg["out_time"][:2]), int(cfg["out_time"][3:5])
		created = 0

		for day in range(1, 32):
			if day in cfg["leave_days"]:
				continue

			date_str = f"2026-05-{day:02d}"
			late_m  = cfg["late"].get(day, 0)
			early_m = cfg["early"].get(day, 0)

			# Calculate actual IN and OUT times
			in_total  = in_h  * 60 + in_m  + late_m
			out_total = out_h * 60 + out_m - early_m
			actual_in  = f"{in_total  // 60:02d}:{in_total  % 60:02d}:00"
			actual_out = f"{out_total // 60:02d}:{out_total % 60:02d}:00"

			for log_type, t_str in [("IN", actual_in), ("OUT", actual_out)]:
				dt_str = f"{date_str} {t_str}"
				if frappe.db.get_value("Employee Checkin",
					{"employee": emp, "time": dt_str, "log_type": log_type}, "name"):
					continue

				checkin = frappe.new_doc("Employee Checkin")
				checkin.employee = emp
				checkin.log_type = log_type
				checkin.time = dt_str
				checkin.flags.ignore_permissions = True
				checkin.insert()
				created += 1

			if late_m or early_m:
				_log(f"  {emp_name} {date_str}: late={late_m}min  early_exit={early_m}min")

		_log(f"  ✓ {emp_name}: {created} checkin records added (31 days - {len(cfg['leave_days'])} leave days)")


# ─────────────────────────────────────────────
# LEAVE APPLICATIONS
# ─────────────────────────────────────────────

def _setup_leaves(emp1, emp2, company):
	# Ensure both demo employees have a holiday list — Leave Application validation requires it.
	# Employees created with ignore_mandatory may be missing this even if Company has one set.
	company_holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")
	if company_holiday_list:
		for emp in [emp1, emp2]:
			if not frappe.db.get_value("Employee", emp, "holiday_list"):
				frappe.db.set_value("Employee", emp, "holiday_list", company_holiday_list)
				_log(f"  ✓ Holiday list patched on {emp}")
	else:
		frappe.throw(
			"No default Holiday List found on Company. "
			"Go to Company master → set 'Default Holiday List' and re-run."
		)

	leave_map = {
		emp1: PREETHI_LEAVES,
		emp2: SARANYA_LEAVES,
	}

	for emp, leaves in leave_map.items():
		emp_name = frappe.db.get_value("Employee", emp, "employee_name")

		for from_date, to_date, label in leaves:
			existing = frappe.db.get_value("Leave Application", {
				"employee": emp,
				"from_date": from_date,
				"to_date": to_date,
				"leave_type": LEAVE_TYPE,
				"docstatus": ["!=", 2]
			}, "name")

			if existing:
				_log(f"  ✓ Leave exists: {emp_name} on {from_date}")
				continue

			la = frappe.new_doc("Leave Application")
			la.employee = emp
			la.leave_type = LEAVE_TYPE
			la.from_date = from_date
			la.to_date = to_date
			la.status = "Approved"
			la.company = company
			la.posting_date = today()
			la.description = label
			la.flags.ignore_permissions = True
			la.flags.ignore_validate_maximum_allowed_leaves = True
			la.insert()
			# on_submit hook fires here → creates Additional Salary for leave deduction
			la.submit()
			_log(f"  + {emp_name} leave on {from_date} ({label}) → submitted")


# ─────────────────────────────────────────────
# DEMO SUMMARY PRINTER
# ─────────────────────────────────────────────

def _print_demo_summary(emp1, emp2):
	_banner("POC Setup Complete — Demo Summary")

	month_start = get_first_day(today())
	month_end = get_last_day(today())

	for emp in [emp1, emp2]:
		emp_doc = frappe.get_doc("Employee", emp)
		base = float(frappe.db.get_value("Salary Structure Assignment", {
			"employee": emp, "docstatus": 1
		}, "base") or 0)

		add_sals = frappe.get_all("Additional Salary", {
			"employee": emp,
			"payroll_date": ["between", [month_start, month_end]],
			"docstatus": 1
		}, ["salary_component", "amount"])

		total_ded = sum(float(r.amount) for r in add_sals)

		_log(f"\n  {emp_doc.employee_name} ({emp})")
		_log(f"  {'─' * 45}")
		_log(f"  Gross (Basic Pay)     : ₹{base:>10,.2f}")
		for r in add_sals:
			_log(f"  {r.salary_component:<22}: ₹{float(r.amount):>10,.2f}")
		_log(f"  {'─' * 45}")
		_log(f"  Total Deductions      : ₹{total_ded:>10,.2f}")
		_log(f"  Estimated Net Pay     : ₹{base - total_ded:>10,.2f}")

	_log("\nNEXT STEP:")
	_log("  create_salary_slips_demo(result['emp1'], result['emp2'])")
	_log("  This creates Salary Slips and sends email to each employee.\n")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _ensure_fiscal_year(reference_date, company):
	"""Create a Fiscal Year covering reference_date if none exists."""
	exists = frappe.db.sql("""
		SELECT fy.name FROM `tabFiscal Year` fy
		INNER JOIN `tabFiscal Year Company` fyc ON fyc.parent = fy.name
		WHERE fyc.company = %s
		  AND fy.year_start_date <= %s
		  AND fy.year_end_date   >= %s
		LIMIT 1
	""", (company, reference_date, reference_date))

	if exists:
		return

	year = getdate(reference_date).year
	fy = frappe.new_doc("Fiscal Year")
	fy.year = str(year)
	fy.year_start_date = f"{year}-01-01"
	fy.year_end_date = f"{year}-12-31"
	fy.append("companies", {"company": company})
	fy.insert(ignore_permissions=True)
	frappe.db.commit()
	_log(f"  ✓ Fiscal Year {year} created automatically")


def _log(msg):
	print(msg)
	frappe.logger("demo_setup").info(msg)


def _banner(title):
	line = "=" * 55
	_log(f"\n{line}")
	_log(f"  {title}")
	_log(line)
