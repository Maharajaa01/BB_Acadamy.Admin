# Copyright (c) 2026, Maha Raja and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Update Students Application Form chart to display inquiries by standard as bar chart"""
	try:
		# Check if the chart exists
		if not frappe.db.exists("Dashboard Chart", "Students Application Form"):
			return
		
		# Get the chart document
		chart = frappe.get_doc("Dashboard Chart", "Students Application Form")
		
		# Update chart configuration
		chart.based_on = "standard"
		chart.value_based_on = "name"
		chart.group_by_type = "Count"
		chart.type = "Bar"
		chart.timeseries = 0
		chart.timespan = None
		chart.time_interval = None
		chart.show_values_over_chart = 1
		
		# Save the updated chart
		chart.save()
		
		frappe.msgprint("Dashboard Chart 'Students Application Form' has been updated successfully!")
		
	except Exception as e:
		frappe.log_error(f"Error updating Dashboard Chart: {str(e)}")
		frappe.msgprint(f"Error updating chart: {str(e)}", alert=True)
