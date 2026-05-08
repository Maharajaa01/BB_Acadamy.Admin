app_name = "bb_acadamy_admin"
app_title = "Black Building Admin "
app_publisher = "Maha Raja"
app_description = "This App used for Black Building Tution Center to Manage their Staff and Students "
app_email = "maharajab.tech@gmail.com"
app_license = "mit"

# Fixtures
# ------------------
fixtures = [
    {
        "doctype": "Dashboard Chart",
        "filters": {
            "name": "Students Application Form"
        }
    }
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "bb_acadamy_admin",
# 		"logo": "/assets/bb_acadamy_admin/logo.png",
# 		"title": "Black Building Admin ",
# 		"route": "/bb_acadamy_admin",
# 		"has_permission": "bb_acadamy_admin.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/bb_acadamy_admin/css/bb_acadamy_admin.css"
# app_include_js = "/assets/bb_acadamy_admin/js/bb_acadamy_admin.js"

# include js, css files in header of web template
# web_include_css = "/assets/bb_acadamy_admin/css/bb_acadamy_admin.css"
# web_include_js = "/assets/bb_acadamy_admin/js/bb_acadamy_admin.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "bb_acadamy_admin/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "bb_acadamy_admin/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "bb_acadamy_admin.utils.jinja_methods",
# 	"filters": "bb_acadamy_admin.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "bb_acadamy_admin.install.before_install"
# after_install = "bb_acadamy_admin.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "bb_acadamy_admin.uninstall.before_uninstall"
# after_uninstall = "bb_acadamy_admin.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "bb_acadamy_admin.utils.before_app_install"
# after_app_install = "bb_acadamy_admin.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "bb_acadamy_admin.utils.before_app_uninstall"
# after_app_uninstall = "bb_acadamy_admin.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bb_acadamy_admin.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Employee Checkin": {
        "before_save": "bb_acadamy_admin.black_building_admin.payroll.attendance.calculate_attendance_deviation"
    },
    "Employee": {
        "before_save": "bb_acadamy_admin.black_building_admin.payroll.employee.calculate_salary_rates"
    },
    "Leave Application": {
        "on_submit": "bb_acadamy_admin.black_building_admin.payroll.leave.create_leave_deduction",
        "on_cancel": "bb_acadamy_admin.black_building_admin.payroll.leave.cancel_leave_deduction"
    },
    "Salary Slip": {
        "on_submit": "bb_acadamy_admin.black_building_admin.payroll.salary_slip_email.send_salary_slip_email"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    # Runs on the 28th of every month — gives 2-3 days buffer before payroll
    "cron": {
        "0 9 28 * *": [
            "bb_acadamy_admin.black_building_admin.payroll.monthly.create_attendance_deductions"
        ]
    }
}

# Testing
# -------

# before_tests = "bb_acadamy_admin.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "bb_acadamy_admin.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "bb_acadamy_admin.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["bb_acadamy_admin.utils.before_request"]
# after_request = ["bb_acadamy_admin.utils.after_request"]

# Job Events
# ----------
# before_job = ["bb_acadamy_admin.utils.before_job"]
# after_job = ["bb_acadamy_admin.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"bb_acadamy_admin.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


website_route_rules = [{'from_route': '/BB_Academy_Dashboard/<path:app_path>', 'to_route': 'BB_Academy_Dashboard'},]