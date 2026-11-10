from django.conf import settings
from django.db import models

from admissions.models import (
    StudentAdmissionApplication,
    EmployeeAdmissionApplication,
)

class Bus(models.Model):

    BUS_STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("maintenance", "Maintenance"),
    )

    FUEL_TYPE_CHOICES = (
        ("diesel", "Diesel"),
        ("petrol", "Petrol"),
        ("cng", "CNG"),
        ("electric", "Electric"),
    )

    # -----------------------------------------------------
    # BASIC BUS DETAILS
    # -----------------------------------------------------

    bus_number = models.CharField(
        max_length=30,
        unique=True,
    )

    registration_number = models.CharField(
        max_length=30,
        unique=True,
    )

    bus_name = models.CharField(
        max_length=100,
        blank=True,
    )

    manufacturer = models.CharField(
        max_length=100,
        blank=True,
    )

    model_name = models.CharField(
        max_length=100,
        blank=True,
    )

    manufacture_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    capacity = models.PositiveIntegerField(
        default=40,
    )

    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        default="diesel",
    )

    # -----------------------------------------------------
    # DRIVER
    # Existing EmployeeAdmissionApplication is reused
    # -----------------------------------------------------

    driver = models.ForeignKey(
        EmployeeAdmissionApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_buses",
    )

    # -----------------------------------------------------
    # ROUTE
    # -----------------------------------------------------

    route = models.ForeignKey(
        "transport.BusRoute",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="buses",
    )

    # -----------------------------------------------------
    # GPS TRACKER
    # Physical Onelap GPS tracker details
    # -----------------------------------------------------

    tracker_device_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    tracker_imei = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    tracker_provider = models.CharField(
        max_length=100,
        default="Onelap",
        blank=True,
    )

    tracker_is_active = models.BooleanField(
        default=False,
    )

    # -----------------------------------------------------
    # CURRENT GPS LOCATION
    # These fields are for fast live dashboard display
    # -----------------------------------------------------

    current_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    current_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    current_speed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Speed in km/h",
    )

    current_ignition = models.BooleanField(
        null=True,
        blank=True,
    )

    last_location_update = models.DateTimeField(
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # BUS STATUS
    # -----------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=BUS_STATUS_CHOICES,
        default="active",
    )

    is_active = models.BooleanField(
        default=True,
    )

    # -----------------------------------------------------
    # IMPORTANT DOCUMENT DETAILS
    # -----------------------------------------------------

    insurance_expiry = models.DateField(
        null=True,
        blank=True,
    )

    fitness_expiry = models.DateField(
        null=True,
        blank=True,
    )

    permit_expiry = models.DateField(
        null=True,
        blank=True,
    )

    pollution_expiry = models.DateField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["bus_number"]

    def __str__(self):
        return f"{self.bus_number} - {self.registration_number}"

class BusRoute(models.Model):

    route_name = models.CharField(
        max_length=150,
    )

    route_code = models.CharField(
        max_length=50,
        unique=True,
    )

    start_location = models.CharField(
        max_length=200,
    )

    end_location = models.CharField(
        max_length=200,
    )

    total_distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    estimated_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["route_name"]

    def __str__(self):
        return f"{self.route_name} ({self.route_code})"

class BusStop(models.Model):

    route = models.ForeignKey(
        BusRoute,
        on_delete=models.CASCADE,
        related_name="stops",
    )

    stop_name = models.CharField(
        max_length=150,
    )

    stop_order = models.PositiveIntegerField()

    address = models.CharField(
        max_length=250,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    pickup_time = models.TimeField(
        null=True,
        blank=True,
    )

    drop_time = models.TimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "route",
            "stop_order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["route", "stop_order"],
                name="unique_route_stop_order",
            )
        ]

    def __str__(self):
        return f"{self.route.route_name} - {self.stop_order}. {self.stop_name}"

class BusTrip(models.Model):

    TRIP_TYPE_CHOICES = (
        ("morning", "Morning"),
        ("afternoon", "Afternoon"),
        ("special", "Special"),
    )

    TRIP_STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("started", "Started"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="trips",
    )

    route = models.ForeignKey(
        BusRoute,
        on_delete=models.PROTECT,
        related_name="trips",
    )

    driver = models.ForeignKey(
        EmployeeAdmissionApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bus_trips",
    )

    trip_date = models.DateField()

    trip_type = models.CharField(
        max_length=20,
        choices=TRIP_TYPE_CHOICES,
    )

    scheduled_start_time = models.TimeField(
        null=True,
        blank=True,
    )

    actual_start_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    actual_end_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    current_stop = models.ForeignKey(
        BusStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_trips",
    )

    status = models.CharField(
        max_length=20,
        choices=TRIP_STATUS_CHOICES,
        default="scheduled",
    )

    driver_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-trip_date",
            "-scheduled_start_time",
        ]

    def __str__(self):
        return (
            f"{self.bus.bus_number} - "
            f"{self.trip_date} - "
            f"{self.get_trip_type_display()}"
        )

class StudentBusAssignment(models.Model):

    student = models.ForeignKey(
        StudentAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="bus_assignments",
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="student_assignments",
    )

    route = models.ForeignKey(
        BusRoute,
        on_delete=models.PROTECT,
        related_name="student_assignments",
    )

    pickup_stop = models.ForeignKey(
        BusStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pickup_students",
    )

    drop_stop = models.ForeignKey(
        BusStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drop_students",
    )

    pickup_required = models.BooleanField(
        default=True,
    )

    drop_required = models.BooleanField(
        default=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    assigned_date = models.DateField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["student__first_name"]

    def __str__(self):
        return (
            f"{self.student.application_id} - "
            f"{self.bus.bus_number}"
        )

class EmployeeBusAssignment(models.Model):
    employee = models.ForeignKey(
        EmployeeAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="bus_assignments",
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="employee_assignments",
    )

    route = models.ForeignKey(
        BusRoute,
        on_delete=models.PROTECT,
        related_name="employee_assignments",
    )

    pickup_stop = models.ForeignKey(
        BusStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_pickup_assignments",
    )

    drop_stop = models.ForeignKey(
        BusStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_drop_assignments",
    )

    pickup_required = models.BooleanField(
        default=True
    )

    drop_required = models.BooleanField(
        default=True
    )

    is_active = models.BooleanField(
        default=True
    )

    assigned_date = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["employee__first_name"]

    def __str__(self):
        return f"{self.employee.application_id} - {self.bus.bus_number}"

class BusLocation(models.Model):

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="location_history",
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    speed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )

    ignition = models.BooleanField(
        null=True,
        blank=True,
    )

    gps_timestamp = models.DateTimeField(
        null=True,
        blank=True,
    )

    received_at = models.DateTimeField(
        auto_now_add=True,
    )

    # Original tracker/device information
    device_id = models.CharField(
        max_length=100,
        blank=True,
    )

    imei = models.CharField(
        max_length=50,
        blank=True,
    )

    class Meta:
        ordering = ["-gps_timestamp", "-received_at"]

    def __str__(self):
        return (
            f"{self.bus.bus_number} - "
            f"{self.latitude}, {self.longitude}"
        )

class BusExpense(models.Model):

    EXPENSE_TYPE_CHOICES = (
        ("fuel", "Fuel"),
        ("maintenance", "Maintenance"),
        ("repair", "Repair"),
        ("tyre", "Tyre"),
        ("service", "Service"),
        ("other", "Other"),
    )

    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="expenses",
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bus_expenses_reported",
    )

    expense_type = models.CharField(
        max_length=30,
        choices=EXPENSE_TYPE_CHOICES,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    expense_date = models.DateField()

    description = models.TextField(
        blank=True,
    )

    bill = models.FileField(
        upload_to="transport/expenses/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="submitted",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bus_expenses_reviewed",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return (
            f"{self.bus.bus_number} - "
            f"{self.get_expense_type_display()} - "
            f"{self.amount}"
        )

class BusIssue(models.Model):

    ISSUE_TYPE_CHOICES = (
        ("engine", "Engine"),
        ("tyre", "Tyre"),
        ("brake", "Brake"),
        ("battery", "Battery"),
        ("gps", "GPS"),
        ("electrical", "Electrical"),
        ("ac", "AC"),
        ("other", "Other"),
    )

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    )

    STATUS_CHOICES = (
        ("reported", "Reported"),
        ("under_review", "Under Review"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="issues",
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bus_issues_reported",
    )

    issue_type = models.CharField(
        max_length=30,
        choices=ISSUE_TYPE_CHOICES,
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    photo = models.ImageField(
        upload_to="transport/issues/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="reported",
    )

    resolution_notes = models.TextField(
        blank=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.bus.bus_number} - {self.title}"

class SafetyAlert(models.Model):

    ALERT_TYPE_CHOICES = (
        ("overspeed", "Overspeed"),
        ("route_deviation", "Route Deviation"),
        ("gps_offline", "GPS Offline"),
        ("unauthorized_stop", "Unauthorized Stop"),
        ("ignition", "Ignition Alert"),
        ("emergency", "Emergency"),
        ("other", "Other"),
    )

    SEVERITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    )

    STATUS_CHOICES = (
        ("new", "New"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="safety_alerts",
    )

    trip = models.ForeignKey(
        BusTrip,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="safety_alerts",
    )

    alert_type = models.CharField(
        max_length=30,
        choices=ALERT_TYPE_CHOICES,
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="medium",
    )

    title = models.CharField(
        max_length=200,
    )

    message = models.TextField()

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transport_alerts_acknowledged",
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.bus.bus_number} - "
            f"{self.get_alert_type_display()} - "
            f"{self.status}"
        )