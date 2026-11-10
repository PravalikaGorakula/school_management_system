from django.contrib import admin

from .models import (
    Bus,
    BusRoute,
    BusStop,
    BusTrip,
    StudentBusAssignment,
    EmployeeBusAssignment,
    BusLocation,
    BusExpense,
    BusIssue,
    SafetyAlert,
)

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):

    list_display = (
        "bus_number",
        "registration_number",
        "driver",
        "route",
        "tracker_is_active",
        "status",
        "is_active",
        "last_location_update",
    )

    list_filter = (
        "status",
        "is_active",
        "tracker_is_active",
        "fuel_type",
    )

    search_fields = (
        "bus_number",
        "registration_number",
        "bus_name",
        "tracker_device_id",
        "tracker_imei",
    )

    list_select_related = (
        "driver",
        "route",
    )

@admin.register(BusRoute)
class BusRouteAdmin(admin.ModelAdmin):

    list_display = (
        "route_code",
        "route_name",
        "start_location",
        "end_location",
        "total_distance_km",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "route_code",
        "route_name",
        "start_location",
        "end_location",
    )

@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):

    list_display = (
        "stop_name",
        "route",
        "stop_order",
        "pickup_time",
        "drop_time",
        "is_active",
    )

    list_filter = (
        "route",
        "is_active",
    )

    search_fields = (
        "stop_name",
        "address",
    )

    ordering = (
        "route",
        "stop_order",
    )

@admin.register(BusTrip)
class BusTripAdmin(admin.ModelAdmin):

    list_display = (
        "bus",
        "route",
        "driver",
        "trip_date",
        "trip_type",
        "status",
        "current_stop",
    )

    list_filter = (
        "trip_type",
        "status",
        "trip_date",
    )

    search_fields = (
        "bus__bus_number",
        "route__route_name",
    )

    date_hierarchy = "trip_date"

    list_select_related = (
        "bus",
        "route",
        "driver",
        "current_stop",
    )

@admin.register(StudentBusAssignment)
class StudentBusAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "bus",
        "route",
        "pickup_stop",
        "drop_stop",
        "pickup_required",
        "drop_required",
        "is_active",
    )

    list_filter = (
        "bus",
        "route",
        "pickup_required",
        "drop_required",
        "is_active",
    )

    search_fields = (
        "student__application_id",
        "bus__bus_number",
        "route__route_name",
    )

    list_select_related = (
        "student",
        "bus",
        "route",
        "pickup_stop",
        "drop_stop",
    )

@admin.register(EmployeeBusAssignment)
class EmployeeBusAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "employee",
        "bus",
        "route",
        "pickup_stop",
        "drop_stop",
        "pickup_required",
        "drop_required",
        "is_active",
        "assigned_date",
    )

    list_filter = (
        "is_active",
        "pickup_required",
        "drop_required",
        "route",
        "bus",
    )

    search_fields = (
        "employee__application_id",
        "employee__first_name",
        "employee__last_name",
        "bus__bus_number",
        "bus__registration_number",
        "route__route_name",
        "pickup_stop__stop_name",
        "drop_stop__stop_name",
    )

    autocomplete_fields = (
        "employee",
        "bus",
        "route",
        "pickup_stop",
        "drop_stop",
    )

@admin.register(BusLocation)
class BusLocationAdmin(admin.ModelAdmin):

    list_display = (
        "bus",
        "latitude",
        "longitude",
        "speed",
        "ignition",
        "gps_timestamp",
        "received_at",
    )

    list_filter = (
        "ignition",
        "bus",
    )

    search_fields = (
        "bus__bus_number",
        "device_id",
        "imei",
    )

    date_hierarchy = "received_at"

    list_select_related = (
        "bus",
    )

@admin.register(BusExpense)
class BusExpenseAdmin(admin.ModelAdmin):

    list_display = (
        "bus",
        "expense_type",
        "amount",
        "expense_date",
        "reported_by",
        "status",
    )

    list_filter = (
        "expense_type",
        "status",
        "expense_date",
    )

    search_fields = (
        "bus__bus_number",
        "description",
    )

    date_hierarchy = "expense_date"

    list_select_related = (
        "bus",
        "reported_by",
        "reviewed_by",
    )

@admin.register(BusIssue)
class BusIssueAdmin(admin.ModelAdmin):

    list_display = (
        "bus",
        "issue_type",
        "priority",
        "title",
        "status",
        "reported_by",
        "created_at",
    )

    list_filter = (
        "issue_type",
        "priority",
        "status",
    )

    search_fields = (
        "bus__bus_number",
        "title",
        "description",
    )

    date_hierarchy = "created_at"

    list_select_related = (
        "bus",
        "reported_by",
    )

@admin.register(SafetyAlert)
class SafetyAlertAdmin(admin.ModelAdmin):

    list_display = (
        "bus",
        "alert_type",
        "severity",
        "title",
        "status",
        "created_at",
        "acknowledged_by",
    )

    list_filter = (
        "alert_type",
        "severity",
        "status",
    )

    search_fields = (
        "bus__bus_number",
        "title",
        "message",
    )

    date_hierarchy = "created_at"

    list_select_related = (
        "bus",
        "trip",
        "acknowledged_by",
    )