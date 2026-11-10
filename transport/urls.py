from django.urls import path

from . import views


app_name = "transport"


urlpatterns = [

    # =====================================================
    # DRIVER
    # =====================================================

    path(
        "driver/my-bus/",
        views.driver_my_bus,
        name="driver_my_bus",
    ),

    path(
        "driver/my-students/",
        views.driver_students,
        name="driver_students",
    ),

    path(
        "driver/bus-location/",
        views.driver_bus_location,
        name="driver_bus_location",
    ),

    path(
        "driver/trip-history/",
        views.driver_trip_history,
        name="driver_trip_history",
    ),

    path(
        "driver/safety-alerts/",
        views.driver_safety_alerts,
        name="driver_safety_alerts",
    ),

    path(
        "driver/report-issue/",
        views.driver_report_issue,
        name="driver_report_issue",
    ),

    path(
        "driver/emergency/",
        views.driver_emergency,
        name="driver_emergency",
    ),


    # =====================================================
    # VP - MAIN BUS DASHBOARD
    # =====================================================

    path(
        "vp/buses/",
        views.vp_buses_dashboard,
        name="vp_buses_dashboard",
    ),

    # =====================================================
    # VP - ALL BUSES
    # =====================================================

    path(
        "vp/buses/all/",
        views.vp_all_buses,
        name="vp_all_buses",
    ),

    # =====================================================
    # VP - BUS ASSIGNMENT
    # =====================================================

    path(
        "vp/bus-assignment/",
        views.vp_bus_assignment,
        name="vp_bus_assignment",
    ),

    # =====================================================
    # VP - STUDENT ASSIGNMENT
    # =====================================================

    path(
        "vp/student-assignment/",
        views.vp_student_assignment,
        name="vp_student_assignment",
    ),
    path(
    "vp/student-assignments/students-by-grade/",
    views.students_by_grade,
    name="students_by_grade",),
    path(
    "vp/student-assignments/<int:assignment_id>/edit/",
    views.vp_student_assignment_edit,
    name="vp_student_assignment_edit",),

    path(
        "vp/trip-history/",
        views.vp_trip_history,
        name="vp_trip_history",
    ),

    # =====================================================
    # VP - ALL BUS LOCATION
    # =====================================================

    path(
        "vp/bus-location/",
        views.vp_bus_location,
        name="vp_bus_location",
    ),

    # =====================================================
    # VP - ALL SAFETY ALERTS
    # =====================================================

    path(
        "vp/safety-alerts/",
        views.vp_safety_alerts,
        name="vp_safety_alerts",
    ),

    # =====================================================
    # VP - ALL BUS ISSUES
    # =====================================================

    path(
        "vp/bus-issues/",
        views.vp_bus_issues,
        name="vp_bus_issues",
    ),

    # =====================================================
    # VP - ROUTES
    # =====================================================

    path(
        "vp/bus-routes/",
        views.vp_bus_routes,
        name="vp_bus_routes",
    ),

    path(
        "vp/bus-routes/<int:route_id>/",
        views.vp_route_detail,
        name="vp_route_detail",
    ),

    path(
        "vp/bus-routes/<int:route_id>/delete/",
        views.vp_delete_route,
        name="vp_delete_route",
    ),

    path(
        "vp/bus-stops/<int:stop_id>/delete/",
        views.vp_delete_stop,
        name="vp_delete_stop",
    ),


    # =====================================================
    # ACCOUNTANT
    # =====================================================

    path(
        "accountant/expenses/",
        views.accountant_expenses,
        name="accountant_expenses",
    ),


    # =====================================================
    # STUDENT
    # =====================================================

    path(
        "student/live-bus/",
        views.student_live_bus,
        name="student_live_bus",
    ),

    path(
        "student/live-bus/data/",
        views.student_live_bus_data,
        name="student_live_bus_data",
    ),


    # =====================================================
    # ADMISSION TRANSPORT APIs
    # =====================================================

    path(
        "route-options/",
        views.route_options,
        name="route_options",
    ),

    path(
        "stop-options/",
        views.stop_options,
        name="stop_options",
    ),
]