from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from admissions.models import EmployeeAdmissionApplication, EmployeeCredential
from transport.forms import BusForm
from transport.models import Bus, BusRoute, BusStop


class BusEditWorkflowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="transport-vp",
			password="test-pass",
		)
		self.user.profile.role = "vice_principal"
		self.user.profile.save(update_fields=["role"])
		self.client.force_login(self.user)

		self.route = self.create_route("North Route", "NORTH-1")
		self.updated_route = self.create_route("South Route", "SOUTH-1")
		self.driver = EmployeeAdmissionApplication.objects.create(
			application_id="EMP-TEST-DRIVER",
			first_name="Ravi",
			last_name="Driver",
			date_of_birth=date(1985, 1, 1),
			gender="male",
			phone="9000000000",
			designation="Bus Driver",
			joining_date=date(2020, 1, 1),
			qualification="High School",
			address="Driver address",
			city="Madanapalle",
			state="Andhra Pradesh",
			pincode="517325",
			status="account_created",
		)
		self.driver_user = self.create_employee_user("bus-driver", "bus_driver")
		self.create_credential(self.driver, self.driver_user)
		self.teacher = EmployeeAdmissionApplication.objects.create(
			application_id="EMP-TEST-TEACHER",
			first_name="Tara",
			last_name="Teacher",
			date_of_birth=date(1988, 1, 1),
			gender="female",
			phone="9000000003",
			designation="Teacher",
			joining_date=date(2021, 1, 1),
			qualification="Degree",
			address="Teacher address",
			city="Madanapalle",
			state="Andhra Pradesh",
			pincode="517325",
			status="account_created",
		)
		self.teacher_user = self.create_employee_user("teacher-staff", "teacher")
		self.create_credential(self.teacher, self.teacher_user)
		self.bus = Bus.objects.create(
			bus_number="BUS-001",
			registration_number="AP01AB1234",
			bus_name="North Star",
			manufacturer="Tata",
			model_name="Starbus",
			manufacture_year=2022,
			capacity=40,
			fuel_type="diesel",
			driver=self.driver,
			route=self.route,
			tracker_device_id="GPS-001",
			tracker_imei="123456789012345",
			tracker_provider="Onelap",
			tracker_is_active=True,
			status="active",
			is_active=True,
			insurance_expiry=date(2027, 1, 1),
			fitness_expiry=date(2027, 2, 1),
			permit_expiry=date(2027, 3, 1),
			pollution_expiry=date(2027, 4, 1),
		)

	def create_route(self, name, code):
		return BusRoute.objects.create(
			route_name=name,
			route_code=code,
			start_location="Town",
			end_location="School",
		)

	def create_employee_user(self, username, role):
		user = User.objects.create_user(username=username, password="test-pass")
		user.profile.role = role
		user.profile.save(update_fields=["role"])
		return user

	def create_credential(self, employee, user):
		return EmployeeCredential.objects.create(
			employee_application=employee,
			user=user,
			username=user.username,
			temporary_password="temporary",
		)

	def edit_url(self):
		return reverse("transport:vp_bus_assignment")

	def update_data(self, **overrides):
		data = {
			"bus_id": str(self.bus.pk),
			"bus_number": "BUS-001",
			"registration_number": "AP01AB1234",
			"bus_name": "North Star Updated",
			"manufacturer": "Tata",
			"model_name": "Starbus",
			"manufacture_year": "2022",
			"capacity": "44",
			"fuel_type": "diesel",
			"driver": str(self.driver.pk),
			"route": str(self.updated_route.pk),
			"tracker_device_id": "GPS-001",
			"tracker_imei": "123456789012345",
			"tracker_provider": "Onelap Updated",
			"tracker_is_active": "on",
			"status": "maintenance",
			"is_active": "on",
			"insurance_expiry": "2027-01-01",
			"fitness_expiry": "2027-02-01",
			"permit_expiry": "2027-03-01",
			"pollution_expiry": "2027-04-01",
		}
		data.update(overrides)
		return data

	def test_edit_get_prefills_saved_values_and_related_choices(self):
		response = self.client.get(
			self.edit_url(),
			{"bus_id": self.bus.pk, "mode": "edit"},
		)

		self.assertEqual(response.status_code, 200)
		form = response.context["form"]
		self.assertEqual(form.instance.pk, self.bus.pk)
		self.assertEqual(form["bus_number"].value(), "BUS-001")
		self.assertEqual(form["capacity"].value(), 40)
		self.assertEqual(form["driver"].value(), self.driver.pk)
		self.assertEqual(form["route"].value(), self.route.pk)
		self.assertContains(response, "Update Bus")
		self.assertContains(response, 'name="bus_id"')
		self.assertContains(response, 'name="tracker_provider"')
		self.assertContains(response, 'name="pollution_expiry"')

	def test_bus_driver_dropdown_only_contains_bus_driver_role(self):
		form = BusForm()
		self.assertEqual(
			list(form.fields["driver"].queryset),
			[self.driver],
		)

	def test_update_changes_existing_bus_and_does_not_create_another(self):
		response = self.client.post(
			f"{self.edit_url()}?bus_id={self.bus.pk}&mode=edit",
			self.update_data(),
		)

		self.assertRedirects(response, reverse("transport:vp_all_buses"))
		self.assertEqual(Bus.objects.count(), 1)
		self.bus.refresh_from_db()
		self.assertEqual(self.bus.bus_name, "North Star Updated")
		self.assertEqual(self.bus.capacity, 44)
		self.assertEqual(self.bus.driver_id, self.driver.pk)
		self.assertEqual(self.bus.route_id, self.updated_route.pk)
		self.assertEqual(self.bus.tracker_provider, "Onelap Updated")
		self.assertEqual(self.bus.pollution_expiry, date(2027, 4, 1))

	def test_invalid_update_keeps_entered_values_and_errors(self):
		other_bus = Bus.objects.create(
			bus_number="BUS-002",
			registration_number="AP01AB5678",
		)
		response = self.client.post(
			f"{self.edit_url()}?bus_id={self.bus.pk}&mode=edit",
			self.update_data(
				bus_number=other_bus.bus_number,
				registration_number=other_bus.registration_number,
			),
		)

		self.assertEqual(response.status_code, 200)
		form = response.context["form"]
		self.assertEqual(form.instance.pk, self.bus.pk)
		self.assertEqual(form["bus_number"].value(), "BUS-002")
		self.assertTrue(form["bus_number"].errors)
		self.assertEqual(Bus.objects.count(), 2)
		self.bus.refresh_from_db()
		self.assertEqual(self.bus.bus_number, "BUS-001")


class RouteStopOptionsTests(TestCase):
	def setUp(self):
		user = User.objects.create_user(
			username="transport-user",
			password="test-pass",
		)
		self.client.force_login(user)
		self.route = BusRoute.objects.create(
			route_name="Madanapalle Route",
			route_code="MDP-OPTIONS",
			start_location="Madanapalle",
			end_location="School",
		)
		self.other_route = BusRoute.objects.create(
			route_name="Chittoor Route",
			route_code="CTR-OPTIONS",
			start_location="Chittoor",
			end_location="School",
		)
		self.active_stop = BusStop.objects.create(
			route=self.route,
			stop_name="Active Stop",
			stop_order=1,
			is_active=True,
		)
		self.saved_inactive_stop = BusStop.objects.create(
			route=self.route,
			stop_name="Saved Stop",
			stop_order=2,
			is_active=False,
		)
		self.other_route_stop = BusStop.objects.create(
			route=self.other_route,
			stop_name="Other Route Stop",
			stop_order=1,
			is_active=True,
		)

	def test_route_options_respect_selected_location(self):
		response = self.client.get(
			reverse("transport:route_options"),
			{"location": "Madanapalle"},
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			[route["id"] for route in response.json()["routes"]],
			[self.route.pk],
		)

	def test_stop_options_only_return_selected_routes_stops(self):
		response = self.client.get(
			reverse("transport:stop_options"),
			{"route_id": self.route.pk},
		)
		self.assertEqual(
			[stop["id"] for stop in response.json()["stops"]],
			[self.active_stop.pk, self.saved_inactive_stop.pk],
		)

		edit_response = self.client.get(
			reverse("transport:stop_options"),
			{
				"route_id": self.route.pk,
				"selected_stop_id": self.saved_inactive_stop.pk,
			},
		)
		self.assertEqual(
			{stop["id"] for stop in edit_response.json()["stops"]},
			{self.active_stop.pk, self.saved_inactive_stop.pk},
		)
		self.assertNotIn(
			self.other_route_stop.pk,
			{stop["id"] for stop in edit_response.json()["stops"]},
		)
