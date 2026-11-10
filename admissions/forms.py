from django import forms

from .models import (
    StudentAdmissionApplication,
    EmployeeAdmissionApplication,
)

from transport.models import (
    BusRoute,
    BusStop,
)

class StudentAdmissionApplicationForm(forms.ModelForm):

    # ========================================================
    # EMAIL
    # ========================================================

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter personal Gmail / email address",
            }
        ),
    )

    # ========================================================
    # TRANSPORT - LOCATION
    # ========================================================

    bus_location = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "id_bus_location",
            }
        ),
    )

    # ========================================================
    # TRANSPORT - ROUTE
    # ========================================================

    bus_route = forms.ModelChoiceField(
        required=False,
        queryset=BusRoute.objects.none(),
        empty_label="Select route",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "id_bus_route",
            }
        ),
    )

    # ========================================================
    # TRANSPORT - PICKUP STOP
    # ========================================================

    pickup_stop = forms.ModelChoiceField(
        required=False,
        queryset=BusStop.objects.none(),
        empty_label="Select pickup stop",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "id_pickup_stop",
            }
        ),
    )

    class Meta:

        model = StudentAdmissionApplication

        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "phone",
            "email",
            "address",

            # Transport
            "bus_required",
            "bus_location",
            "bus_route",
            "pickup_stop",

            # Parent
            "father_name",
            "mother_name",
            "parent_phone",
            "parent_email",

            # Academic
            "applying_class",
            "previous_school",
            "previous_percentage",

            # Documents
            "student_photo",
            "birth_certificate",
            "aadhaar_card",
            "previous_school_certificate",
            "transfer_certificate",
        ]

        widgets = {

            # =================================================
            # PERSONAL DETAILS
            # =================================================

            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter first name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter last name",
                }
            ),

            "date_of_birth": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "gender": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter phone number",
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter complete address",
                }
            ),

            # =================================================
            # TRANSPORT
            # =================================================

            "bus_required": forms.Select(
                choices=[
                    (False, "No"),
                    (True, "Yes"),
                ],
                attrs={
                    "class": "form-control",
                    "id": "id_bus_required",
                }
            ),

            # =================================================
            # PARENT DETAILS
            # =================================================

            "father_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter father's name",
                }
            ),

            "mother_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter mother's name",
                }
            ),

            "parent_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter parent phone number",
                }
            ),

            "parent_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter parent email address",
                }
            ),

            # =================================================
            # ACADEMIC DETAILS
            # =================================================

            "applying_class": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 8th Class",
                }
            ),

            "previous_school": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter previous school",
                }
            ),

            "previous_percentage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter percentage",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),

            # =================================================
            # DOCUMENTS
            # =================================================

            "student_photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "birth_certificate": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),

            "aadhaar_card": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),

            "previous_school_certificate": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),

            "transfer_certificate": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),
        }

    # ========================================================
    # INITIALIZE
    # ========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # ====================================================
        # LOCATION DROPDOWN
        # ====================================================

        locations = (
            BusRoute.objects
            .filter(is_active=True)
            .exclude(start_location__isnull=True)
            .exclude(start_location="")
            .values_list(
                "start_location",
                flat=True
            )
            .distinct()
            .order_by("start_location")
        )

        self.fields["bus_location"].choices = [
            ("", "Select location")
        ] + [
            (location, location)
            for location in locations
        ]

        # ====================================================
        # ACTIVE ROUTES
        # ====================================================

        self.fields["bus_route"].queryset = (
            BusRoute.objects
            .filter(is_active=True)
            .order_by("route_name")
        )

        # ====================================================
        # GET LOCATION
        # ====================================================

        location = None

        if self.is_bound:

            location = self.data.get(
                "bus_location"
            )

        if not location:

            location = self.initial.get(
                "bus_location"
            )

        # ====================================================
        # FILTER ROUTES BY LOCATION
        # ====================================================

        if location:

            self.fields["bus_route"].queryset = (
                BusRoute.objects
                .filter(
                    is_active=True,
                    start_location__iexact=location
                )
                .order_by("route_name")
            )

        saved_route_id = getattr(self.instance, "bus_route_id", None)
        if saved_route_id:
            self.fields["bus_route"].queryset = (
                self.fields["bus_route"].queryset
                | BusRoute.objects.filter(pk=saved_route_id)
            ).distinct().order_by("route_name")

        # ====================================================
        # GET ROUTE
        # ====================================================

        route_id = None

        if self.is_bound:

            route_id = self.data.get(
                "bus_route"
            )

        if not route_id:

            route_id = self.initial.get(
                "bus_route"
            )

        # ====================================================
        # FILTER STOPS BY ROUTE
        # ====================================================

        if route_id:
            stops = BusStop.objects.filter(
                route_id=route_id,
            )
            saved_stop_id = getattr(self.instance, "pickup_stop_id", None)
            if saved_stop_id:
                stops = stops | BusStop.objects.filter(
                    route_id=route_id,
                    pk=saved_stop_id,
                )
            self.fields["pickup_stop"].queryset = stops.distinct().order_by(
                "stop_order"
            )

    # ========================================================
    # FIRST NAME VALIDATION
    # ========================================================

    def clean_first_name(self):

        value = self.cleaned_data.get(
            "first_name",
            ""
        ).strip()

        if not value:

            raise forms.ValidationError(
                "First name is required."
            )

        return value

    # ========================================================
    # PHONE VALIDATION
    # ========================================================

    def clean_phone(self):

        value = self.cleaned_data.get(
            "phone",
            ""
        ).strip()

        if not value:

            raise forms.ValidationError(
                "Phone number is required."
            )

        if not value.isdigit():

            raise forms.ValidationError(
                "Phone number must contain only digits."
            )

        if len(value) != 10:

            raise forms.ValidationError(
                "Phone number must contain 10 digits."
            )

        return value

    # ========================================================
    # PARENT PHONE VALIDATION
    # ========================================================

    def clean_parent_phone(self):

        value = self.cleaned_data.get(
            "parent_phone",
            ""
        ).strip()

        if not value:

            raise forms.ValidationError(
                "Parent phone number is required."
            )

        if not value.isdigit():

            raise forms.ValidationError(
                "Parent phone number must contain only digits."
            )

        if len(value) != 10:

            raise forms.ValidationError(
                "Parent phone number must contain 10 digits."
            )

        return value

    # ========================================================
    # PERCENTAGE VALIDATION
    # ========================================================

    def clean_previous_percentage(self):

        value = self.cleaned_data.get(
            "previous_percentage"
        )

        if value is not None:

            if value < 0 or value > 100:

                raise forms.ValidationError(
                    "Percentage must be between 0 and 100."
                )

        return value

    # ========================================================
    # TRANSPORT VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        bus_required = cleaned_data.get(
            "bus_required"
        )

        bus_location = cleaned_data.get(
            "bus_location"
        )

        bus_route = cleaned_data.get(
            "bus_route"
        )

        pickup_stop = cleaned_data.get(
            "pickup_stop"
        )

        # ====================================================
        # BUS REQUIRED
        # ====================================================

        if bus_required:

            if not bus_location:

                self.add_error(
                    "bus_location",
                    "Please select the student's bus location."
                )

            if not bus_route:

                self.add_error(
                    "bus_route",
                    "Please select a bus route."
                )

            if not pickup_stop:

                self.add_error(
                    "pickup_stop",
                    "Please select the nearest pickup stop."
                )

        # ====================================================
        # BUS NOT REQUIRED
        # ====================================================

        else:

            cleaned_data["bus_location"] = None
            cleaned_data["bus_route"] = None
            cleaned_data["pickup_stop"] = None

        return cleaned_data

class EmployeeAdmissionApplicationForm(forms.ModelForm):

    staff_role = forms.ChoiceField(
        choices=[
            ("", "Select staff role"),
            ("Teaching Staff", (("teacher", "Teaching Staff"),)),
            ("Admission Staff", (("admission_staff", "Admission Staff"),)),
            (
                "Management Staff",
                (
                    ("principal", "Principal"),
                    ("vice_principal", "Vice Principal"),
                    ("chairman", "Chairman"),
                    ("accountant", "Accountant"),
                    ("system_administrator", "System Administrator"),
                ),
            ),
            ("Bus Drivers", (("bus_driver", "Bus Driver"),)),
        ],
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Assigned Staff Role",
    )

    # ========================================================
    # EMAIL
    # ========================================================

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter personal Gmail / email address",
            }
        ),
    )

    # ========================================================
    # TRANSPORT - LOCATION
    # ========================================================

    bus_location = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "id_bus_location",
            }
        ),
    )

    # ========================================================
    # TRANSPORT - ROUTE
    # ========================================================

    bus_route = forms.ModelChoiceField(
        required=False,
        queryset=BusRoute.objects.none(),
        empty_label="Select route",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "id_bus_route",
            }
        ),
    )

    # ========================================================
    # TRANSPORT - PICKUP STOP
    # ========================================================

    pickup_stop = forms.ModelChoiceField(
        required=False,
        queryset=BusStop.objects.none(),
        empty_label="Select pickup stop",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "id_pickup_stop",
            }
        ),
    )

    class Meta:

        model = EmployeeAdmissionApplication

        fields = [

            # Personal
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "marital_status",

            # Contact
            "email",
            "phone",
            "alternate_phone",

            # Professional
            "designation",
            "staff_role",
            "department",
            "joining_date",
            "qualification",
            "specialization",
            "experience_years",
            "previous_organization",
            "previous_salary",

            # Address
            "address",
            "city",
            "state",
            "pincode",

            # Transport
            "bus_required",
            "bus_location",
            "bus_route",
            "pickup_stop",

            # Emergency
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",

            # Documents
            "employee_photo",
            "aadhaar_card",
            "pan_card",
            "educational_certificate",
            "experience_certificate",
            "resume",
            "joining_document",
        ]

        widgets = {

            # =================================================
            # PERSONAL DETAILS
            # =================================================

            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter first name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter last name",
                }
            ),

            "date_of_birth": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "gender": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "marital_status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            # =================================================
            # CONTACT DETAILS
            # =================================================

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter phone number",
                }
            ),

            "alternate_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter alternate phone number",
                }
            ),

            # =================================================
            # PROFESSIONAL DETAILS
            # =================================================

            "designation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Mathematics Teacher",
                }
            ),

            "staff_role": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "department": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter department",
                }
            ),

            "joining_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "qualification": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter qualification",
                }
            ),

            "specialization": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter specialization",
                }
            ),

            "experience_years": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2.5",
                    "step": "0.1",
                    "min": "0",
                }
            ),

            "previous_organization": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter previous organization",
                }
            ),

            "previous_salary": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter previous salary",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            # =================================================
            # ADDRESS
            # =================================================

            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter complete address",
                }
            ),

            "city": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter city",
                }
            ),

            "state": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter state",
                }
            ),

            "pincode": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter pincode",
                }
            ),

            # =================================================
            # TRANSPORT
            # =================================================

            "bus_required": forms.Select(
                choices=[
                    (False, "No"),
                    (True, "Yes"),
                ],
                attrs={
                    "class": "form-control",
                    "id": "id_bus_required",
                }
            ),

            # =================================================
            # EMERGENCY CONTACT
            # =================================================

            "emergency_contact_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter emergency contact name",
                }
            ),

            "emergency_contact_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter emergency contact phone",
                }
            ),

            "emergency_contact_relation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Father",
                }
            ),

            # =================================================
            # DOCUMENTS
            # =================================================

            "employee_photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "aadhaar_card": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),

            "pan_card": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),

            "educational_certificate": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),

            "experience_certificate": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),

            "resume": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.doc,.docx",
                }
            ),

            "joining_document": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),
        }

    # ========================================================
    # INITIALIZE
    # ========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # ====================================================
        # LOCATION DROPDOWN
        # ====================================================

        locations = (
            BusRoute.objects
            .filter(is_active=True)
            .exclude(start_location__isnull=True)
            .exclude(start_location="")
            .values_list(
                "start_location",
                flat=True
            )
            .distinct()
            .order_by("start_location")
        )

        self.fields["bus_location"].choices = [
            ("", "Select location")
        ] + [
            (location, location)
            for location in locations
        ]

        # ====================================================
        # ACTIVE ROUTES
        # ====================================================

        self.fields["bus_route"].queryset = (
            BusRoute.objects
            .filter(is_active=True)
            .order_by("route_name")
        )

        # ====================================================
        # GET LOCATION
        # ====================================================

        location = None

        if self.is_bound:

            location = self.data.get(
                "bus_location"
            )

        if not location:

            location = self.initial.get(
                "bus_location"
            )

        # ====================================================
        # FILTER ROUTES BY LOCATION
        # ====================================================

        if location:

            self.fields["bus_route"].queryset = (
                BusRoute.objects
                .filter(
                    is_active=True,
                    start_location__iexact=location
                )
                .order_by("route_name")
            )

        saved_route_id = getattr(self.instance, "bus_route_id", None)
        if saved_route_id:
            self.fields["bus_route"].queryset = (
                self.fields["bus_route"].queryset
                | BusRoute.objects.filter(pk=saved_route_id)
            ).distinct().order_by("route_name")

        # ====================================================
        # GET ROUTE
        # ====================================================

        route_id = None

        if self.is_bound:

            route_id = self.data.get(
                "bus_route"
            )

        if not route_id:

            route_id = self.initial.get(
                "bus_route"
            )

        # ====================================================
        # FILTER STOPS BY ROUTE
        # ====================================================

        if route_id:
            stops = BusStop.objects.filter(
                route_id=route_id,
            )
            saved_stop_id = getattr(self.instance, "pickup_stop_id", None)
            if saved_stop_id:
                stops = stops | BusStop.objects.filter(
                    route_id=route_id,
                    pk=saved_stop_id,
                )
            self.fields["pickup_stop"].queryset = stops.distinct().order_by(
                "stop_order"
            )

    # ========================================================
    # PHONE VALIDATION
    # ========================================================

    def clean_phone(self):

        value = self.cleaned_data.get(
            "phone",
            ""
        ).strip()

        if not value:

            raise forms.ValidationError(
                "Phone number is required."
            )

        if not value.isdigit():

            raise forms.ValidationError(
                "Phone number must contain only digits."
            )

        if len(value) != 10:

            raise forms.ValidationError(
                "Phone number must contain 10 digits."
            )

        return value

    # ========================================================
    # ALTERNATE PHONE
    # ========================================================

    def clean_alternate_phone(self):

        value = self.cleaned_data.get(
            "alternate_phone",
            ""
        ).strip()

        if value:

            if not value.isdigit():

                raise forms.ValidationError(
                    "Alternate phone number must contain only digits."
                )

            if len(value) != 10:

                raise forms.ValidationError(
                    "Alternate phone number must contain 10 digits."
                )

        return value

    # ========================================================
    # EXPERIENCE
    # ========================================================

    def clean_experience_years(self):

        value = self.cleaned_data.get(
            "experience_years"
        )

        if value is not None and value < 0:

            raise forms.ValidationError(
                "Experience cannot be negative."
            )

        return value

    # ========================================================
    # PREVIOUS SALARY
    # ========================================================

    def clean_previous_salary(self):

        value = self.cleaned_data.get(
            "previous_salary"
        )

        if value is not None and value < 0:

            raise forms.ValidationError(
                "Salary cannot be negative."
            )

        return value

    # ========================================================
    # PINCODE
    # ========================================================

    def clean_pincode(self):

        value = self.cleaned_data.get(
            "pincode",
            ""
        ).strip()

        if not value.isdigit():

            raise forms.ValidationError(
                "Pincode must contain only digits."
            )

        if len(value) != 6:

            raise forms.ValidationError(
                "Pincode must contain 6 digits."
            )

        return value

    # ========================================================
    # TRANSPORT VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        bus_required = cleaned_data.get(
            "bus_required"
        )

        bus_location = cleaned_data.get(
            "bus_location"
        )

        bus_route = cleaned_data.get(
            "bus_route"
        )

        pickup_stop = cleaned_data.get(
            "pickup_stop"
        )

        # ====================================================
        # BUS REQUIRED
        # ====================================================

        if bus_required:

            if not bus_location:

                self.add_error(
                    "bus_location",
                    "Please select the employee's bus location."
                )

            if not bus_route:

                self.add_error(
                    "bus_route",
                    "Please select a bus route."
                )

            if not pickup_stop:

                self.add_error(
                    "pickup_stop",
                    "Please select the nearest pickup stop."
                )

        # ====================================================
        # BUS NOT REQUIRED
        # ====================================================

        else:

            cleaned_data["bus_location"] = None
            cleaned_data["bus_route"] = None
            cleaned_data["pickup_stop"] = None

        return cleaned_data