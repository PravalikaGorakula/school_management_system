from datetime import date, datetime, time, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from academic_calendar.models import AcademicCalendarEvent
from academics.models import (
	ClassSection,
	Subject,
	SubjectEmployeeAssignment,
	TimetableEntry,
)
from admissions.models import (
	ParentStudent,
	StudentAdmissionApplication,
	StudentCredential,
)
from leave_management.models import LeaveRequest
from notifications.models import Notification

from .models import (
	AttendanceCorrection,
	AttendanceParentNotification,
	AttendanceSession,
	EmployeeAttendance,
	StudentAttendance,
)
from .services import (
	SYSTEM_ABSENCE_PREFIX,
	employee_attendance_summary,
	holiday_details,
	process_daily_attendance,
	student_attendance_summary,
)


class TeacherAttendanceWorkflowTests(TestCase):
	def setUp(self):
		self.teacher = self.create_user("teacher", "teacher")
		self.other_teacher = self.create_user("other-teacher", "teacher")
		self.principal = self.create_user("principal", "principal")
		self.parent = self.create_user("parent", "parent")

		self.class_section = ClassSection.objects.create(
			grade="5",
			section="A",
			academic_year="2026-2027",
		)
		self.subject = Subject.objects.create(
			subject_name="Mathematics",
			subject_code="MATH-5A",
		)
		SubjectEmployeeAssignment.objects.create(
			employee=self.teacher,
			class_section=self.class_section,
			subject=self.subject,
			academic_year=self.class_section.academic_year,
			is_active=True,
		)
		self.students = [
			self.create_student("STU-001", "Ada"),
			self.create_student("STU-002", "Linus"),
		]
		self.attendance_date = timezone.localdate()
		self.teacher_client = self.client
		self.teacher_client.force_login(self.teacher)

	def create_user(self, username, role):
		user = User.objects.create_user(username=username, password="test-pass")
		user.profile.role = role
		user.profile.save(update_fields=["role"])
		return user

	def create_student(self, application_id, first_name):
		return StudentAdmissionApplication.objects.create(
			application_id=application_id,
			first_name=first_name,
			last_name="Student",
			date_of_birth=date(2015, 1, 1),
			gender="other",
			phone="9000000000",
			address="School address",
			father_name="Parent One",
			mother_name="Parent Two",
			parent_phone="9000000001",
			applying_class="5",
			class_section=self.class_section,
			status="account_created",
		)

	def teacher_post(self, action, statuses):
		data = {
			"action": action,
			"class_section": self.class_section.pk,
			"subject": self.subject.pk,
			"date": self.attendance_date.isoformat(),
		}
		data.update(
			{f"status_{student.pk}": status for student, status in statuses.items()}
		)
		return self.teacher_client.post(reverse("attendance:teacher_attendance"), data)

	def test_drafts_preserve_statuses_and_submission_is_complete_and_read_only(self):
		first_student, second_student = self.students

		response = self.teacher_post("save_draft", {first_student: "Present"})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(StudentAttendance.objects.count(), 1)

		self.teacher_post("save_draft", {second_student: "Absent"})
		first_record = StudentAttendance.objects.get(student=first_student)
		self.assertEqual(first_record.status, "Present")
		self.assertEqual(StudentAttendance.objects.count(), 2)

		self.teacher_post("submit", {first_student: "Present"})
		session = AttendanceSession.objects.get()
		self.assertEqual(session.status, "draft")

		self.teacher_post(
			"submit",
			{first_student: "Present", second_student: "Absent"},
		)
		session.refresh_from_db()
		self.assertEqual(session.status, "submitted")
		self.assertIsNotNone(session.submitted_at)

		self.teacher_post(
			"save_draft",
			{first_student: "Absent", second_student: "Present"},
		)
		first_record.refresh_from_db()
		self.assertEqual(first_record.status, "Present")

	def test_teacher_cannot_mark_an_unassigned_class(self):
		self.teacher_client.force_login(self.other_teacher)
		response = self.teacher_client.post(
			reverse("attendance:teacher_attendance"),
			{
				"action": "save_draft",
				"class_section": self.class_section.pk,
				"subject": self.subject.pk,
				"date": self.attendance_date.isoformat(),
			},
		)
		self.assertEqual(response.status_code, 403)
		self.assertFalse(AttendanceSession.objects.exists())

	def test_teacher_page_renders_and_management_review_is_role_limited(self):
		response = self.teacher_client.get(
			reverse("attendance:teacher_attendance"),
			{
				"class_section": self.class_section.pk,
				"subject": self.subject.pk,
				"date": self.attendance_date.isoformat(),
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Unmarked")

		response = self.teacher_client.get(reverse("attendance:attendance_review"))
		self.assertEqual(response.status_code, 403)

		manager_client = self.client_class()
		manager_client.force_login(self.principal)
		response = manager_client.get(reverse("attendance:attendance_review"))
		self.assertEqual(response.status_code, 200)

	def test_finalization_creates_parent_alert_once(self):
		absent_student = self.students[0]
		ParentStudent.objects.create(parent=self.parent, student=absent_student)
		self.teacher_post(
			"submit",
			{self.students[0]: "Absent", self.students[1]: "Present"},
		)
		self.assertFalse(AttendanceParentNotification.objects.exists())
		session = AttendanceSession.objects.get()
		finalize_url = reverse(
			"attendance:finalize_student_attendance",
			args=[session.pk],
		)

		manager_client = self.client_class()
		manager_client.force_login(self.principal)
		response = manager_client.post(finalize_url)
		self.assertEqual(response.status_code, 302)
		session.refresh_from_db()
		self.assertEqual(session.status, "finalized")
		self.assertIsNotNone(session.finalized_at)
		self.assertEqual(AttendanceParentNotification.objects.count(), 1)

		manager_client.post(finalize_url)
		self.assertEqual(AttendanceParentNotification.objects.count(), 1)

	def test_correction_changes_attendance_only_after_approval(self):
		record = StudentAttendance.objects.create(
			student=self.students[0],
			class_section=self.class_section,
			subject=self.subject,
			date=self.attendance_date - timedelta(days=1),
			status="Present",
			marked_by=self.teacher,
		)
		AttendanceSession.objects.create(
			class_section=self.class_section,
			subject=self.subject,
			date=record.date,
			status="finalized",
			created_by=self.teacher,
			finalized_by=self.principal,
		)
		correction_url = reverse(
			"attendance:request_attendance_correction",
			args=[record.pk],
		)

		response = self.teacher_client.get(correction_url)
		self.assertEqual(response.status_code, 200)
		self.teacher_client.post(
			correction_url,
			{"new_status": "Absent", "reason": "Incorrectly recorded."},
		)
		record.refresh_from_db()
		correction = AttendanceCorrection.objects.get()
		self.assertEqual(record.status, "Present")
		self.assertEqual(correction.status, "pending")
		self.assertTrue(
			Notification.objects.filter(
				recipient=self.principal,
				notification_type="attendance",
			).exists()
		)

		manager_client = self.client_class()
		manager_client.force_login(self.principal)
		manager_client.post(
			reverse(
				"attendance:review_attendance_correction",
				args=[correction.pk],
			),
			{"decision": "approved"},
		)
		record.refresh_from_db()
		correction.refresh_from_db()
		self.assertEqual(record.status, "Absent")
		self.assertEqual(correction.status, "approved")
		self.assertTrue(
			Notification.objects.filter(
				recipient=self.teacher,
				notification_type="attendance",
			).exists()
		)

		second_correction = AttendanceCorrection.objects.create(
			attendance=record,
			old_status="Absent",
			new_status="Late",
			reason="Second review test.",
			requested_by=self.teacher,
		)
		manager_client.post(
			reverse(
				"attendance:review_attendance_correction",
				args=[second_correction.pk],
			),
			{"decision": "rejected"},
		)
		record.refresh_from_db()
		self.assertEqual(record.status, "Absent")


class AttendancePolicyAndAutomationTests(TestCase):
	def setUp(self):
		self.teacher = self.create_user("policy-teacher", "teacher")
		self.principal = self.create_user("policy-principal", "principal")
		self.student_user = self.create_user("policy-student", "student")
		self.parent = self.create_user("policy-parent", "parent")
		self.class_section = ClassSection.objects.create(
			grade="7",
			section="C",
			academic_year="2026-2027",
		)
		self.subject = Subject.objects.create(
			subject_name="Science",
			subject_code="SCI-7C",
		)
		self.assignment = SubjectEmployeeAssignment.objects.create(
			employee=self.teacher,
			class_section=self.class_section,
			subject=self.subject,
			academic_year=self.class_section.academic_year,
			is_active=True,
		)
		self.student = StudentAdmissionApplication.objects.create(
			application_id="STU-POLICY-01",
			first_name="Policy",
			last_name="Student",
			date_of_birth=date(2014, 2, 2),
			gender="other",
			phone="9111111111",
			address="School address",
			father_name="Parent One",
			mother_name="Parent Two",
			parent_phone="9111111112",
			applying_class="7",
			class_section=self.class_section,
			status="account_created",
		)
		self.student_credential = StudentCredential.objects.create(
			student_application=self.student,
			user=self.student_user,
			username=self.student_user.username,
			temporary_password="temporary",
			is_active=True,
		)
		self.attendance_date = self.previous_non_sunday()
		self.set_user_start_date(self.teacher, self.attendance_date)
		self.set_user_start_date(self.principal, self.attendance_date)
		self.set_credential_start_date(
			self.student_credential,
			self.attendance_date,
		)
		SubjectEmployeeAssignment.objects.filter(pk=self.assignment.pk).update(
			updated_at=timezone.now()
		)
		TimetableEntry.objects.create(
			class_section=self.class_section,
			subject=self.subject,
			employee=self.teacher,
			academic_year=self.class_section.academic_year,
			day=self.attendance_date.strftime("%A"),
			period=1,
			is_active=True,
		)

	def create_user(self, username, role):
		user = User.objects.create_user(username=username, password="test-pass")
		user.profile.role = role
		user.profile.save(update_fields=["role"])
		return user

	def previous_non_sunday(self):
		current = timezone.localdate() - timedelta(days=1)
		while current.weekday() == 6:
			current -= timedelta(days=1)
		return current

	def set_user_start_date(self, user, start_date):
		start_datetime = timezone.make_aware(
			datetime.combine(start_date, datetime.min.time())
		)
		User.objects.filter(pk=user.pk).update(date_joined=start_datetime)

	def set_credential_start_date(self, credential, start_date):
		created_at = timezone.make_aware(
			datetime.combine(start_date, datetime.min.time())
		)
		StudentCredential.objects.filter(pk=credential.pk).update(
			created_at=created_at
		)

	def create_holiday(self, title, event_type="holiday", status="published"):
		return AcademicCalendarEvent.objects.create(
			title=title,
			event_type=event_type,
			start_date=self.attendance_date,
			end_date=self.attendance_date,
			academic_year=self.class_section.academic_year,
			status=status,
		)

	def test_only_published_holiday_events_are_holidays(self):
		self.create_holiday("Draft break", status="draft")
		self.create_holiday("Cancelled break", status="cancelled")
		self.create_holiday("Exam", event_type="examination")
		self.assertIsNone(holiday_details(self.attendance_date))

		event = self.create_holiday("Founders Day")
		details = holiday_details(self.attendance_date)
		self.assertEqual(details["name"], "Founders Day")
		self.assertEqual(details["status"], "Holiday")
		event.status = "cancelled"
		event.save(update_fields=["status"])
		self.assertIsNone(holiday_details(self.attendance_date))

	def test_weekly_holiday_defaults_to_sunday_and_can_be_configured(self):
		sunday = self.attendance_date + timedelta(
			days=(6 - self.attendance_date.weekday()) % 7
		)
		saturday = sunday - timedelta(days=1)
		with override_settings(ATTENDANCE_WEEKLY_HOLIDAYS=(6,)):
			self.assertEqual(holiday_details(sunday)["name"], "Sunday")
			self.assertIsNone(holiday_details(saturday))
		with override_settings(ATTENDANCE_WEEKLY_HOLIDAYS=(5,)):
			self.assertEqual(holiday_details(saturday)["name"], "Saturday")
			self.assertIsNone(holiday_details(sunday))

	def test_command_is_idempotent_skips_approved_leave_and_preserves_records(self):
		LeaveRequest.objects.create(
			user=self.teacher,
			leave_type="Casual Leave",
			from_date=self.attendance_date,
			to_date=self.attendance_date,
			reason="Approved test leave",
			status="approved",
		)
		first_result = process_daily_attendance(self.attendance_date)
		self.assertEqual(first_result["employees_on_leave"], 1)
		self.assertEqual(first_result["students_processed"], 1)
		student_record = StudentAttendance.objects.get(student=self.student)
		self.assertEqual(student_record.status, "Absent")
		self.assertTrue(student_record.remarks.startswith(SYSTEM_ABSENCE_PREFIX))
		self.assertEqual(
			EmployeeAttendance.objects.get(employee=self.teacher).status,
			"Leave",
		)

		second_result = process_daily_attendance(self.attendance_date)
		self.assertEqual(second_result["students_processed"], 0)
		self.assertEqual(StudentAttendance.objects.count(), 1)

		student_record.status = "Present"
		student_record.remarks = "Teacher submitted."
		student_record.marked_by = self.teacher
		student_record.save()
		process_daily_attendance(self.attendance_date)
		student_record.refresh_from_db()
		self.assertEqual(student_record.status, "Present")
		self.assertEqual(student_record.marked_by, self.teacher)

	def test_command_skips_published_holidays_without_creating_absences(self):
		self.create_holiday("School Foundation Day")
		result = process_daily_attendance(self.attendance_date)
		self.assertEqual(result["skipped_holidays"], 1)
		self.assertFalse(StudentAttendance.objects.exists())
		self.assertFalse(EmployeeAttendance.objects.exists())

	def test_management_command_processes_a_past_workday(self):
		output = StringIO()
		call_command(
			"process_daily_attendance",
			"--date",
			self.attendance_date.isoformat(),
			stdout=output,
		)
		self.assertTrue(
			StudentAttendance.objects.filter(
				student=self.student,
				remarks__startswith=SYSTEM_ABSENCE_PREFIX,
			).exists()
		)
		self.assertIn("students_processed", output.getvalue())

	def test_approved_student_leave_is_not_auto_marked_absent(self):
		LeaveRequest.objects.create(
			user=self.student_user,
			leave_type="Sick Leave",
			from_date=self.attendance_date,
			to_date=self.attendance_date,
			reason="Approved student leave",
			status="approved",
		)
		result = process_daily_attendance(self.attendance_date)
		self.assertEqual(result["students_on_leave"], 1)
		self.assertFalse(StudentAttendance.objects.exists())

	def test_attendance_percentage_uses_eligible_workdays(self):
		StudentAttendance.objects.create(
			student=self.student,
			class_section=self.class_section,
			subject=self.subject,
			date=self.attendance_date,
			status="Present",
			marked_by=self.teacher,
		)
		student_summary = student_attendance_summary(
			self.student,
			self.attendance_date,
			self.attendance_date,
		)
		self.assertEqual(student_summary["eligible_working_days"], 1)
		self.assertEqual(student_summary["percentage"], 100)

	def test_student_cannot_write_employee_attendance_and_reports_render(self):
		client = self.client_class()
		client.force_login(self.student_user)
		response = client.post(reverse("attendance:employee_check_in"))
		self.assertEqual(response.status_code, 403)
		self.assertFalse(EmployeeAttendance.objects.exists())

		manager_client = self.client_class()
		manager_client.force_login(self.principal)
		management_response = manager_client.get(
			reverse("attendance:student_attendance_management"),
			{
				"class_id": self.class_section.pk,
				"student_id": self.student.pk,
				"start_date": self.attendance_date.isoformat(),
				"end_date": self.attendance_date.isoformat(),
				"subject_id": self.subject.pk,
			},
		)
		self.assertEqual(management_response.status_code, 200)

		employee_response = manager_client.get(
			reverse("attendance:employee_attendance"),
			{
				"employee": self.teacher.pk,
				"start_date": self.attendance_date.isoformat(),
				"end_date": self.attendance_date.isoformat(),
			},
		)
		self.assertEqual(employee_response.status_code, 200)

	def test_parent_attendance_page_uses_only_linked_child_and_renders(self):
		ParentStudent.objects.create(parent=self.parent, student=self.student)
		client = self.client_class()
		client.force_login(self.parent)
		response = client.get(
			reverse("attendance:child_attendance"),
			{
				"student_id": self.student.pk,
				"start_date": self.attendance_date.isoformat(),
				"end_date": self.attendance_date.isoformat(),
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.student.application_id)

	def test_command_refuses_today_before_six_pm(self):
		local_today = timezone.localdate()
		before_cutoff = timezone.make_aware(
			datetime.combine(local_today, time(17, 59))
		)
		with patch(
			"attendance.management.commands.process_daily_attendance.timezone.localtime",
			return_value=before_cutoff,
		):
			with self.assertRaises(CommandError):
				call_command(
					"process_daily_attendance",
					"--date",
					local_today.isoformat(),
				)

	def test_sunday_command_skips_all_attendance_processing(self):
		sunday = self.attendance_date - timedelta(
			days=(self.attendance_date.weekday() + 1) % 7 or 7
		)
		result = process_daily_attendance(sunday)
		self.assertEqual(result["skipped_holidays"], 1)
		self.assertFalse(StudentAttendance.objects.exists())
		self.assertFalse(EmployeeAttendance.objects.exists())

	def test_command_flags_finalized_sessions_overlapping_new_holidays(self):
		AttendanceSession.objects.create(
			class_section=self.class_section,
			subject=self.subject,
			date=self.attendance_date,
			status="finalized",
			created_by=self.teacher,
			finalized_by=self.principal,
		)
		self.create_holiday("Late Declared Holiday")
		result = process_daily_attendance(self.attendance_date)
		self.assertEqual(result["conflicts"], 1)
		self.assertTrue(
			Notification.objects.filter(
				recipient=self.principal,
				title="Published holiday conflicts with finalized attendance",
			).exists()
		)

	def test_summaries_exclude_holidays_and_return_none_for_zero_workdays(self):
		self.create_holiday("Attendance Summary Holiday")
		student_summary = student_attendance_summary(
			self.student,
			self.attendance_date,
			self.attendance_date,
		)
		self.assertEqual(student_summary["eligible_working_days"], 0)
		self.assertIsNone(student_summary["percentage"])

		employee_summary = employee_attendance_summary(
			self.teacher,
			self.attendance_date,
			self.attendance_date,
		)
		self.assertEqual(employee_summary["eligible_working_days"], 0)
		self.assertIsNone(employee_summary["percentage"])
