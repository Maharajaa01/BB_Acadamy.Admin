"""Mobile-friendly API endpoints for the BB Academy HRMS Flutter app.

These methods aggregate data so the mobile client can render screens with
fewer round-trips than the standard Frappe REST endpoints would require.

All endpoints require an authenticated session (no `allow_guest=True`).
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, nowdate, today


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_employee() -> dict[str, Any]:
    """Resolve the Employee row tied to the logged-in user.

    Raises a 404 if the logged-in user has no Employee record. The mobile app
    is intended for staff only, so this is the correct failure mode.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    employee_name = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee_name:
        frappe.throw(
            _("No employee profile is linked to user {0}").format(user),
            frappe.DoesNotExistError,
        )

    employee = frappe.get_doc("Employee", employee_name)
    return employee.as_dict()


def _user_roles(user: str) -> list[str]:
    return [r.role for r in frappe.get_roles(user)]


def _is_hr(user: str | None = None) -> bool:
    user = user or frappe.session.user
    roles = set(_user_roles(user))
    return bool({"HR Manager", "HR User", "System Manager", "Administrator"} & roles)


def _ensure_hr() -> None:
    if not _is_hr():
        frappe.throw(_("HR access required"), frappe.PermissionError)


def _to_minutes(d: timedelta | None) -> int:
    if not d:
        return 0
    return int(d.total_seconds() // 60)


def _today_checkins(employee: str) -> list[Any]:
    return frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [f"{today()} 00:00:00", f"{today()} 23:59:59"]],
        },
        fields=[
            "name",
            "log_type",
            "time",
            "custom_late_minutes",
            "custom_early_exit_minutes",
        ],
        order_by="time asc",
    )


# ---------------------------------------------------------------------------
# Auth / profile
# ---------------------------------------------------------------------------

@frappe.whitelist()
def me() -> dict[str, Any]:
    """Return the current logged-in user enriched with employee fields."""
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Authentication required"), frappe.AuthenticationError)

    user_doc = frappe.get_cached_doc("User", user)
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        [
            "name",
            "employee_name",
            "designation",
            "department",
            "image",
            "holiday_list",
        ],
        as_dict=True,
    ) or {}

    return {
        "username": user,
        "email": user_doc.email or user,
        "full_name": user_doc.full_name or employee.get("employee_name") or user,
        "image": employee.get("image") or user_doc.user_image or "",
        "employee": employee.get("name", ""),
        "employee_name": employee.get("employee_name", ""),
        "designation": employee.get("designation", ""),
        "department": employee.get("department", ""),
        "holiday_list": employee.get("holiday_list", ""),
        "roles": _user_roles(user),
    }


# ---------------------------------------------------------------------------
# Employee dashboard
# ---------------------------------------------------------------------------

@frappe.whitelist()
def employee_dashboard() -> dict[str, Any]:
    """Aggregated payload for the employee home screen."""
    employee = _current_employee()

    checkins = _today_checkins(employee["name"])
    in_checkin = next((c for c in checkins if c.log_type == "IN"), None)
    out_checkin = next((c for c in reversed(checkins) if c.log_type == "OUT"), None)

    worked_minutes = 0
    if in_checkin:
        end = get_datetime(out_checkin.time) if out_checkin else datetime.now()
        worked_minutes = _to_minutes(end - get_datetime(in_checkin.time))

    today_attendance = frappe.db.get_value(
        "Attendance",
        {"employee": employee["name"], "attendance_date": today()},
        ["status", "leave_type"],
        as_dict=True,
    )

    if today_attendance and today_attendance.status == "On Leave":
        attendance_status = "on_leave"
    elif out_checkin:
        attendance_status = "completed"
    elif in_checkin:
        attendance_status = "working"
    else:
        attendance_status = "not_checked_in"

    pending_tasks = frappe.db.count(
        "Task",
        filters={
            "_assign": ("like", f"%{frappe.session.user}%"),
            "status": ("in", ("Open", "Working", "Pending Review")),
        },
    )

    open_leaves = frappe.db.count(
        "Leave Application",
        filters={"employee": employee["name"], "status": "Open"},
    )

    leave_balance = frappe.db.sql(
        """
        SELECT COALESCE(SUM(leaves), 0)
        FROM `tabLeave Allocation`
        WHERE employee = %s
          AND from_date <= %s AND to_date >= %s
        """,
        (employee["name"], today(), today()),
    )
    leave_balance = flt(leave_balance[0][0]) if leave_balance else 0.0

    upcoming_holiday = None
    if employee.get("holiday_list"):
        row = frappe.db.sql(
            """
            SELECT holiday_date, description
            FROM `tabHoliday`
            WHERE parent = %s AND weekly_off = 0 AND holiday_date >= %s
            ORDER BY holiday_date ASC LIMIT 1
            """,
            (employee["holiday_list"], today()),
            as_dict=True,
        )
        if row:
            upcoming_holiday = {
                "holiday_date": str(row[0].holiday_date),
                "description": row[0].description,
            }

    return {
        "attendance_status": attendance_status,
        "check_in_time": str(in_checkin.time) if in_checkin else None,
        "check_out_time": str(out_checkin.time) if out_checkin else None,
        "late_minutes": flt(in_checkin.custom_late_minutes) if in_checkin else 0,
        "early_exit_minutes": flt(out_checkin.custom_early_exit_minutes) if out_checkin else 0,
        "worked_minutes": worked_minutes,
        "pending_tasks": pending_tasks,
        "open_leaves": open_leaves,
        "leave_balance": leave_balance,
        "upcoming_holiday": upcoming_holiday,
    }


# ---------------------------------------------------------------------------
# HR dashboard
# ---------------------------------------------------------------------------

@frappe.whitelist()
def hr_dashboard() -> dict[str, Any]:
    _ensure_hr()
    today_str = today()

    total_employees = frappe.db.count("Employee", filters={"status": "Active"})

    attendance_rows = frappe.db.sql(
        """
        SELECT status, COUNT(*) AS c
        FROM `tabAttendance`
        WHERE attendance_date = %s
        GROUP BY status
        """,
        (today_str,),
        as_dict=True,
    )
    by_status = {r.status: int(r.c) for r in attendance_rows}

    late_today = frappe.db.count(
        "Employee Checkin",
        filters={
            "log_type": "IN",
            "time": ["between", [f"{today_str} 00:00:00", f"{today_str} 23:59:59"]],
            "custom_late_minutes": [">", 0],
        },
    )

    pending_leave_approvals = frappe.db.count(
        "Leave Application", filters={"status": "Open"}
    )
    open_tasks = frappe.db.count(
        "Task", filters={"status": ("in", ("Open", "Working", "Pending Review"))}
    )

    payroll_total = frappe.db.sql(
        """
        SELECT COALESCE(SUM(net_pay), 0)
        FROM `tabSalary Slip`
        WHERE start_date >= %s
        """,
        (today_str[:7] + "-01",),
    )
    payroll_total = flt(payroll_total[0][0]) if payroll_total else 0.0

    activity = _recent_activity()

    return {
        "total_employees": total_employees,
        "present_today": by_status.get("Present", 0),
        "late_today": late_today,
        "absent_today": by_status.get("Absent", 0),
        "on_leave_today": by_status.get("On Leave", 0),
        "pending_leave_approvals": pending_leave_approvals,
        "open_tasks": open_tasks,
        "payroll_total": payroll_total,
        "recent_activity": activity,
    }


def _recent_activity(limit: int = 8) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    checkins = frappe.get_all(
        "Employee Checkin",
        fields=["employee", "employee_name", "log_type", "time"],
        order_by="time desc",
        limit=limit,
    )
    for c in checkins:
        items.append(
            {
                "employee": c.employee,
                "employee_name": c.employee_name,
                "kind": "checkin" if c.log_type == "IN" else "checkout",
                "message": f"{'Checked in' if c.log_type == 'IN' else 'Checked out'} at {c.time.strftime('%I:%M %p')}",
                "time": c.time.isoformat(),
            }
        )

    leaves = frappe.get_all(
        "Leave Application",
        fields=["employee", "employee_name", "leave_type", "from_date", "creation"],
        order_by="creation desc",
        limit=limit,
    )
    for l in leaves:
        items.append(
            {
                "employee": l.employee,
                "employee_name": l.employee_name,
                "kind": "leave_applied",
                "message": f"Applied for {l.leave_type} from {l.from_date}",
                "time": l.creation.isoformat(),
            }
        )

    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:limit]


# ---------------------------------------------------------------------------
# Check-in / check-out
# ---------------------------------------------------------------------------

@frappe.whitelist(methods=["POST"])
def check_in(latitude: float | None = None, longitude: float | None = None,
             time: str | None = None) -> dict[str, Any]:
    return _create_checkin("IN", latitude=latitude, longitude=longitude, log_time=time)


@frappe.whitelist(methods=["POST"])
def check_out(latitude: float | None = None, longitude: float | None = None,
              time: str | None = None) -> dict[str, Any]:
    return _create_checkin("OUT", latitude=latitude, longitude=longitude, log_time=time)


def _create_checkin(log_type: str, latitude: float | None, longitude: float | None,
                    log_time: str | None) -> dict[str, Any]:
    employee = _current_employee()

    log_dt = get_datetime(log_time) if log_time else datetime.now()

    checkin = frappe.get_doc(
        {
            "doctype": "Employee Checkin",
            "employee": employee["name"],
            "log_type": log_type,
            "time": log_dt,
            "device_id": "MobileApp",
            "latitude": latitude,
            "longitude": longitude,
        }
    )
    checkin.flags.ignore_permissions = False
    checkin.insert()

    return {
        "name": checkin.name,
        "log_type": checkin.log_type,
        "time": str(checkin.time),
        "late_minutes": flt(checkin.get("custom_late_minutes", 0)),
        "early_exit_minutes": flt(checkin.get("custom_early_exit_minutes", 0)),
    }


@frappe.whitelist()
def today_checkin_status() -> dict[str, Any]:
    employee = _current_employee()
    rows = _today_checkins(employee["name"])
    in_row = next((c for c in rows if c.log_type == "IN"), None)
    out_row = next((c for c in reversed(rows) if c.log_type == "OUT"), None)
    return {
        "in_time": str(in_row.time) if in_row else None,
        "out_time": str(out_row.time) if out_row else None,
        "late_minutes": flt(in_row.custom_late_minutes) if in_row else 0,
        "early_exit_minutes": flt(out_row.custom_early_exit_minutes) if out_row else 0,
    }


# ---------------------------------------------------------------------------
# Attendance calendar
# ---------------------------------------------------------------------------

@frappe.whitelist()
def monthly_attendance(year: int, month: int) -> dict[str, Any]:
    employee = _current_employee()
    year, month = int(year), int(month)

    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)

    attendance_rows = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee["name"],
            "attendance_date": ["between", [start, end]],
        },
        fields=[
            "attendance_date",
            "status",
            "in_time",
            "out_time",
            "late_entry",
            "early_exit",
            "working_hours",
            "leave_type",
        ],
    )
    by_date = {a.attendance_date: a for a in attendance_rows}

    holiday_list = employee.get("holiday_list")
    holiday_dates: dict[date, str] = {}
    weekly_off_dates: set[date] = set()
    if holiday_list:
        rows = frappe.db.sql(
            """
            SELECT holiday_date, description, weekly_off
            FROM `tabHoliday`
            WHERE parent = %s AND holiday_date BETWEEN %s AND %s
            """,
            (holiday_list, start, end),
            as_dict=True,
        )
        for h in rows:
            holiday_dates[h.holiday_date] = h.description
            if h.weekly_off:
                weekly_off_dates.add(h.holiday_date)

    days = []
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        att = by_date.get(d)
        mark = "none"
        in_time = out_time = None
        late = early = working = 0.0
        note = ""

        if att:
            late = flt(att.late_entry)
            early = flt(att.early_exit)
            working = flt(att.working_hours)
            in_time = att.in_time
            out_time = att.out_time
            if att.status == "Present":
                mark = "late" if late else "present"
            elif att.status == "On Leave":
                mark = "on_leave"
                note = att.leave_type or "On leave"
            elif att.status == "Half Day":
                mark = "half_day"
            elif att.status == "Absent":
                mark = "absent"

        if mark == "none" and d in holiday_dates:
            mark = "weekly_off" if d in weekly_off_dates else "holiday"
            note = holiday_dates[d]

        days.append(
            {
                "date": str(d),
                "mark": mark,
                "check_in": str(in_time) if in_time else None,
                "check_out": str(out_time) if out_time else None,
                "late_minutes": late,
                "early_exit_minutes": early,
                "working_hours": working,
                "note": note,
            }
        )

    summary = {
        "total_present": sum(1 for x in days if x["mark"] in ("present", "late")),
        "total_late": sum(1 for x in days if x["mark"] == "late"),
        "total_absent": sum(1 for x in days if x["mark"] == "absent"),
        "total_leaves": sum(1 for x in days if x["mark"] == "on_leave"),
        "total_holidays": sum(1 for x in days if x["mark"] == "holiday"),
        "total_early_exits": sum(1 for x in days if x["early_exit_minutes"] > 0),
        "working_hours": sum(x["working_hours"] for x in days),
    }

    return {"summary": summary, "days": days}


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------

@frappe.whitelist()
def leave_balance() -> list[dict[str, Any]]:
    employee = _current_employee()

    rows = frappe.db.sql(
        """
        SELECT leave_type, SUM(leaves) AS balance
        FROM `tabLeave Allocation`
        WHERE employee = %s
          AND from_date <= %s AND to_date >= %s
          AND docstatus = 1
        GROUP BY leave_type
        """,
        (employee["name"], today(), today()),
        as_dict=True,
    )
    return [
        {"leave_type": r.leave_type, "balance": flt(r.balance)}
        for r in rows
    ]


@frappe.whitelist(methods=["POST"])
def apply_leave(leave_type: str, from_date: str, to_date: str,
                description: str = "", half_day: int = 0) -> dict[str, Any]:
    employee = _current_employee()

    leave = frappe.get_doc(
        {
            "doctype": "Leave Application",
            "employee": employee["name"],
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "description": description,
            "half_day": int(half_day),
            "status": "Open",
            "posting_date": nowdate(),
        }
    )
    leave.insert()
    return {"name": leave.name, "status": leave.status}


@frappe.whitelist(methods=["POST"])
def approve_leave(name: str, status: str, note: str = "") -> dict[str, Any]:
    _ensure_hr()
    if status not in ("Approved", "Rejected"):
        frappe.throw(_("status must be Approved or Rejected"))

    leave = frappe.get_doc("Leave Application", name)
    leave.status = status
    if note:
        leave.add_comment("Comment", note)
    leave.save()
    if status == "Approved":
        try:
            leave.submit()
        except Exception:
            # Some site setups submit on save via workflow.
            frappe.db.commit()
    return {"name": leave.name, "status": leave.status}


# ---------------------------------------------------------------------------
# Salary slip
# ---------------------------------------------------------------------------

@frappe.whitelist()
def my_salary_slips() -> list[dict[str, Any]]:
    employee = _current_employee()

    slips = frappe.get_all(
        "Salary Slip",
        filters={"employee": employee["name"], "docstatus": ("!=", 2)},
        fields=[
            "name",
            "employee_name",
            "start_date",
            "end_date",
            "gross_pay",
            "total_deduction",
            "net_pay",
            "payroll_frequency",
            "status",
        ],
        order_by="start_date desc",
        limit_page_length=24,
    )
    return [dict(s) for s in slips]


@frappe.whitelist()
def salary_slip_detail(name: str) -> dict[str, Any]:
    employee = _current_employee()
    slip = frappe.get_doc("Salary Slip", name)
    if slip.employee != employee["name"] and not _is_hr():
        frappe.throw(_("Not allowed"), frappe.PermissionError)

    return {
        "name": slip.name,
        "employee_name": slip.employee_name,
        "start_date": str(slip.start_date),
        "end_date": str(slip.end_date),
        "gross_pay": flt(slip.gross_pay),
        "total_deduction": flt(slip.total_deduction),
        "net_pay": flt(slip.net_pay),
        "payroll_frequency": slip.payroll_frequency,
        "status": slip.status,
        "earnings": [
            {"salary_component": e.salary_component, "amount": flt(e.amount)}
            for e in (slip.earnings or [])
        ],
        "deductions": [
            {"salary_component": d.salary_component, "amount": flt(d.amount)}
            for d in (slip.deductions or [])
        ],
    }
