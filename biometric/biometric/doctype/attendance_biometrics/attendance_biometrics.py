import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from datetime import datetime
class AttendanceBiometrics(Document):
    def after_insert(self):
        try:
            # Fetch Biometric Settings
            settings = frappe.get_single("Biometric Settings")
            if not hasattr(self, 'devicecode'):
                frappe.throw(_("Device Code is missing from Attendance Biometric document"))
            if not self.logdatetime:
                raise ValueError("logdatetime is missing or empty in Attendance Biometric document.")
            # Fetch employees based on attendance_device_id
            employee_ids = frappe.get_all("Employee", filters={"attendance_device_id": self.devicecode}, fields=["name", "attendance_device_id"])
            # Handle no employee found case
            if not employee_ids:
                no_employee_msg = f"No employees found with attendance_device_id: {self.devicecode}"
                frappe.get_doc({
                    "doctype": "Attendance Biometric Error Log",
                    "title": "No Employee Found",
                    "time_stamp": now_datetime(),
                    "details": no_employee_msg
                }).insert(ignore_permissions=True)
                frappe.log_error(no_employee_msg, "AttendanceBiometric No Employee Found")
                return  # Exit the function gracefully
            success_log_entries = []  # To track successful operations
            # Process each employee
            for employee in employee_ids:
                try:
                    logdatetime = datetime.strptime(self.logdatetime, "%Y-%m-%d %H:%M:%S")
                except ValueError as e:
                    frappe.get_doc({
                        "doctype": "Biometric Error Log",
                        "title": "Error in AttendanceBiometric after_insert",
                        "time_stamp": now_datetime(),
                        "details": f"Error parsing logdatetime: {str(e)} - logdatetime value: '{self.logdatetime}'"
                    }).insert(ignore_permissions=True)
                    frappe.log_error(f"Error parsing logdatetime: {str(e)} - logdatetime value: '{self.logdatetime}'", "AttendanceBiometric Error")
                    raise
                log_type = "IN" if logdatetime.hour < 12 else "OUT"
                # Insert Employee Checkin
                if settings.employee_checkin:
                    frappe.get_doc({
                        "doctype": "Employee Checkin",
                        "employee": employee['name'],
                        "time": self.logdatetime,
                        "log_type": log_type,
                        "attendance_biometric": self.name
                    }).insert(ignore_permissions=True)
                    success_log_entries.append(f"Employee Checkin created for employee {employee['name']}")
                # Insert Attendance
                if settings.attendance:
                    frappe.get_doc({
                        "doctype": "Attendance",
                        "employee": employee['name'],
                        "attendance_date": self.logdatetime,
                        "status": "Present",
                        "attendance_biometric": self.name
                    }).insert(ignore_permissions=True)
                    success_log_entries.append(f"Attendance record created for employee {employee['name']}")
                # Insert Attendance Request
                if settings.attendance_request:
                    frappe.get_doc({
                        "doctype": "Attendance Request",
                        "employee": employee['name'],
                        "from_date": self.logdatetime,
                        "to_date": self.logdatetime,
                        "reason": "Auto-created by Attendance Biometric",
                        "status": "Open",
                        "attendance_biometric": self.name
                    }).insert(ignore_permissions=True)
                    success_log_entries.append(f"Attendance Request created for employee {employee['name']}")
            # Log success message
            if success_log_entries:
                frappe.get_doc({
                    "doctype": "Biometric Success Log",
                    "title": "Success in AttendanceBiometric after_insert",
                    "time_stamp": now_datetime(),
                    "details": "\n".join(success_log_entries)
                }).insert(ignore_permissions=True)
        except Exception as e:
            # Log error message
            frappe.get_doc({
                "doctype": "Attendance Biometric Error Log",
                "title": "Error in AttendanceBiometric after_insert",
                "time_stamp": now_datetime(),
                "details": str(e)
            }).insert(ignore_permissions=True)
            frappe.db.rollback()
            frappe.db.commit()
            frappe.log_error(f"Error in AttendanceBiometric after_insert: {str(e)}", "AttendanceBiometric Error")
            raise