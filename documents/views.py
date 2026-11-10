from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from .forms import DocumentForm
from .models import Document
from .permissions import (
    get_role_permissions,
    has_document_permission,
)

from admissions.models import (
    StudentAdmissionApplication,
    EmployeeAdmissionApplication,
)


@login_required
def documents_home(request):

    user = request.user

    permissions = get_role_permissions(user)

    documents = Document.objects.none()

    role = getattr(
        getattr(user, "profile", None),
        "role",
        None,
    )

    # =====================================================
    # STUDENT
    # =====================================================

    if role == "student":

        documents = Document.objects.filter(
            owner=user,
            category="personal",
        )


    # =====================================================
    # TEACHER
    # =====================================================

    elif role == "teacher":

        documents = Document.objects.filter(
            owner=user,
            category="personal",
        )


    # =====================================================
    # BUS DRIVER
    # =====================================================

    elif role == "bus_driver":

        documents = Document.objects.filter(
            owner=user,
            category="personal",
        )


    # =====================================================
    # PARENT
    # =====================================================

    elif role == "parent":

        documents = Document.objects.filter(
            owner=user,
        )


    # =====================================================
    # ADMIN / STAFF / MANAGEMENT
    # =====================================================

    else:

        allowed_categories = []

        category_mapping = [
            "student",
            "employee",
            "user",
            "fee",
            "report",
            "transport",
            "personal",
        ]

        for category in category_mapping:

            if permissions.get(category, False):

                allowed_categories.append(category)

        documents = Document.objects.filter(
            category__in=allowed_categories
        )


    # =====================================================
    # SELECT RELATED
    # =====================================================

    documents = documents.select_related(
        "owner",
        "uploaded_by",
    )


    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "documents": documents,

        "permissions": permissions,

        "role": role,

        "can_upload": permissions.get(
            "upload",
            False
        ),

        "can_view": permissions.get(
            "view",
            False
        ),

        "can_download": permissions.get(
            "download",
            False
        ),

        "can_manage": permissions.get(
            "manage",
            False
        ),
    }


    return render(
        request,
        "documents/documents.html",
        context,
    )


# =========================================================
# UPLOAD DOCUMENT
# =========================================================

@login_required
def upload_document(request):

    if not has_document_permission(
        request.user,
        "upload"
    ):

        return HttpResponseForbidden(
            "You do not have permission to upload documents."
        )


    if request.method == "POST":

        form = DocumentForm(
            request.POST,
            request.FILES,
        )


        if form.is_valid():

            document = form.save(
                commit=False
            )

            document.owner = request.user

            document.uploaded_by = request.user

            document.is_verified = False

            document.save()

            return redirect(
                "documents:home"
            )


    else:

        form = DocumentForm()


    context = {

        "form": form,

        "role": getattr(
            getattr(
                request.user,
                "profile",
                None
            ),
            "role",
            None,
        ),

    }


    return render(
        request,
        "documents/upload.html",
        context,
    )


# =========================================================
# VIEW DOCUMENT
# =========================================================

@login_required
def view_document(
    request,
    document_id
):

    if not has_document_permission(
        request.user,
        "view"
    ):

        return HttpResponseForbidden(
            "You do not have permission to view documents."
        )


    document = get_object_or_404(
        Document.objects.select_related(
            "owner",
            "uploaded_by",
        ),
        id=document_id,
    )


    if not can_access_document(
        request.user,
        document
    ):

        return HttpResponseForbidden(
            "You do not have permission to access this document."
        )


    if not document.file:

        raise Http404(
            "Document file does not exist."
        )


    return FileResponse(
        document.file.open("rb"),
        content_type=get_content_type(
            document.file.name
        ),
    )


# =========================================================
# DOWNLOAD DOCUMENT
# =========================================================

@login_required
def download_document(
    request,
    document_id
):

    if not has_document_permission(
        request.user,
        "download"
    ):

        return HttpResponseForbidden(
            "You do not have permission to download documents."
        )


    document = get_object_or_404(
        Document,
        id=document_id,
    )


    if not can_access_document(
        request.user,
        document
    ):

        return HttpResponseForbidden(
            "You do not have permission to access this document."
        )


    if not document.file:

        raise Http404(
            "Document file does not exist."
        )


    response = FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.file.name.split("/")[-1],
    )


    return response


# =========================================================
# DOCUMENT ACCESS CONTROL
# =========================================================

def can_access_document(
    user,
    document
):

    role = getattr(
        getattr(
            user,
            "profile",
            None
        ),
        "role",
        None,
    )


    # =====================================================
    # OWNER ACCESS
    # =====================================================

    if document.owner_id == user.id:

        if role in [
            "student",
            "teacher",
            "bus_driver",
        ]:

            return document.category == "personal"


        if role == "parent":

            return True


        return True


    # =====================================================
    # ADMISSION STAFF
    # =====================================================

    if role == "admission_staff":

        return document.category in [
            "student",
            "employee",
        ]


    # =====================================================
    # SYSTEM ADMINISTRATOR
    # =====================================================

    if role == "system_administrator":

        return document.category in [
            "student",
            "employee",
            "user",
        ]


    # =====================================================
    # VICE PRINCIPAL
    # =====================================================

    if role == "vice_principal":

        return document.category in [
            "student",
            "employee",
        ]


    # =====================================================
    # TEACHER
    # =====================================================

    if role == "teacher":

        return document.category == "student"


    # =====================================================
    # PRINCIPAL
    # =====================================================

    if role == "principal":

        return document.category in [
            "student",
            "employee",
            "report",
        ]


    # =====================================================
    # CHAIRMAN
    # =====================================================

    if role == "chairman":

        return document.category in [
            "student",
            "employee",
            "report",
        ]


    # =====================================================
    # ACCOUNTANT
    # =====================================================

    if role == "accountant":

        return document.category in [
            "student",
            "employee",
            "fee",
        ]


    # =====================================================
    # PARENT
    # =====================================================

    if role == "parent":

        return document.category == "student"


    # =====================================================
    # BUS DRIVER
    # =====================================================

    if role == "bus_driver":

        return document.category in [
            "transport",
        ]


    return False


# =========================================================
# FILE CONTENT TYPE
# =========================================================

def get_content_type(file_name):

    file_name = file_name.lower()


    if file_name.endswith(".pdf"):

        return "application/pdf"


    if (
        file_name.endswith(".jpg")
        or file_name.endswith(".jpeg")
    ):

        return "image/jpeg"


    if file_name.endswith(".png"):

        return "image/png"


    if file_name.endswith(".doc"):

        return "application/msword"


    if file_name.endswith(".docx"):

        return (
            "application/"
            "vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )


    if file_name.endswith(".xls"):

        return "application/vnd.ms-excel"


    if file_name.endswith(".xlsx"):

        return (
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )


    return "application/octet-stream"

# =========================================================
# DYNAMIC APPLICATION DOCUMENT HELPER
# =========================================================

def get_uploaded_application_documents(instance):
    """
    Dynamically finds every uploaded FileField/ImageField
    from the given admission application.

    No document names are hard-coded.
    """

    documents = []

    for field in instance._meta.get_fields():

        # Only real database fields
        if not getattr(field, "concrete", False):
            continue

        # FileField includes ImageField
        if not isinstance(field, models.FileField):
            continue

        file_value = getattr(instance, field.name, None)

        if not file_value:
            continue

        if not getattr(file_value, "name", None):
            continue

        documents.append({
            "field_name": field.name,
            "label": field.verbose_name.title(),
            "file_name": file_value.name.split("/")[-1],
            "file": file_value,
            "url": file_value.url,
        })

    return documents


def get_application_document_count(instance):
    return len(
        get_uploaded_application_documents(instance)
    )


# =========================================================
# STUDENT DOCUMENTS
# =========================================================

@login_required
def student_documents(request):

    if not has_document_permission(
        request.user,
        "view"
    ):
        return HttpResponseForbidden(
            "You do not have permission to view student documents."
        )

    students = StudentAdmissionApplication.objects.all().order_by(
        "-id"
    )

    search = request.GET.get("search", "").strip()

    if search:

        students = students.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(application_id__icontains=search)
        )

    student_rows = []

    for student in students:

        uploaded_documents = (
            get_uploaded_application_documents(student)
        )

        student_rows.append({
            "student": student,
            "document_count": len(uploaded_documents),
        })

    context = {
        "students": student_rows,
        "search": search,
        "can_manage": has_document_permission(
            request.user,
            "manage"
        ),
    }

    return render(
        request,
        "documents/student_documents.html",
        context,
    )


# =========================================================
# STUDENT DOCUMENT DETAILS
# =========================================================

@login_required
def student_document_details(
    request,
    application_id
):

    if not has_document_permission(
        request.user,
        "view"
    ):
        return HttpResponseForbidden(
            "You do not have permission to view student documents."
        )

    student = get_object_or_404(
        StudentAdmissionApplication,
        application_id=application_id,
    )

    documents = get_uploaded_application_documents(
        student
    )

    context = {
        "application": student,
        "application_type": "student",
        "documents": documents,
        "can_manage": has_document_permission(
            request.user,
            "manage"
        ),
    }

    return render(
        request,
        "documents/application_documents.html",
        context,
    )


# =========================================================
# EMPLOYEE DOCUMENTS
# =========================================================

@login_required
def employee_documents(request):

    if not has_document_permission(
        request.user,
        "view"
    ):
        return HttpResponseForbidden(
            "You do not have permission to view employee documents."
        )

    employees = EmployeeAdmissionApplication.objects.all().order_by(
        "-id"
    )

    search = request.GET.get("search", "").strip()

    if search:

        employees = employees.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(application_id__icontains=search)
        )

    employee_rows = []

    for employee in employees:

        uploaded_documents = (
            get_uploaded_application_documents(employee)
        )

        employee_rows.append({
            "employee": employee,
            "document_count": len(uploaded_documents),
        })

    context = {
        "employees": employee_rows,
        "search": search,
        "can_manage": has_document_permission(
            request.user,
            "manage"
        ),
    }

    return render(
        request,
        "documents/employee_documents.html",
        context,
    )


# =========================================================
# EMPLOYEE DOCUMENT DETAILS
# =========================================================

@login_required
def employee_document_details(
    request,
    application_id
):

    if not has_document_permission(
        request.user,
        "view"
    ):
        return HttpResponseForbidden(
            "You do not have permission to view employee documents."
        )

    employee = get_object_or_404(
        EmployeeAdmissionApplication,
        application_id=application_id,
    )

    documents = get_uploaded_application_documents(
        employee
    )

    context = {
        "application": employee,
        "application_type": "employee",
        "documents": documents,
        "can_manage": has_document_permission(
            request.user,
            "manage"
        ),
    }

    return render(
        request,
        "documents/application_documents.html",
        context,
    )


# =========================================================
# GET APPLICATION INSTANCE
# =========================================================

def get_application_instance(
    application_type,
    application_id
):

    if application_type == "student":

        return get_object_or_404(
            StudentAdmissionApplication,
            application_id=application_id,
        )

    if application_type == "employee":

        return get_object_or_404(
            EmployeeAdmissionApplication,
            application_id=application_id,
        )

    raise Http404(
        "Invalid application type."
    )


# =========================================================
# VIEW APPLICATION DOCUMENT
# =========================================================

@login_required
def view_application_document(
    request,
    application_type,
    application_id,
    field_name,
):

    if not has_document_permission(
        request.user,
        "view"
    ):
        return HttpResponseForbidden(
            "You do not have permission to view documents."
        )

    application = get_application_instance(
        application_type,
        application_id,
    )

    field = application._meta.get_field(
        field_name
    )

    if not isinstance(
        field,
        models.FileField
    ):
        raise Http404(
            "Invalid document field."
        )

    file_value = getattr(
        application,
        field_name,
        None
    )

    if not file_value:
        raise Http404(
            "Document does not exist."
        )

    return FileResponse(
        file_value.open("rb"),
        content_type=get_content_type(
            file_value.name
        ),
    )


# =========================================================
# EDIT APPLICATION DOCUMENT
# =========================================================

@login_required
def edit_application_document(
    request,
    application_type,
    application_id,
    field_name,
):

    if not has_document_permission(
        request.user,
        "manage"
    ):
        return HttpResponseForbidden(
            "You do not have permission to edit documents."
        )

    application = get_application_instance(
        application_type,
        application_id,
    )

    try:

        field = application._meta.get_field(
            field_name
        )

    except Exception:

        raise Http404(
            "Document field does not exist."
        )

    if not isinstance(
        field,
        models.FileField
    ):
        raise Http404(
            "Invalid document field."
        )

    current_file = getattr(
        application,
        field_name,
        None
    )

    if request.method == "POST":

        new_file = request.FILES.get(
            field_name
        )

        if not new_file:

            return render(
                request,
                "documents/edit_application_document.html",
                {
                    "application": application,
                    "application_type": application_type,
                    "field": field,
                    "current_file": current_file,
                    "error": "Please select a new file.",
                },
            )

        # Delete old physical file
        if current_file:

            try:
                current_file.delete(
                    save=False
                )
            except Exception:
                pass

        setattr(
            application,
            field_name,
            new_file
        )

        application.save(
            update_fields=[
                field_name,
                "updated_at",
            ]
        )

        return redirect(
            "documents:application_document_details",
            application_type=application_type,
            application_id=application_id,
        )

    return render(
        request,
        "documents/edit_application_document.html",
        {
            "application": application,
            "application_type": application_type,
            "field": field,
            "current_file": current_file,
        },
    )


# =========================================================
# DELETE APPLICATION DOCUMENT
# =========================================================

@login_required
def delete_application_document(
    request,
    application_type,
    application_id,
    field_name,
):

    if not has_document_permission(
        request.user,
        "manage"
    ):
        return HttpResponseForbidden(
            "You do not have permission to delete documents."
        )

    if request.method != "POST":

        return HttpResponseForbidden(
            "Invalid request method."
        )

    application = get_application_instance(
        application_type,
        application_id,
    )

    try:

        field = application._meta.get_field(
            field_name
        )

    except Exception:

        raise Http404(
            "Document field does not exist."
        )

    if not isinstance(
        field,
        models.FileField
    ):
        raise Http404(
            "Invalid document field."
        )

    file_value = getattr(
        application,
        field_name,
        None
    )

    if file_value:

        try:
            file_value.delete(
                save=False
            )
        except Exception:
            pass

    setattr(
        application,
        field_name,
        None
    )

    application.save(
        update_fields=[
            field_name,
            "updated_at",
        ]
    )

    return redirect(
        "documents:application_document_details",
        application_type=application_type,
        application_id=application_id,
    )