from django import forms

from admissions.models import EmployeeAdmissionApplication

from .models import Bus, BusRoute, BusStop


class BusRouteForm(forms.ModelForm):

    assigned_bus = forms.ModelChoiceField(
        queryset=Bus.objects.filter(is_active=True).order_by("bus_number"),
        required=False,
        empty_label="Select Bus",
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
        label="Assigned Bus",
    )

    class Meta:
        model = BusRoute

        fields = [
            "route_name",
            "route_code",
            "start_location",
            "end_location",
            "total_distance_km",
            "estimated_duration_minutes",
            "is_active",
        ]

        widgets = {

            "route_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter route name",
                }
            ),

            "route_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: R001",
                }
            ),

            "start_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Madanapalle",
                }
            ),

            "end_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: School",
                }
            ),

            "total_distance_km": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Distance in KM",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "estimated_duration_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Duration in minutes",
                    "min": "0",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class BusStopForm(forms.ModelForm):

    class Meta:
        model = BusStop

        fields = [
            "stop_name",
            "stop_order",
            "address",
            "pickup_time",
            "drop_time",
            "is_active",
        ]

        widgets = {

            "stop_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter stop name",
                }
            ),

            "stop_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "1",
                }
            ),

            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter stop address",
                }
            ),

            "pickup_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            "drop_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

from django import forms

from .models import Bus, BusRoute, BusStop


# =========================================================
# BUS ROUTE FORM
# =========================================================

class BusRouteForm(forms.ModelForm):

    assigned_bus = forms.ModelChoiceField(
        queryset=Bus.objects.filter(
            is_active=True
        ).order_by(
            "bus_number"
        ),
        required=False,
        empty_label="Select Bus",
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
        label="Assigned Bus",
    )

    class Meta:

        model = BusRoute

        fields = [
            "route_name",
            "route_code",
            "start_location",
            "end_location",
            "total_distance_km",
            "estimated_duration_minutes",
            "is_active",
        ]

        widgets = {

            "route_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter route name",
                }
            ),

            "route_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: R001",
                }
            ),

            "start_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Madanapalle",
                }
            ),

            "end_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: School",
                }
            ),

            "total_distance_km": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Distance in KM",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "estimated_duration_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Duration in minutes",
                    "min": "0",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


# =========================================================
# BUS STOP FORM
# =========================================================

class BusStopForm(forms.ModelForm):

    class Meta:

        model = BusStop

        fields = [
            "stop_name",
            "stop_order",
            "address",
            "pickup_time",
            "drop_time",
            "is_active",
        ]

        widgets = {

            "stop_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter stop name",
                }
            ),

            "stop_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "1",
                }
            ),

            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter stop address",
                }
            ),

            "pickup_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            "drop_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

# =========================================================
# BUS FORM
# =========================================================

class BusForm(forms.ModelForm):

    class Meta:

        model = Bus

        fields = [
            "bus_number",
            "registration_number",
            "bus_name",
            "manufacturer",
            "model_name",
            "manufacture_year",
            "capacity",
            "fuel_type",

            "driver",
            "route",

            "tracker_device_id",
            "tracker_imei",
            "tracker_provider",
            "tracker_is_active",

            "status",
            "is_active",

            "insurance_expiry",
            "fitness_expiry",
            "permit_expiry",
            "pollution_expiry",
        ]

        widgets = {

            # =================================================
            # BASIC BUS INFORMATION
            # =================================================

            "bus_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: BUS-001",
                }
            ),

            "registration_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: AP39AB1234",
                }
            ),

            "bus_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter bus name",
                }
            ),

            "manufacturer": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Tata",
                }
            ),

            "model_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Starbus",
                }
            ),

            "manufacture_year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2024",
                    "min": "1900",
                    "max": "2100",
                }
            ),

            "capacity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Number of seats",
                    "min": "1",
                }
            ),

            "fuel_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            # =================================================
            # DRIVER
            # =================================================

            "driver": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            # =================================================
            # ROUTE
            # =================================================

            "route": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            # =================================================
            # GPS / TRACKER
            # =================================================

            "tracker_device_id": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter GPS device ID",
                }
            ),

            "tracker_imei": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter tracker IMEI",
                }
            ),

            "tracker_provider": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Onelap",
                }
            ),

            "tracker_is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

            # =================================================
            # STATUS
            # =================================================

            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

            # =================================================
            # DOCUMENT EXPIRY
            # =================================================

            "insurance_expiry": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "fitness_expiry": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "permit_expiry": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "pollution_expiry": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

        labels = {

            "bus_number": "Bus Number",

            "registration_number": "Registration Number",

            "bus_name": "Bus Name",

            "manufacturer": "Manufacturer",

            "model_name": "Model Name",

            "manufacture_year": "Manufacture Year",

            "capacity": "Capacity",

            "fuel_type": "Fuel Type",

            "driver": "Driver",

            "route": "Route",

            "tracker_device_id": "Tracker Device ID",

            "tracker_imei": "Tracker IMEI",

            "tracker_provider": "Tracker Provider",

            "tracker_is_active": "GPS Tracker Active",

            "status": "Bus Status",

            "is_active": "Bus Active",

            "insurance_expiry": "Insurance Expiry",

            "fitness_expiry": "Fitness Expiry",

            "permit_expiry": "Permit Expiry",

            "pollution_expiry": "Pollution Expiry",
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # =================================================
        # DRIVER
        # =================================================

        if "driver" in self.fields:

            self.fields["driver"].required = False

            self.fields["driver"].empty_label = "Select Driver"

            drivers = EmployeeAdmissionApplication.objects.filter(
                status="account_created",
                credential__is_active=True,
                credential__user__is_active=True,
                credential__user__profile__is_active=True,
                credential__user__profile__role="bus_driver",
            )
            self.fields["driver"].queryset = drivers.distinct().order_by(
                "first_name",
                "last_name",
            )

        # =================================================
        # ROUTE
        # =================================================

        if "route" in self.fields:

            self.fields["route"].required = False

            self.fields["route"].empty_label = "Select Route"

        # =================================================
        # GPS OPTIONAL FIELDS
        # =================================================

        if "tracker_device_id" in self.fields:

            self.fields["tracker_device_id"].required = False

        if "tracker_imei" in self.fields:

            self.fields["tracker_imei"].required = False

        if "tracker_provider" in self.fields:

            self.fields["tracker_provider"].required = False

        # =================================================
        # DOCUMENT OPTIONAL FIELDS
        # =================================================

        if "insurance_expiry" in self.fields:

            self.fields["insurance_expiry"].required = False

        if "fitness_expiry" in self.fields:

            self.fields["fitness_expiry"].required = False

        if "permit_expiry" in self.fields:

            self.fields["permit_expiry"].required = False

        if "pollution_expiry" in self.fields:

            self.fields["pollution_expiry"].required = False