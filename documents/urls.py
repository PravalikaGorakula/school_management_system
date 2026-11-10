from django.urls import path

from . import views


app_name = "documents"


urlpatterns = [

    # =====================================================
    # DOCUMENT HOME
    # =====================================================

    path(
        "",
        views.documents_home,
        name="home",
    ),

    # =====================================================
    # UPLOAD DOCUMENT
    # =====================================================

    path(
        "upload/",
        views.upload_document,
        name="upload",
    ),

    # =====================================================
    # VIEW DOCUMENT
    # =====================================================

    path(
        "view/<int:document_id>/",
        views.view_document,
        name="view",
    ),

    # =====================================================
    # DOWNLOAD DOCUMENT
    # =====================================================

    path(
        "download/<int:document_id>/",
        views.download_document,
        name="download",
    ),
    # =====================================================
# STUDENT DOCUMENTS
# =====================================================

path(
    "students/",
    views.student_documents,
    name="student_documents",
),

path(
    "students/<str:application_id>/",
    views.student_document_details,
    name="student_document_details",
),


# =====================================================
# EMPLOYEE DOCUMENTS
# =====================================================

path(
    "employees/",
    views.employee_documents,
    name="employee_documents",
),

path(
    "employees/<str:application_id>/",
    views.employee_document_details,
    name="employee_document_details",
),


# =====================================================
# APPLICATION DOCUMENT ACTIONS
# =====================================================

path(
    "application/<str:application_type>/<str:application_id>/<str:field_name>/view/",
    views.view_application_document,
    name="view_application_document",
),

path(
    "application/<str:application_type>/<str:application_id>/<str:field_name>/edit/",
    views.edit_application_document,
    name="edit_application_document",
),

path(
    "application/<str:application_type>/<str:application_id>/<str:field_name>/delete/",
    views.delete_application_document,
    name="delete_application_document",
),
]