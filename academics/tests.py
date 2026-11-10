from django.contrib.auth.models import User
from django.test import TestCase

from .forms import (
	ClassSectionForm,
	SubjectEmployeeAssignmentForm,
	TimetableEntryForm,
)


class TeachingStaffDropdownTests(TestCase):
	def setUp(self):
		self.teacher = self.create_staff_user("role-teacher", "teacher")
		self.bus_driver = self.create_staff_user("role-driver", "bus_driver")
		self.admission_staff = self.create_staff_user(
			"role-admission",
			"admission_staff",
		)

	def create_staff_user(self, username, role):
		user = User.objects.create_user(username=username, password="test-pass")
		user.profile.role = role
		user.profile.save(update_fields=["role"])
		return user

	def test_class_subject_and_timetable_dropdowns_only_show_teachers(self):
		forms = (
			ClassSectionForm(),
			SubjectEmployeeAssignmentForm(),
			TimetableEntryForm(),
		)
		for form in forms:
			self.assertEqual(
				list(form.fields["class_teacher" if "class_teacher" in form.fields else "employee"].queryset),
				[self.teacher],
			)
			self.assertNotIn(
				self.bus_driver,
				form.fields[
					"class_teacher" if "class_teacher" in form.fields else "employee"
				].queryset,
			)
			self.assertNotIn(
				self.admission_staff,
				form.fields[
					"class_teacher" if "class_teacher" in form.fields else "employee"
				].queryset,
			)
