from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from transport.models import BusRoute, BusStop

from .forms import (
	EmployeeAdmissionApplicationForm,
	StudentAdmissionApplicationForm,
)
from .models import (
	ApplicationApproval,
	EmployeeAdmissionApplication,
	EmployeeCredential,
	StudentAdmissionApplication,
)


class SavedPickupStopFormTests(TestCase):
	def setUp(self):
		self.route = BusRoute.objects.create(
			route_name="Central Route",
			route_code="CENTRAL-TEST",
			start_location="Madanapalle",
			end_location="School",
		)
		self.other_route = BusRoute.objects.create(
			route_name="North Route",
			route_code="NORTH-TEST",
			start_location="Madanapalle",
			end_location="School",
		)
		self.saved_stop = BusStop.objects.create(
			route=self.route,
			stop_name="Old Saved Stop",
			stop_order=1,
			is_active=False,
		)
		self.active_stop = BusStop.objects.create(
			route=self.route,
			stop_name="Current Stop",
			stop_order=2,
			is_active=True,
		)
		self.other_route_stop = BusStop.objects.create(
			route=self.other_route,
			stop_name="Other Route Stop",
			stop_order=1,
			is_active=True,
		)

	def create_student(self):
		return StudentAdmissionApplication.objects.create(
			first_name="Pickup",
			last_name="Student",
			date_of_birth=date(2015, 1, 1),
			gender="other",
			phone="9000000000",
			email="pickup@example.com",
			address="Student address",
			father_name="Parent One",
			mother_name="Parent Two",
			parent_phone="9000000001",
			applying_class="5",
			bus_required=True,
			bus_location="Madanapalle",
			bus_route=self.route,
			pickup_stop=self.saved_stop,
		)

	def create_employee(self):
		return EmployeeAdmissionApplication.objects.create(
			first_name="Pickup",
			last_name="Employee",
			date_of_birth=date(1985, 1, 1),
			gender="other",
			phone="9000000002",
			designation="Teacher",
			joining_date=date(2020, 1, 1),
			qualification="Degree",
			address="Employee address",
			city="Madanapalle",
			state="Andhra Pradesh",
			pincode="517325",
			bus_required=True,
			bus_location="Madanapalle",
			bus_route=self.route,
			pickup_stop=self.saved_stop,
		)

	def assert_saved_stop_is_selected(self, form):
		self.assertEqual(form["bus_route"].value(), self.route.pk)
		self.assertEqual(form["pickup_stop"].value(), self.saved_stop.pk)
		self.assertEqual(
			set(form.fields["pickup_stop"].queryset),
			{self.saved_stop, self.active_stop},
		)
		self.assertNotIn(
			self.other_route_stop,
			form.fields["pickup_stop"].queryset,
		)

	def test_student_form_prefills_saved_route_and_pickup_stop(self):
		form = StudentAdmissionApplicationForm(instance=self.create_student())
		self.assert_saved_stop_is_selected(form)

	def test_employee_form_prefills_saved_route_and_pickup_stop(self):
		form = EmployeeAdmissionApplicationForm(instance=self.create_employee())
		self.assert_saved_stop_is_selected(form)


class EmployeeRoleAssignmentTests(TestCase):
	def setUp(self):
		self.approver = User.objects.create_user(
			username="role-approver",
			password="test-pass",
		)
		self.approver.profile.role = "vice_principal"
		self.approver.profile.save(update_fields=["role"])
		self.client.force_login(self.approver)

		self.application = EmployeeAdmissionApplication.objects.create(
			application_id="EMP-APP-2026-0901",
			first_name="Taylor",
			last_name="Staff",
			date_of_birth=date(1988, 1, 1),
			gender="other",
			phone="9000000011",
			email="taylor@example.com",
			designation="School Staff",
			joining_date=date(2025, 1, 1),
			qualification="Degree",
			address="Staff address",
			city="Madanapalle",
			state="Andhra Pradesh",
			pincode="517325",
			status="vp_approved",
		)
		self.approval = ApplicationApproval.objects.create(
			application_type="Employee",
			application_id=self.application.application_id,
			stage="vice_principal",
			status="pending",
		)

	def test_new_employee_form_requires_one_of_the_existing_staff_roles(self):
		form = EmployeeAdmissionApplicationForm()
		self.assertTrue(form.fields["staff_role"].required)
		role_values = {
			value
			for group_name, options in form.fields["staff_role"].choices
			if isinstance(options, (list, tuple))
			for value, label in options
		}
		self.assertEqual(
			role_values,
			{
				"teacher",
				"admission_staff",
				"principal",
				"vice_principal",
				"chairman",
				"accountant",
				"system_administrator",
				"bus_driver",
			},
		)

	def test_role_category_groups_render_from_existing_profile_choices(self):
		response = self.client.get(
			reverse(
				"admissions:vp_employee_approval_detail",
				args=[self.approval.pk],
			)
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Teaching Staff")
		self.assertContains(response, "Admission Staff")
		self.assertContains(response, "Management Staff")
		self.assertContains(response, "Bus Drivers")

	@patch("admissions.views.send_credentials_email", return_value=True)
	@patch("admissions.views.send_credentials_sms", return_value=True)
	def test_approved_employee_receives_selected_staff_role(self, send_sms, send_email):
		response = self.client.post(
			reverse(
				"admissions:vp_approve_employee",
				args=[self.approval.pk],
			),
			{"staff_role": "bus_driver"},
		)

		self.assertRedirects(response, reverse("admissions:vp_employee_approvals"))
		credential = EmployeeCredential.objects.get(
			employee_application=self.application
		)
		self.assertEqual(credential.user.profile.role, "bus_driver")
		self.assertEqual(credential.user.profile.get_role_display(), "Bus Driver")
		self.application.refresh_from_db()
		self.assertEqual(self.application.staff_role, "bus_driver")
		self.approval.refresh_from_db()
		self.assertEqual(self.approval.status, "accepted")

	def test_invalid_staff_role_is_rejected(self):
		response = self.client.post(
			reverse(
				"admissions:vp_approve_employee",
				args=[self.approval.pk],
			),
			{"staff_role": "student"},
		)
		self.assertEqual(response.status_code, 400)
		self.assertFalse(EmployeeCredential.objects.exists())
