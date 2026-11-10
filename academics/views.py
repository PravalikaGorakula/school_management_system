from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseForbidden, FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from exams.models import ExamMark

from .models import (
    ClassSection,
    Subject,
    SubjectEmployeeAssignment,
    TimetableEntry,
    SubjectPeriodRequirement,
    SchoolTimetableConfig,
    PeriodDefinition,
    TimetablePlan,
    StudentTeacherMessage,
    Assignment,
    AssignmentSubmission,
)

from .forms import (
    SubjectEmployeeAssignmentForm,
    TimetableEntryForm,
    ClassSectionForm,
    SubjectForm,
    SubjectPeriodRequirementForm,
)
from admissions.models import (
    StudentAdmissionApplication,
    ParentStudent,
    ParentMessage,
)
def get_academic_student(request):
    """
    Student: own academic record.
    Parent: only a child linked through ParentStudent.
    Parent can select a child using ?student_id=<id>.
    """

    user = request.user
    role = str(user.profile.role).lower()

    if role == "student":
        student = (
            StudentAdmissionApplication.objects
            .filter(
                credential__user=user,
                credential__is_active=True,
                status="account_created",
            )
            .select_related("class_section")
            .first()
        )

        return student

    if role == "parent":
        links = (
            ParentStudent.objects
            .filter(
                parent=user,
                is_active=True,
                student__status="account_created",
            )
            .select_related(
                "student",
                "student__class_section",
            )
        )

        student_id = request.GET.get("student_id", "").strip()

        if student_id:
            link = links.filter(
                student_id=student_id
            ).first()
        else:
            link = links.first()

        return link.student if link else None

    return None


def get_parent_children(user):
    """
    Return only children linked to the logged-in parent.
    """

    if not hasattr(user, "profile"):
        return StudentAdmissionApplication.objects.none()

    if str(user.profile.role).lower() != "parent":
        return StudentAdmissionApplication.objects.none()

    return (
        StudentAdmissionApplication.objects
        .filter(
            parent_links__parent=user,
            parent_links__is_active=True,
            status="account_created",
        )
        .select_related("class_section")
        .distinct()
        .order_by("first_name", "last_name")
    )

def is_vice_principal(user):
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role == "vice_principal"
    )

@login_required
def class_sections(request):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to access Class & Sections."
        )

    # =========================================================
    # SELECTED CLASS SECTION FOR STUDENT MANAGEMENT
    # =========================================================

    manage_students_id = request.GET.get(
        "manage_students",
        ""
    ).strip()

    selected_class_section = None

    if manage_students_id:

        try:
            selected_class_section = (
                ClassSection.objects
                .select_related("class_teacher")
                .get(id=int(manage_students_id))
            )

        except (
            ValueError,
            ClassSection.DoesNotExist,
        ):
            selected_class_section = None

    # =========================================================
    # POST ACTIONS
    # =========================================================

    if request.method == "POST":

        action = request.POST.get(
            "action",
            ""
        ).strip()

        # =====================================================
        # ASSIGN STUDENTS
        # =====================================================

        if action == "assign_students":

            class_section_id = request.POST.get(
                "class_section_id"
            )

            student_ids = request.POST.getlist(
                "student_ids"
            )

            if not class_section_id:

                messages.error(
                    request,
                    "Class & Section was not selected."
                )

                return redirect(
                    "academics:class_sections"
                )

            class_section = get_object_or_404(
                ClassSection,
                id=class_section_id
            )

            # -------------------------------------------------
            # CHECK CLASS STATUS
            # -------------------------------------------------

            if class_section.status == "Inactive":

                messages.error(
                    request,
                    "Students cannot be assigned to an inactive class section."
                )

                return redirect(
                    f"/academics/class-sections/"
                    f"?manage_students={class_section.id}"
                )

            # -------------------------------------------------
            # CHECK STUDENT SELECTION
            # -------------------------------------------------

            if not student_ids:

                messages.error(
                    request,
                    "Please select at least one student."
                )

                return redirect(
                    f"/academics/class-sections/"
                    f"?manage_students={class_section.id}"
                )

            # -------------------------------------------------
            # CURRENT STUDENT COUNT
            # -------------------------------------------------

            current_count = (
                StudentAdmissionApplication.objects
                .filter(
                    class_section=class_section,
                    status="account_created",
                )
                .count()
            )

            available_capacity = (
                class_section.capacity - current_count
            )

            # -------------------------------------------------
            # CAPACITY CHECK
            # -------------------------------------------------

            if available_capacity <= 0:

                class_section.status = "Full"

                class_section.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                messages.error(
                    request,
                    "This class section has reached its capacity."
                )

                return redirect(
                    f"/academics/class-sections/"
                    f"?manage_students={class_section.id}"
                )

            # -------------------------------------------------
            # GET ELIGIBLE STUDENTS
            #
            # Only:
            # account_created
            # class_section = NULL
            # -------------------------------------------------

            students = (
                StudentAdmissionApplication.objects
                .filter(
                    id__in=student_ids,
                    status="account_created",
                    class_section__isnull=True,
                )
            )

            selected_count = students.count()

            # -------------------------------------------------
            # NO ELIGIBLE STUDENTS
            # -------------------------------------------------

            if selected_count == 0:

                messages.error(
                    request,
                    "No eligible students were selected."
                )

                return redirect(
                    f"/academics/class-sections/"
                    f"?manage_students={class_section.id}"
                )

            # -------------------------------------------------
            # CAPACITY CHECK
            # -------------------------------------------------

            if selected_count > available_capacity:

                messages.error(
                    request,
                    (
                        f"Only {available_capacity} student(s) "
                        f"can be assigned. "
                        f"Selected: {selected_count}."
                    )
                )

                return redirect(
                    f"/academics/class-sections/"
                    f"?manage_students={class_section.id}"
                )

            # -------------------------------------------------
            # ASSIGN STUDENTS
            # -------------------------------------------------

            students.update(
                class_section=class_section
            )

            # -------------------------------------------------
            # UPDATE CLASS STATUS
            # -------------------------------------------------

            new_count = (
                StudentAdmissionApplication.objects
                .filter(
                    class_section=class_section,
                    status="account_created",
                )
                .count()
            )

            if new_count >= class_section.capacity:

                class_section.status = "Full"

            elif class_section.status == "Full":

                class_section.status = "Active"

            class_section.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                (
                    f"{selected_count} student(s) "
                    f"assigned to "
                    f"{class_section.grade} - "
                    f"{class_section.section} successfully."
                )
            )

            return redirect(
                f"/academics/class-sections/"
                f"?manage_students={class_section.id}"
            )

        # =====================================================
        # REMOVE STUDENT
        # =====================================================

        elif action == "remove_student":

            class_section_id = request.POST.get(
                "class_section_id"
            )

            student_id = request.POST.get(
                "student_id"
            )

            if not class_section_id or not student_id:

                messages.error(
                    request,
                    "Invalid student or class section."
                )

                return redirect(
                    "academics:class_sections"
                )

            class_section = get_object_or_404(
                ClassSection,
                id=class_section_id
            )

            student = get_object_or_404(
                StudentAdmissionApplication,
                id=student_id,
                class_section=class_section,
            )

            # -------------------------------------------------
            # REMOVE CLASS ASSIGNMENT
            # -------------------------------------------------

            student.class_section = None

            student.save(
                update_fields=[
                    "class_section"
                ]
            )

            # -------------------------------------------------
            # IF CLASS WAS FULL, MAKE ACTIVE
            # -------------------------------------------------

            if class_section.status == "Full":

                class_section.status = "Active"

                class_section.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            messages.success(
                request,
                (
                    f"{student.first_name} "
                    f"{student.last_name} removed from "
                    f"{class_section.grade} - "
                    f"{class_section.section}."
                )
            )

            return redirect(
                f"/academics/class-sections/"
                f"?manage_students={class_section.id}"
            )

    # =========================================================
    # CLASS & SECTION LIST
    # =========================================================

    classes = (
        ClassSection.objects
        .select_related("class_teacher")
        .order_by(
            "grade",
            "section"
        )
    )

    # =========================================================
    # SEARCH CLASS / SECTION
    # =========================================================

    search = request.GET.get(
        "q",
        ""
    ).strip()

    if search:

        classes = classes.filter(
            Q(
                grade__icontains=search
            )
            | Q(
                section__icontains=search
            )
            | Q(
                grade_group__icontains=search
            )
            | Q(
                class_teacher__first_name__icontains=search
            )
            | Q(
                class_teacher__last_name__icontains=search
            )
            | Q(
                class_teacher__username__icontains=search
            )
        )

    # =========================================================
    # ACADEMIC YEAR FILTER
    # =========================================================

    academic_year = request.GET.get(
        "academic_year",
        ""
    ).strip()

    if academic_year:

        classes = classes.filter(
            academic_year=academic_year
        )

    # =========================================================
    # STATUS FILTER
    # =========================================================

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if status:

        classes = classes.filter(
            status=status
        )

    # =========================================================
    # SUMMARY COUNTS
    # =========================================================

    total_classes = (
        ClassSection.objects
        .values("grade")
        .distinct()
        .count()
    )

    total_sections = (
        ClassSection.objects.count()
    )

    class_teachers = (
        ClassSection.objects
        .filter(
            class_teacher__isnull=False
        )
        .values(
            "class_teacher"
        )
        .distinct()
        .count()
    )

    total_students = (
        StudentAdmissionApplication.objects
        .filter(
            status="account_created",
            class_section__isnull=False,
        )
        .count()
    )

    # =========================================================
    # ACADEMIC YEARS
    # =========================================================

    academic_years = (
        ClassSection.objects
        .values_list(
            "academic_year",
            flat=True
        )
        .distinct()
        .order_by("-academic_year")
    )

    # =========================================================
    # STUDENT COUNTS FOR EACH CLASS SECTION
    # =========================================================

    for class_section in classes:

        class_section.students_count = (
            StudentAdmissionApplication.objects
            .filter(
                class_section=class_section,
                status="account_created",
            )
            .count()
        )

    # =========================================================
    # STUDENTS FOR SELECTED CLASS
    # =========================================================

    available_students = (
        StudentAdmissionApplication.objects.none()
    )

    assigned_students = (
        StudentAdmissionApplication.objects.none()
    )

    student_search = ""

    if selected_class_section:

        # -----------------------------------------------------
        # STUDENT SEARCH
        # -----------------------------------------------------

        student_search = request.GET.get(
            "student_search",
            ""
        ).strip()

        # -----------------------------------------------------
        # AVAILABLE STUDENTS
        #
        # Only account-created students who are not
        # assigned to any class section.
        # -----------------------------------------------------

        available_students = (
            StudentAdmissionApplication.objects
            .filter(
                status="account_created",
                class_section__isnull=True,
            )
            .order_by(
                "first_name",
                "last_name",
            )
        )

        # -----------------------------------------------------
        # SEARCH AVAILABLE STUDENTS
        # -----------------------------------------------------

        if student_search:

            available_students = (
                available_students.filter(
                    Q(
                        first_name__icontains=student_search
                    )
                    | Q(
                        last_name__icontains=student_search
                    )
                    | Q(
                        application_id__icontains=student_search
                    )
                    | Q(
                        credential__username__icontains=student_search
                    )
                )
            )

        # -----------------------------------------------------
        # ALREADY ASSIGNED STUDENTS
        # -----------------------------------------------------

        assigned_students = (
            StudentAdmissionApplication.objects
            .filter(
                status="account_created",
                class_section=selected_class_section,
            )
            .order_by(
                "first_name",
                "last_name",
            )
        )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "classes": classes,

        "total_classes": total_classes,

        "total_sections": total_sections,

        "class_teachers": class_teachers,

        "total_students": total_students,

        "academic_years": academic_years,

        "search": search,

        "student_search": student_search,

        "academic_year": academic_year,

        "status": status,

        "selected_class_section": selected_class_section,

        "available_students": available_students,

        "assigned_students": assigned_students,

        "breadcrumb": (
            "Vice Principal / "
            "Academics / "
            "Class & Sections"
        ),
    }

    return render(
        request,
        "academics/class_sections.html",
        context
    )

@login_required
def add_class_section(request):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to add Class & Section."
        )

    if request.method == "POST":

        form = ClassSectionForm(request.POST)

        if form.is_valid():

            class_section = form.save()

            messages.success(
                request,
                (
                    f"{class_section.grade} - "
                    f"{class_section.section} "
                    "created successfully."
                )
            )

            return redirect(
                "academics:class_sections"
            )

    else:
        form = ClassSectionForm()

    context = {
        "form": form,
        "is_edit": False,
        "breadcrumb": (
            "Vice Principal / "
            "Academics / "
            "Class & Sections / "
            "Add"
        ),
    }

    return render(
        request,
        "academics/class_section_form.html",
        context
    )


@login_required
def edit_class_section(request, class_section_id):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to edit Class & Section."
        )

    class_section = get_object_or_404(
        ClassSection,
        id=class_section_id
    )

    if request.method == "POST":

        form = ClassSectionForm(
            request.POST,
            instance=class_section
        )

        if form.is_valid():

            class_section = form.save()

            messages.success(
                request,
                (
                    f"{class_section.grade} - "
                    f"{class_section.section} "
                    "updated successfully."
                )
            )

            return redirect(
                "academics:class_sections"
            )

    else:

        form = ClassSectionForm(
            instance=class_section
        )

    context = {
        "form": form,
        "class_section": class_section,
        "is_edit": True,
        "breadcrumb": (
            "Vice Principal / "
            "Academics / "
            "Class & Sections / "
            "Edit"
        ),
    }

    return render(
        request,
        "academics/class_section_form.html",
        context
    )


@login_required
def delete_class_section(request, class_section_id):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to delete Class & Section."
        )

    class_section = get_object_or_404(
        ClassSection,
        id=class_section_id
    )

    if request.method == "POST":

        class_name = (
            f"{class_section.grade} - "
            f"{class_section.section}"
        )

        class_section.delete()

        messages.success(
            request,
            f"{class_name} deleted successfully."
        )

        return redirect(
            "academics:class_sections"
        )

    return HttpResponseForbidden(
        "Invalid request."
    )


@login_required
def subjects(request):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to access Subjects."
        )

    # =====================================================
    # 1. SUBJECT LIST FILTERS
    # =====================================================

    subjects_list = Subject.objects.all().order_by("subject_name")

    search = request.GET.get("q", "").strip()
    subject_type = request.GET.get("subject_type", "").strip()
    status = request.GET.get("status", "").strip()

    if search:
        subjects_list = subjects_list.filter(
            Q(subject_name__icontains=search)
            | Q(subject_code__icontains=search)
            | Q(department__icontains=search)
            | Q(description__icontains=search)
        )

    if subject_type:
        subjects_list = subjects_list.filter(
            subject_type=subject_type
        )

    if status == "active":
        subjects_list = subjects_list.filter(is_active=True)
    elif status == "inactive":
        subjects_list = subjects_list.filter(is_active=False)

    # =====================================================
    # 2. EMPLOYEE ASSIGNMENT FILTER VALUES
    # =====================================================

    assignment_q = request.GET.get("assigned_q", "").strip()
    assignment_subject = request.GET.get(
        "assigned_subject", ""
    ).strip()
    assignment_class = request.GET.get(
        "assigned_class", ""
    ).strip()
    assignment_grade = request.GET.get(
        "assigned_grade", ""
    ).strip()
    assignment_employee = request.GET.get(
        "assigned_employee", ""
    ).strip()
    assignment_year = request.GET.get(
        "assigned_year", ""
    ).strip()
    assignment_status = request.GET.get(
        "assigned_status", ""
    ).strip()

    # =====================================================
    # 3. BASE ASSIGNMENT QUERYSET
    # =====================================================

    assignments = (
        SubjectEmployeeAssignment.objects
        .select_related(
            "subject",
            "employee",
            "class_section",
        )
        .all()
    )

    # =====================================================
    # 4. SEARCH EMPLOYEE / USERNAME / SUBJECT / CLASS
    # =====================================================

    if assignment_q:
        assignments = assignments.filter(
            Q(employee__first_name__icontains=assignment_q)
            | Q(employee__last_name__icontains=assignment_q)
            | Q(employee__username__icontains=assignment_q)
            | Q(employee__email__icontains=assignment_q)
            | Q(subject__subject_name__icontains=assignment_q)
            | Q(subject__subject_code__icontains=assignment_q)
            | Q(
                class_section__grade__icontains=assignment_q
            )
            | Q(
                class_section__section__icontains=assignment_q
            )
            | Q(
                academic_year__icontains=assignment_q
            )
        )

    # =====================================================
    # 5. FILTER BY SUBJECT
    # =====================================================

    if assignment_subject.isdigit():
        assignments = assignments.filter(
            subject_id=int(assignment_subject)
        )

    # =====================================================
    # 6. FILTER BY GRADE
    # Grade 1 selects all sections within Grade 1.
    # =====================================================

    if assignment_grade:
        assignments = assignments.filter(
            class_section__grade=assignment_grade
        )

    # =====================================================
    # 7. FILTER BY SPECIFIC CLASS & SECTION
    # =====================================================

    if assignment_class.isdigit():
        assignments = assignments.filter(
            class_section_id=int(assignment_class)
        )

    # =====================================================
    # 8. FILTER BY EMPLOYEE
    # =====================================================

    if assignment_employee.isdigit():
        assignments = assignments.filter(
            employee_id=int(assignment_employee)
        )

    # =====================================================
    # 9. FILTER BY ACADEMIC YEAR
    # =====================================================

    if assignment_year:
        assignments = assignments.filter(
            academic_year__icontains=assignment_year
        )

    # =====================================================
    # 10. FILTER BY ASSIGNMENT STATUS
    # =====================================================

    if assignment_status == "active":
        assignments = assignments.filter(is_active=True)

    elif assignment_status == "inactive":
        assignments = assignments.filter(is_active=False)

    # =====================================================
    # 11. ORDER ASSIGNMENTS
    # =====================================================

    assignments = assignments.order_by(
        "subject__subject_name",
        "class_section__grade",
        "class_section__section",
        "employee__first_name",
        "employee__last_name",
    )

    # =====================================================
    # 12. FILTER DROPDOWN DATA
    # =====================================================

    assignment_subjects = Subject.objects.order_by(
        "subject_name"
    )

    assignment_class_sections = ClassSection.objects.order_by(
        "grade",
        "section",
    )

    # Distinct grade values, so Grade 1 is shown once.
    assignment_grades = (
        ClassSection.objects
        .values_list("grade", flat=True)
        .distinct()
        .order_by("grade")
    )

    assignment_employees = (
        User.objects
        .filter(
            is_active=True,
            profile__role="teacher",
            profile__is_active=True,
        )
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    # =====================================================
    # 13. SUMMARY CARDS
    # =====================================================

    total_subjects = Subject.objects.count()

    core_subjects = Subject.objects.filter(
        subject_type="Core"
    ).count()

    elective_subjects = Subject.objects.filter(
        subject_type="Elective"
    ).count()

    active_departments = (
        Subject.objects
        .filter(
            is_active=True,
            department__isnull=False,
        )
        .exclude(department="")
        .values("department")
        .distinct()
        .count()
    )

    # =====================================================
    # 14. TEMPLATE CONTEXT
    # =====================================================

    context = {
        # Subject list
        "subjects": subjects_list,
        "total_subjects": total_subjects,
        "core_subjects": core_subjects,
        "elective_subjects": elective_subjects,
        "active_departments": active_departments,

        # Existing subject filters
        "search": search,
        "subject_type": subject_type,
        "status": status,

        # Filtered assignment list
        "assignments": assignments,

        # Assignment filter dropdowns
        "assignment_subjects": assignment_subjects,
        "assignment_class_sections": assignment_class_sections,
        "assignment_grades": assignment_grades,
        "assignment_employees": assignment_employees,

        # Selected assignment filter values
        "assignment_q": assignment_q,
        "assignment_subject": assignment_subject,
        "assignment_class": assignment_class,
        "assignment_grade": assignment_grade,
        "assignment_employee": assignment_employee,
        "assignment_year": assignment_year,
        "assignment_status": assignment_status,

        "breadcrumb": "Vice Principal / Academics / Subjects",
    }

    return render(
        request,
        "academics/subjects.html",
        context,
    )

@login_required
def add_subject(request):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to add Subject."
        )

    if request.method == "POST":

        form = SubjectForm(request.POST)

        if form.is_valid():

            subject = form.save()

            messages.success(
                request,
                f"{subject.subject_name} created successfully."
            )

            return redirect(
                "academics:subjects"
            )

    else:
        form = SubjectForm()

    context = {
        "form": form,
        "is_edit": False,
        "breadcrumb": "Vice Principal / Academics / Subjects / Add",
    }

    return render(
        request,
        "academics/subject_form.html",
        context
    )


# =========================================================
# EDIT SUBJECT
# =========================================================

@login_required
def edit_subject(request, subject_id):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to edit Subject."
        )

    subject = get_object_or_404(
        Subject,
        id=subject_id
    )

    if request.method == "POST":

        form = SubjectForm(
            request.POST,
            instance=subject
        )

        if form.is_valid():

            subject = form.save()

            messages.success(
                request,
                f"{subject.subject_name} updated successfully."
            )

            return redirect(
                "academics:subjects"
            )

    else:
        form = SubjectForm(
            instance=subject
        )

    context = {
        "form": form,
        "subject": subject,
        "is_edit": True,
        "breadcrumb": "Vice Principal / Academics / Subjects / Edit",
    }

    return render(
        request,
        "academics/subject_form.html",
        context
    )


# =========================================================
# TOGGLE SUBJECT STATUS
# =========================================================

@login_required
def toggle_subject(request, subject_id):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to change Subject status."
        )

    subject = get_object_or_404(
        Subject,
        id=subject_id
    )

    if request.method == "POST":

        subject.is_active = not subject.is_active

        subject.save(
            update_fields=[
                "is_active",
                "updated_at"
            ]
        )

        if subject.is_active:
            messages.success(
                request,
                f"{subject.subject_name} activated successfully."
            )
        else:
            messages.success(
                request,
                f"{subject.subject_name} deactivated successfully."
            )

        return redirect(
            "academics:subjects"
        )

    return HttpResponseForbidden(
        "Invalid request."
    )


# =========================================================
# DELETE SUBJECT
# =========================================================

@login_required
def delete_subject(request, subject_id):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to delete Subject."
        )

    subject = get_object_or_404(
        Subject,
        id=subject_id
    )

    if request.method == "POST":

        subject_name = subject.subject_name

        subject.delete()

        messages.success(
            request,
            f"{subject_name} deleted successfully."
        )

        return redirect(
            "academics:subjects"
        )

    return HttpResponseForbidden(
        "Invalid request."
    )

@login_required
def assign_subject_employee(request):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to assign employees to subjects."
        )

    if request.method == "POST":

        form = SubjectEmployeeAssignmentForm(request.POST)

        if form.is_valid():

            assignment = form.save(commit=False)

            subject = assignment.subject
            employee = assignment.employee
            class_section = assignment.class_section
            academic_year = assignment.academic_year

            duplicate = SubjectEmployeeAssignment.objects.filter(
                subject=subject,
                employee=employee,
                class_section=class_section,
                academic_year=academic_year,
            ).exists()

            if duplicate:
                form.add_error(
                    None,
                    "This employee is already assigned to this subject and class for the selected academic year."
                )

            else:
                assignment.save()

                employee_name = (
                    employee.get_full_name()
                    or employee.username
                )

                messages.success(
                    request,
                    (
                        f"{employee_name} assigned to "
                        f"{subject.subject_name} successfully."
                    )
                )

                return redirect("academics:subjects")

    else:
        form = SubjectEmployeeAssignmentForm()

    context = {
        "form": form,
        "breadcrumb": (
            "Vice Principal / Academics / "
            "Subjects / Assign Employee"
        ),
    }

    return render(
        request,
        "academics/subject_employee_form.html",
        context
    )

@login_required
def edit_subject_assignment(request, assignment_id):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to edit subject assignments."
        )

    assignment = get_object_or_404(
        SubjectEmployeeAssignment,
        id=assignment_id
    )

    if request.method == "POST":

        form = SubjectEmployeeAssignmentForm(
            request.POST,
            instance=assignment
        )

        if form.is_valid():

            subject = form.cleaned_data["subject"]
            employee = form.cleaned_data["employee"]
            class_section = form.cleaned_data["class_section"]
            academic_year = form.cleaned_data["academic_year"]

            duplicate = (
                SubjectEmployeeAssignment.objects
                .filter(
                    subject=subject,
                    employee=employee,
                    class_section=class_section,
                    academic_year=academic_year,
                )
                .exclude(
                    id=assignment.id
                )
                .exists()
            )

            if duplicate:

                form.add_error(
                    None,
                    "This employee is already assigned to this subject and class for the selected academic year."
                )

            else:

                form.save()

                messages.success(
                    request,
                    "Subject employee assignment updated successfully."
                )

                return redirect(
                    "academics:subjects"
                )

    else:

        form = SubjectEmployeeAssignmentForm(
            instance=assignment
        )

    context = {
        "form": form,
        "assignment": assignment,
        "breadcrumb": (
            "Vice Principal / Academics / "
            "Subjects / Edit Assignment"
        ),
    }

    return render(
        request,
        "academics/subject_employee_form.html",
        context
    )


@login_required
def delete_subject_assignment(request, assignment_id):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to delete subject assignments."
        )

    assignment = get_object_or_404(
        SubjectEmployeeAssignment,
        id=assignment_id
    )

    if request.method == "POST":

        assignment.delete()

        messages.success(
            request,
            "Subject employee assignment deleted successfully."
        )

        return redirect(
            "academics:subjects"
        )

    return render(
        request,
        "academics/subject_employee_assignment_delete.html",
        {
            "assignment": assignment,
            "breadcrumb": (
                "Vice Principal / Academics / "
                "Subjects / Delete Assignment"
            ),
        }
    )

@login_required
def timetable(request):
    """
    Display the weekly timetable using the actual
    ClassSection, SchoolTimetableConfig, PeriodDefinition
    and TimetableEntry models.
    """

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to access Timetable."
        )

    # --------------------------------------------------
    # 1. CLASS SECTIONS
    # Include Full classes for viewing their timetables.
    # --------------------------------------------------

    classes = ClassSection.objects.exclude(
        status="Inactive"
    ).select_related(
        "class_teacher"
    ).order_by(
        "grade",
        "section",
    )

    # --------------------------------------------------
    # 2. SELECT CLASS
    # HTML sends class_section, so read that parameter.
    # --------------------------------------------------

    selected_class_id = request.GET.get(
        "class_section",
        "",
    ).strip()

    selected_class_obj = None

    if selected_class_id.isdigit():
        selected_class_obj = classes.filter(
            pk=int(selected_class_id)
        ).first()

    # --------------------------------------------------
    # 3. ACADEMIC YEAR
    # Use selected class academic year by default.
    # --------------------------------------------------

    academic_year = request.GET.get(
        "academic_year",
        "",
    ).strip()

    if not academic_year and selected_class_obj:
        academic_year = selected_class_obj.academic_year

    # --------------------------------------------------
    # 4. SCHOOL TIMETABLE CONFIGURATION
    # --------------------------------------------------

    config = None

    if academic_year:
        config = SchoolTimetableConfig.objects.filter(
            academic_year=academic_year,
            is_active=True,
        ).first()

    # --------------------------------------------------
    # 5. WORKING DAYS
    # --------------------------------------------------

    default_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]

    days = default_days

    if config and config.working_days:
        days = config.working_days

    # --------------------------------------------------
    # 6. CONFIGURED PERIODS
    # Keep period objects so the template can show times.
    # --------------------------------------------------

    period_definitions = PeriodDefinition.objects.none()

    if academic_year:
        period_definitions = PeriodDefinition.objects.filter(
            academic_year=academic_year,
            is_active=True,
        ).order_by(
            "period_number"
        )

    periods = list(period_definitions)

    # --------------------------------------------------
    # 7. TIMETABLE ENTRIES
    # --------------------------------------------------

    entries = TimetableEntry.objects.none()

    if selected_class_obj and academic_year:
        entries = (
            TimetableEntry.objects
            .filter(
                class_section=selected_class_obj,
                academic_year=academic_year,
                is_active=True,
                day__in=days,
            )
            .select_related(
                "class_section",
                "subject",
                "employee",
                "timetable_plan",
            )
            .order_by(
                "day",
                "period",
            )
        )

    # --------------------------------------------------
    # 8. BUILD GRID
    # grid[day][period_number] = timetable entry
    # --------------------------------------------------

    timetable_grid = {
        day: {} for day in days
    }

    for entry in entries:
        if entry.period not in {
            period.period_number for period in periods
        }:
            continue

        timetable_grid.setdefault(
            entry.day,
            {},
        )[entry.period] = entry

    # --------------------------------------------------
    # 9. CONTEXT
    # selected_class remains the ID for HTML comparison.
    # --------------------------------------------------

    context = {
        "classes": classes,
        "selected_class": (
            selected_class_obj.pk
            if selected_class_obj
            else ""
        ),
        "selected_class_obj": selected_class_obj,
        "selected_academic_year": academic_year,
        "academic_year": academic_year,
        "config": config,
        "days": days,
        "periods": periods,
        "entries": entries,
        "timetable_grid": timetable_grid,
        "breadcrumb": (
            "Vice Principal / Academics / Timetable"
        ),
    }

    return render(
        request,
        "academics/timetable.html",
        context,
    )

@login_required
def timetable_config(request):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to configure the timetable."
        )

    working_days_options = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]

    academic_year = request.GET.get("academic_year", "").strip()

    config = None
    period_definitions = []

    if academic_year:
        config = SchoolTimetableConfig.objects.filter(
            academic_year=academic_year
        ).first()

        period_definitions = list(
            PeriodDefinition.objects.filter(
                academic_year=academic_year
            ).order_by("period_number")
        )

    if request.method == "POST":
        academic_year = request.POST.get(
            "academic_year", ""
        ).strip()

        working_days = request.POST.getlist("working_days")

        school_start_time = request.POST.get("school_start_time")
        school_end_time = request.POST.get("school_end_time")

        try:
            periods_per_day = int(
                request.POST.get("periods_per_day", 0)
            )
        except (TypeError, ValueError):
            periods_per_day = 0

        if not academic_year:
            messages.error(request, "Please enter the academic year.")

        elif not working_days:
            messages.error(request, "Please select working days.")

        elif periods_per_day < 1 or periods_per_day > 12:
            messages.error(
                request,
                "Periods per day must be between 1 and 12."
            )

        elif not school_start_time or not school_end_time:
            messages.error(
                request,
                "Please enter school start time and end time."
            )

        elif school_start_time >= school_end_time:
            messages.error(
                request,
                "School end time must be later than start time."
            )

        else:
            config, _ = SchoolTimetableConfig.objects.update_or_create(
                academic_year=academic_year,
                defaults={
                    "working_days": working_days,
                    "school_start_time": school_start_time,
                    "school_end_time": school_end_time,
                    "periods_per_day": periods_per_day,
                    "is_active": True,
                },
            )

            valid_period_types = {
                "Teaching",
                "Break",
                "Lunch",
                "Assembly",
                "Activity",
            }

            periods_valid = True

            for number in range(1, periods_per_day + 1):
                period_name = request.POST.get(
                    f"period_name_{number}", ""
                ).strip()

                period_start = request.POST.get(
                    f"period_start_{number}", ""
                )

                period_end = request.POST.get(
                    f"period_end_{number}", ""
                )

                period_type = request.POST.get(
                    f"period_type_{number}", "Teaching"
                )

                if (
                    not period_name
                    or not period_start
                    or not period_end
                    or period_start >= period_end
                    or period_type not in valid_period_types
                ):
                    periods_valid = False
                    break

            if not periods_valid:
                messages.error(
                    request,
                    "Please check every period's name, time and type. "
                    "The end time must be later than the start time."
                )

            else:
                for number in range(1, periods_per_day + 1):
                    PeriodDefinition.objects.update_or_create(
                        academic_year=academic_year,
                        period_number=number,
                        defaults={
                            "period_name": request.POST.get(
                                f"period_name_{number}"
                            ).strip(),
                            "start_time": request.POST.get(
                                f"period_start_{number}"
                            ),
                            "end_time": request.POST.get(
                                f"period_end_{number}"
                            ),
                            "period_type": request.POST.get(
                                f"period_type_{number}"
                            ),
                            "is_active": True,
                        },
                    )

                # Deactivate any old periods beyond the configured count.
                PeriodDefinition.objects.filter(
                    academic_year=academic_year,
                    period_number__gt=periods_per_day,
                ).update(is_active=False)

                messages.success(
                    request,
                    "Timetable configuration saved successfully."
                )

                return redirect(
                    "academics:subject_period_requirements"
                )

        # Reload current data when validation fails.
        config = SchoolTimetableConfig.objects.filter(
            academic_year=academic_year
        ).first()

        period_definitions = list(
            PeriodDefinition.objects.filter(
                academic_year=academic_year
            ).order_by("period_number")
        )

    context = {
        "config": config,
        "period_definitions": period_definitions,
        "working_days_options": working_days_options,
        "academic_year": academic_year,
        "breadcrumb": [
            {"title": "Academics", "url": None},
            {"title": "Timetable", "url": "academics:timetable"},
            {"title": "Configure Timetable", "url": None},
        ],
    }

    return render(
        request,
        "academics/timetable_config.html",
        context,
    )

@login_required
def timetable_generate(request):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to generate Timetable."
        )

    from django.db import transaction
    from django.contrib import messages

    classes = (
        ClassSection.objects.exclude(status="Inactive")
        .order_by("grade", "section")
    )

    selected_class_id = (
        request.POST.get("class_section")
        or request.GET.get("class_section", "")
    ).strip()

    selected_academic_year = (
        request.POST.get("academic_year")
        or request.GET.get("academic_year", "")
    ).strip()

    selected_class = None

    if selected_class_id.isdigit():
        selected_class = classes.filter(
            pk=int(selected_class_id)
        ).first()

    if selected_class and not selected_academic_year:
        selected_academic_year = selected_class.academic_year

    config = None
    days = []
    periods = []
    entries = TimetableEntry.objects.none()
    subjects = Subject.objects.filter(is_active=True).order_by(
        "subject_name"
    )
    teachers = User.objects.none()
    current_plan = None

    if selected_academic_year:
        config = SchoolTimetableConfig.objects.filter(
            academic_year=selected_academic_year,
            is_active=True,
        ).first()

        if config:
            days = config.working_days or []

        periods = list(
            PeriodDefinition.objects.filter(
                academic_year=selected_academic_year,
                is_active=True,
                period_type="Teaching",
            ).order_by("period_number")
        )

    if selected_class and selected_academic_year:
        current_plan = TimetablePlan.objects.filter(
            class_section=selected_class,
            academic_year=selected_academic_year,
            status="Draft",
        ).order_by("-version").first()

        if current_plan:
            entries = (
                TimetableEntry.objects.filter(
                    timetable_plan=current_plan,
                    is_active=True,
                )
                .select_related("subject", "employee")
                .order_by("day", "period")
            )

        assignment_qs = SubjectEmployeeAssignment.objects.filter(
            class_section=selected_class,
            academic_year=selected_academic_year,
            is_active=True,
        ).select_related("employee", "subject")

        teacher_ids = assignment_qs.values_list(
            "employee_id", flat=True
        ).distinct()

        teachers = User.objects.filter(
            pk__in=teacher_ids
        ).order_by("username")

    # Generate a new Draft timetable.
    if request.method == "POST" and request.POST.get("action") == "generate_timetable":

        if not selected_class:
            messages.error(request, "Please select a valid class.")
        elif not selected_academic_year:
            messages.error(request, "Please select an academic year.")
        elif not config or not days or not periods:
            messages.error(
                request,
                "Please configure working days and teaching periods first.",
            )
        else:
            requirements = list(
                SubjectPeriodRequirement.objects.filter(
                    class_section=selected_class,
                    academic_year=selected_academic_year,
                ).select_related("subject").order_by("subject__subject_name")
            )

            if not requirements:
                messages.error(
                    request,
                    "No subject-period requirements found for this class and academic year.",
                )
            else:
                assignments = list(
                    SubjectEmployeeAssignment.objects.filter(
                        class_section=selected_class,
                        academic_year=selected_academic_year,
                        is_active=True,
                    ).select_related("subject", "employee")
                )

                teacher_map = {}
                for assignment in assignments:
                    teacher_map.setdefault(
                        assignment.subject_id, []
                    ).append(assignment.employee)

                # Build available class/day/period slots.
                slots = [
                    (day, period.period_number)
                    for day in days
                    for period in periods
                ]

                scheduled = []
                used_class_slots = set()
                used_teacher_slots = set()
                unscheduled = []

                for requirement in requirements:
                    subject_id = requirement.subject_id
                    needed = requirement.periods_per_week
                    assigned_teachers = teacher_map.get(subject_id, [])

                    if not assigned_teachers:
                        unscheduled.append(
                            f"{requirement.subject.subject_name}: no teacher assigned"
                        )
                        continue

                    subject_scheduled = 0
                    used_subject_days = set()

                    for day, period_number in slots:
                        if subject_scheduled >= needed:
                            break

                        class_slot = (day, period_number)

                        if class_slot in used_class_slots:
                            continue

                        # Prefer not to schedule the same subject twice
                        # on the same day unless necessary.
                        if day in used_subject_days:
                            continue

                        available_teacher = None

                        for teacher in assigned_teachers:
                            teacher_slot = (
                                teacher.pk,
                                day,
                                period_number,
                            )

                            if teacher_slot not in used_teacher_slots:
                                available_teacher = teacher
                                break

                        if not available_teacher:
                            continue

                        scheduled.append({
                            "day": day,
                            "period": period_number,
                            "subject": requirement.subject,
                            "employee": available_teacher,
                        })

                        used_class_slots.add(class_slot)
                        used_teacher_slots.add((
                            available_teacher.pk,
                            day,
                            period_number,
                        ))
                        used_subject_days.add(day)
                        subject_scheduled += 1

                    if subject_scheduled < needed:
                        unscheduled.append(
                            f"{requirement.subject.subject_name}: "
                            f"{subject_scheduled}/{needed} periods scheduled"
                        )

                if not scheduled:
                    messages.error(
                        request,
                        "No timetable slots could be generated. Check teacher assignments and period requirements.",
                    )
                else:
                    try:
                        with transaction.atomic():
                            # Never modify a Published plan.
                            # Replace only the existing Draft plan.
                            if current_plan:
                                TimetableEntry.objects.filter(
                                    timetable_plan=current_plan
                                ).delete()
                                plan = current_plan
                            else:
                                latest_version = (
                                    TimetablePlan.objects.filter(
                                        class_section=selected_class,
                                        academic_year=selected_academic_year,
                                    ).order_by("-version")
                                    .values_list("version", flat=True)
                                    .first()
                                ) or 0

                                plan = TimetablePlan.objects.create(
                                    class_section=selected_class,
                                    academic_year=selected_academic_year,
                                    version=latest_version + 1,
                                    status="Draft",
                                    created_by=request.user,
                                )

                            for item in scheduled:
                                TimetableEntry.objects.create(
                                    class_section=selected_class,
                                    timetable_plan=plan,
                                    subject=item["subject"],
                                    employee=item["employee"],
                                    academic_year=selected_academic_year,
                                    day=item["day"],
                                    period=item["period"],
                                    is_active=True,
                                )

                        if unscheduled:
                            messages.warning(
                                request,
                                "Draft generated with some incomplete requirements: "
                                + "; ".join(unscheduled),
                            )
                        else:
                            messages.success(
                                request,
                                "Draft timetable generated successfully.",
                            )

                        return redirect(
                            f"{request.path}?class_section={selected_class.pk}"
                            f"&academic_year={selected_academic_year}"
                        )

                    except Exception as exc:
                        messages.error(
                            request,
                            f"Could not generate timetable: {exc}",
                        )

    context = {
        "classes": classes,
        "selected_class": selected_class.pk if selected_class else "",
        "selected_class_obj": selected_class,
        "selected_academic_year": selected_academic_year,
        "academic_year": selected_academic_year,
        "config": config,
        "days": days,
        "periods": periods,
        "entries": entries,
        "subjects": subjects,
        "teachers": teachers,
        "current_plan": current_plan,
        "breadcrumb": "Vice Principal / Academics / Generate Timetable",
    }

    return render(
        request,
        "academics/timetable_generate.html",
        context,
    )
    
@login_required
def timetable_validate(request):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to validate the timetable."
        )

    # Use actual ClassSection model fields.
    classes = ClassSection.objects.filter(
        status="Active"
    ).order_by("grade", "section")

    selected_class_id = request.GET.get("class_id", "")
    academic_year = request.GET.get(
        "academic_year", ""
    ).strip()

    selected_class = None
    plan = None
    entries = TimetableEntry.objects.none()
    requirements = SubjectPeriodRequirement.objects.none()
    validation_errors = []

    if selected_class_id:
        selected_class = classes.filter(
            pk=selected_class_id
        ).first()

    if selected_class and academic_year:
        plan = TimetablePlan.objects.filter(
            class_section=selected_class,
            academic_year=academic_year,
        ).order_by("-version").first()

        entries = TimetableEntry.objects.filter(
            class_section=selected_class,
            academic_year=academic_year,
            is_active=True,
        ).select_related(
            "subject",
            "employee",
        ).order_by("day", "period")

        # Check duplicate class periods.
        seen_class_periods = set()

        for entry in entries:
            key = (entry.day, entry.period)

            if key in seen_class_periods:
                validation_errors.append(
                    f"Class conflict: {entry.day}, "
                    f"period {entry.period} has multiple entries."
                )

            seen_class_periods.add(key)

        # Check required weekly periods.
        requirements = SubjectPeriodRequirement.objects.filter(
            class_section=selected_class,
            academic_year=academic_year,
        ).select_related("subject")

        for requirement in requirements:
            assigned_count = entries.filter(
                subject=requirement.subject
            ).count()

            if assigned_count < requirement.periods_per_week:
                validation_errors.append(
                    f"{requirement.subject}: "
                    f"{assigned_count} of "
                    f"{requirement.periods_per_week} "
                    f"required periods assigned."
                )

    if request.method == "POST":
        action = request.POST.get("action", "")

        # Read selections from POST when submitted.
        post_class_id = request.POST.get(
            "class_section", ""
        )
        post_academic_year = request.POST.get(
            "academic_year", ""
        ).strip()

        if post_class_id:
            selected_class_id = post_class_id

        if post_academic_year:
            academic_year = post_academic_year

        if not selected_class or not academic_year:
            messages.error(
                request,
                "Select a class and academic year before validation."
            )

        elif action == "validate":
            if validation_errors:
                messages.error(
                    request,
                    "Validation found issues. Resolve them before approval."
                )
            else:
                messages.success(
                    request,
                    "Basic timetable validation passed. "
                    "Review the timetable before submitting for approval."
                )

        elif action == "submit":
            if validation_errors:
                messages.error(
                    request,
                    "Resolve all validation issues before submitting."
                )
            elif plan is None:
                messages.error(
                    request,
                    "No timetable plan exists for this class and academic year."
                )
            else:
                messages.info(
                    request,
                    "Validation passed. The approval and publishing "
                    "workflow still needs to be connected."
                )

        from urllib.parse import urlencode

        query_string = urlencode({
            "class_id": selected_class.pk if selected_class else "",
            "academic_year": academic_year,
        })

        return redirect(
            f"/academics/timetable/validate/?{query_string}"
        )

    context = {
        "classes": classes,
        "selected_class": selected_class,
        "selected_class_id": selected_class_id,
        "academic_year": academic_year,
        "plan": plan,
        "entries": entries,
        "requirements": requirements,
        "validation_errors": validation_errors,
        "is_valid": (
            not validation_errors
            and bool(selected_class and academic_year)
        ),
        "breadcrumb": [
            {"title": "Academics", "url": None},
            {
                "title": "Timetable",
                "url": "academics:timetable",
            },
            {
                "title": "Validate Timetable",
                "url": None,
            },
        ],
    }

    return render(
        request,
        "academics/timetable_validate.html",
        context,
    )

@login_required
def subject_period_requirements(request):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to manage subject period requirements."
        )

    edit_id = request.GET.get("edit", "").strip()
    edit_requirement = None

    if edit_id:
        if edit_id.isdigit():
            edit_requirement = get_object_or_404(
                SubjectPeriodRequirement,
                pk=int(edit_id),
            )
        else:
            messages.error(request, "Invalid requirement ID.")
            return redirect("academics:subject_period_requirements")

    # -----------------------------------------------------
    # DELETE REQUIREMENT
    # -----------------------------------------------------

    if request.method == "POST":

        action = request.POST.get("action", "save").strip()

        if action == "delete":

            requirement_id = request.POST.get(
                "requirement_id", ""
            ).strip()

            if not requirement_id.isdigit():
                messages.error(request, "Invalid requirement ID.")
                return redirect(
                    "academics:subject_period_requirements"
                )

            requirement = get_object_or_404(
                SubjectPeriodRequirement,
                pk=int(requirement_id),
            )

            requirement.delete()

            messages.success(
                request,
                "Subject period requirement deleted successfully.",
            )

            return redirect(
                "academics:subject_period_requirements"
            )

        # -------------------------------------------------
        # CREATE / UPDATE REQUIREMENT
        # -------------------------------------------------

        requirement_id = request.POST.get(
            "requirement_id", ""
        ).strip()

        if requirement_id:
            if not requirement_id.isdigit():
                messages.error(request, "Invalid requirement ID.")
                return redirect(
                    "academics:subject_period_requirements"
                )

            instance = get_object_or_404(
                SubjectPeriodRequirement,
                pk=int(requirement_id),
            )
        else:
            instance = None

        form = SubjectPeriodRequirementForm(
            request.POST,
            instance=instance,
        )

        if form.is_valid():

            requirement = form.save()

            messages.success(
                request,
                (
                    f"{requirement.subject.subject_name} weekly "
                    f"period requirement saved successfully."
                ),
            )

            return redirect(
                "academics:subject_period_requirements"
            )

    else:

        if edit_requirement:
            form = SubjectPeriodRequirementForm(
                instance=edit_requirement,
            )
        else:
            form = SubjectPeriodRequirementForm()

    # -----------------------------------------------------
    # REQUIREMENTS LIST
    # -----------------------------------------------------

    requirements = (
        SubjectPeriodRequirement.objects
        .select_related(
            "class_section",
            "subject",
        )
        .order_by(
            "academic_year",
            "class_section__grade",
            "class_section__section",
            "subject__subject_name",
        )
    )

    # -----------------------------------------------------
    # FILTERS
    # -----------------------------------------------------

    search = request.GET.get("q", "").strip()
    academic_year = request.GET.get(
        "academic_year", ""
    ).strip()
    class_section_id = request.GET.get(
        "class_section", ""
    ).strip()

    if search:
        requirements = requirements.filter(
            Q(subject__subject_name__icontains=search)
            | Q(subject__subject_code__icontains=search)
            | Q(class_section__grade__icontains=search)
            | Q(class_section__section__icontains=search)
        )

    if academic_year:
        requirements = requirements.filter(
            academic_year=academic_year
        )

    if class_section_id.isdigit():
        requirements = requirements.filter(
            class_section_id=int(class_section_id)
        )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    total_requirements = requirements.count()

    total_weekly_periods = sum(
        item.periods_per_week for item in requirements
    )

    classes = ClassSection.objects.order_by(
        "grade", "section"
    )

    academic_years = (
        SubjectPeriodRequirement.objects
        .values_list("academic_year", flat=True)
        .distinct()
        .order_by("-academic_year")
    )

    context = {
        "form": form,
        "edit_requirement": edit_requirement,
        "requirements": requirements,
        "classes": classes,
        "academic_years": academic_years,
        "search": search,
        "academic_year": academic_year,
        "selected_class_section": class_section_id,
        "total_requirements": total_requirements,
        "total_weekly_periods": total_weekly_periods,
        "breadcrumb": (
            "Vice Principal / Academics / "
            "Subject Period Requirements"
        ),
    }

    return render(
        request,
        "academics/subject_period_requirements.html",
        context,
    )

@login_required
def timetable_employee_options(request):
    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You do not have permission to view timetable teacher options."
        )

    if request.method != "GET":
        return JsonResponse({"employees": []}, status=405)

    class_section_id = request.GET.get("class_section_id", "").strip()
    subject_id = request.GET.get("subject_id", "").strip()
    academic_year = request.GET.get("academic_year", "").strip()
    if not (
        class_section_id.isdigit()
        and subject_id.isdigit()
        and academic_year
    ):
        return JsonResponse({"employees": []})

    assignments = SubjectEmployeeAssignment.objects.filter(
        class_section_id=int(class_section_id),
        subject_id=int(subject_id),
        academic_year=academic_year,
        is_active=True,
        employee__is_active=True,
        employee__profile__is_active=True,
        employee__profile__role="teacher",
    )
    teachers = User.objects.filter(
        pk__in=assignments.values_list("employee_id", flat=True),
        is_active=True,
        profile__is_active=True,
        profile__role="teacher",
    ).select_related("profile").order_by(
        "first_name",
        "last_name",
        "username",
    )

    return JsonResponse({
        "employees": [
            {
                "id": teacher.pk,
                "name": teacher.get_full_name() or teacher.username,
            }
            for teacher in teachers
        ]
    })

@login_required
def teacher_timetable(request):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "User profile not found."
        )

    if request.user.profile.role != "teacher":
        return HttpResponseForbidden(
            "Only teachers can access their timetable."
        )

    # -----------------------------------------------------
    # SUBJECT / CLASS ASSIGNMENTS
    # -----------------------------------------------------

    assignments = (
        SubjectEmployeeAssignment.objects
        .select_related(
            "subject",
            "class_section",
        )
        .filter(
            employee=request.user,
            is_active=True,
        )
        .order_by(
            "class_section__grade",
            "class_section__section",
            "subject__subject_name",
        )
    )

    # -----------------------------------------------------
    # TEACHER TIMETABLE
    # -----------------------------------------------------

    entries = (
        TimetableEntry.objects
        .select_related(
            "class_section",
            "subject",
            "employee",
        )
        .filter(
            employee=request.user,
            is_active=True,
        )
        .order_by(
            "day",
            "period",
            "class_section__grade",
            "class_section__section",
        )
    )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]

    periods = list(range(1, 8))

    # -----------------------------------------------------
    # CREATE TEACHER TIMETABLE GRID
    # -----------------------------------------------------

    timetable_grid = {}

    for entry in entries:

        if entry.day not in timetable_grid:
            timetable_grid[entry.day] = {}

        timetable_grid[entry.day][entry.period] = entry

    # -----------------------------------------------------
    # CLASSES ASSIGNED TO TEACHER
    # -----------------------------------------------------

    assigned_classes = ClassSection.objects.filter(
        Q(class_teacher=request.user)
        | Q(timetable_entries__employee=request.user)
        | Q(subject_assignments__employee=request.user)
    ).distinct().order_by(
        "grade",
        "section",
    )

    context = {
        "assignments": assignments,

        "entries": entries,

        "assigned_classes": assigned_classes,

        "days": days,

        "periods": periods,

        "timetable_grid": timetable_grid,

        "teacher": request.user,

        "breadcrumb": "Teacher / My Timetable",
    }

    return render(
        request,
        "academics/teacher_timetable.html",
        context
    )

@login_required
def teacher_students(request):

    teacher = request.user

    # ---------------------------------------------------------
    # TEACHER ASSIGNED CLASS SECTIONS
    # ---------------------------------------------------------

    assigned_classes = (
        ClassSection.objects
        .filter(
            class_teacher=teacher
        )
        .order_by(
            "grade",
            "section"
        )
    )
    for class_section in assigned_classes:
        class_section.students_count = (
        StudentAdmissionApplication.objects
        .filter(
            class_section=class_section,
            status="account_created",
        )
        .count()
    )
    

    # ---------------------------------------------------------
    # SELECTED CLASS
    # ---------------------------------------------------------

    selected_class_id = request.GET.get(
        "class_id",
        ""
    ).strip()

    selected_class = None

    students = StudentAdmissionApplication.objects.none()

    if selected_class_id:

        try:

            selected_class = (
                ClassSection.objects
                .get(
                    id=int(selected_class_id),
                    class_teacher=teacher
                )
            )

        except (
            ValueError,
            ClassSection.DoesNotExist,
        ):

            selected_class = None

    # ---------------------------------------------------------
    # STUDENTS
    # ---------------------------------------------------------

    if selected_class:

        students = (
            StudentAdmissionApplication.objects
            .filter(
                class_section=selected_class,
                status="account_created",
            )
            .order_by(
                "first_name",
                "last_name"
            )
        )

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    student_search = request.GET.get(
        "student_search",
        ""
    ).strip()

    if student_search and selected_class:

        students = students.filter(
            Q(first_name__icontains=student_search)
            | Q(last_name__icontains=student_search)
            | Q(application_id__icontains=student_search)
            | Q(phone__icontains=student_search)
        )

    # ---------------------------------------------------------
    # TOTALS
    # ---------------------------------------------------------

    total_classes = assigned_classes.count()

    total_students = (
        StudentAdmissionApplication.objects
        .filter(
            class_section__class_teacher=teacher,
            status="account_created",
        )
        .count()
    )

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {

        "assigned_classes": assigned_classes,

        "selected_class": selected_class,

        "students": students,

        "student_search": student_search,

        "total_classes": total_classes,

        "total_students": total_students,

        "breadcrumb": (
            "Teacher / "
            "Students"
        ),
    }

    return render(
        request,
        "academics/teacher_students.html",
        context
    )

@login_required
def message_parent(request, student_id):
    teacher = request.user

    student = get_object_or_404(
        StudentAdmissionApplication.objects.select_related("class_section"),
        id=student_id,
        status="account_created",
        class_section__class_teacher=teacher,
    )

    parent_links = (
        ParentStudent.objects
        .filter(
            student=student,
            is_active=True
        )
        .select_related("parent")
    )

    # Existing message history
    message_history = (
        ParentMessage.objects
        .filter(
            teacher=teacher,
            student=student
        )
        .select_related("parent")
        .order_by("-created_at")
    )

    if request.method == "POST":

        parent_id = request.POST.get("parent_id", "").strip()
        subject = request.POST.get("subject", "").strip()
        message_text = request.POST.get("message", "").strip()

        if not parent_id:
            messages.error(request, "Please select a parent.")
            return redirect(
                "academics:message_parent",
                student_id=student.id
            )

        if not message_text:
            messages.error(request, "Please enter a message.")
            return redirect(
                "academics:message_parent",
                student_id=student.id
            )

        parent_link = get_object_or_404(
            ParentStudent,
            id=parent_id,
            student=student,
            is_active=True
        )

        # Save message
        ParentMessage.objects.create(
            teacher=teacher,
            parent=parent_link.parent,
            student=student,
            subject=subject if subject else "Message from Teacher",
            message=message_text,
        )

        messages.success(
            request,
            "Message sent successfully to the parent."
        )

        return redirect(
            "academics:message_parent",
            student_id=student.id
        )

    context = {
        "student": student,
        "parent_links": parent_links,
        "message_history": message_history,
        "breadcrumb": "Teacher / Students / Message Parent",
    }

    return render(
        request,
        "academics/message_parent.html",
        context
    )

@login_required
def student_subjects_home(request):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "Student profile not found."
        )

    if request.user.profile.role != "student":
        return HttpResponseForbidden(
            "Only students can access this page."
        )

    return render(
        request,
        "academics/student_subjects_home.html",
        {
            "user": request.user,
            "role": request.user.profile.role,
            "role_display": request.user.profile.get_role_display(),
            "breadcrumb": "Student / Subjects",
        },
    )

@login_required
def student_subject_list(request):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden("User profile not found.")

    role = str(request.user.profile.role).lower()

    if role not in ["student", "parent"]:
        return HttpResponseForbidden(
            "Only students and parents can access subjects."
        )

    student = get_academic_student(request)

    if not student:
        return render(
            request,
            "academics/student_subject_list.html",
            {
                "student": None,
                "class_section": None,
                "subject_assignments": [],
                "parent_children": [],
                "is_parent_view": role == "parent",
                "error_message": (
                    "No linked student record was found."
                ),
                "breadcrumb": "Academics / Subjects",
            },
        )

    # Parent authorization: verify selected child is linked
    if role == "parent":
        is_linked = ParentStudent.objects.filter(
            parent=request.user,
            student=student,
            is_active=True,
        ).exists()

        if not is_linked:
            return HttpResponseForbidden(
                "You cannot access this student's subjects."
            )

    class_section = student.class_section
    subject_assignments = []

    if class_section:
        subject_assignments = (
            SubjectEmployeeAssignment.objects
            .filter(
                class_section=class_section,
                academic_year=class_section.academic_year,
                is_active=True,
                subject__is_active=True,
            )
            .select_related(
                "subject",
                "employee",
                "class_section",
            )
            .order_by("subject__subject_name")
        )

    parent_children = []

    if role == "parent":
        parent_children = list(
            StudentAdmissionApplication.objects
            .filter(
                id__in=ParentStudent.objects.filter(
                    parent=request.user,
                    is_active=True,
                ).values_list("student_id", flat=True),
                status="account_created",
            )
            .order_by("first_name", "last_name")
        )

    return render(
        request,
        "academics/student_subject_list.html",
        {
            "student": student,
            "class_section": class_section,
            "subject_assignments": subject_assignments,
            "parent_children": parent_children,
            "selected_student_id": student.id,
            "is_parent_view": role == "parent",
            "breadcrumb": (
                "Parent / Child Subjects"
                if role == "parent"
                else "Student / My Subjects"
            ),
        },
    )

@login_required
def student_message_teacher(
    request,
    assignment_id,
):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "Student profile not found."
        )

    if request.user.profile.role != "student":
        return HttpResponseForbidden(
            "Only students can message teachers."
        )

    assignment = get_object_or_404(
        SubjectEmployeeAssignment.objects
        .select_related(
            "subject",
            "employee",
            "class_section",
        ),
        id=assignment_id,
        is_active=True,
    )

    credential = (
        StudentAdmissionApplication.objects
        .filter(
            credential__user=request.user,
            credential__is_active=True,
            status="account_created",
        )
        .select_related("class_section")
        .first()
    )

    if not credential:
        return HttpResponseForbidden(
            "Student account is not linked correctly."
        )

    if credential.class_section_id != assignment.class_section_id:
        return HttpResponseForbidden(
            "This subject is not assigned to your class."
        )

    teacher = assignment.employee
    subject = assignment.subject

    message_history = (
        StudentTeacherMessage.objects
        .filter(
            student=request.user,
            teacher=teacher,
            subject=subject,
        )
        .select_related(
            "teacher",
            "subject",
        )
        .order_by("-created_at")
    )

    if request.method == "POST":

        message_subject = request.POST.get(
            "message_subject",
            ""
        ).strip()

        message_text = request.POST.get(
            "message",
            ""
        ).strip()

        if not message_text:

            messages.error(
                request,
                "Please enter a message."
            )

            return redirect(
                "academics:student_message_teacher",
                assignment_id=assignment.id,
            )

        StudentTeacherMessage.objects.create(
            student=request.user,
            teacher=teacher,
            subject=subject,
            message_subject=(
                message_subject
                if message_subject
                else "Message from Student"
            ),
            message=message_text,
        )

        messages.success(
            request,
            "Message sent successfully to the teacher."
        )

        return redirect(
            "academics:student_message_teacher",
            assignment_id=assignment.id,
        )

    return render(
        request,
        "academics/student_message_teacher.html",
        {
            "student": credential,
            "assignment": assignment,
            "teacher": teacher,
            "subject": subject,
            "message_history": message_history,
            "breadcrumb": (
                "Student / Subjects / Message Teacher"
            ),
        },
    )

@login_required
def student_assignments(request):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "Student profile not found."
        )

    if request.user.profile.role != "student":
        return HttpResponseForbidden(
            "Only students can access assignments."
        )

    credential = (
        StudentAdmissionApplication.objects
        .filter(
            credential__user=request.user,
            credential__is_active=True,
            status="account_created",
        )
        .select_related("class_section")
        .first()
    )

    if not credential:
        return render(
            request,
            "academics/student_assignments.html",
            {
                "student": None,
                "class_section": None,
                "assignments": [],
                "breadcrumb": "Student / Assignments",
            },
        )

    student = credential
    class_section = student.class_section

    assignments = []

    if class_section:

        assignments = (
            Assignment.objects
            .filter(
                class_section=class_section,
                academic_year=class_section.academic_year,
            )
            .select_related(
                "subject",
                "teacher",
                "class_section",
            )
            .prefetch_related(
                "submissions"
            )
        )

        for assignment in assignments:

            assignment.student_submission = (
                assignment.submissions
                .filter(
                    student=request.user
                )
                .first()
            )

    return render(
        request,
        "academics/student_assignments.html",
        {
            "student": student,
            "class_section": class_section,
            "assignments": assignments,
            "breadcrumb": "Student / Assignments",
        },
    )


# =========================================================
# STUDENT - UPLOAD ASSIGNMENT SUBMISSION
# =========================================================

@login_required
def student_submit_assignment(
    request,
    assignment_id,
):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "Student profile not found."
        )

    if request.user.profile.role != "student":
        return HttpResponseForbidden(
            "Only students can submit assignments."
        )

    credential = (
        StudentAdmissionApplication.objects
        .filter(
            credential__user=request.user,
            credential__is_active=True,
            status="account_created",
        )
        .select_related("class_section")
        .first()
    )

    if not credential:
        return HttpResponseForbidden(
            "Student account is not linked correctly."
        )

    assignment = get_object_or_404(
        Assignment.objects
        .select_related(
            "subject",
            "teacher",
            "class_section",
        ),
        id=assignment_id,
    )

    if assignment.class_section_id != credential.class_section_id:
        return HttpResponseForbidden(
            "This assignment is not assigned to your class."
        )

    if request.method == "POST":

        submission_file = request.FILES.get(
            "submission_file"
        )

        comment = request.POST.get(
            "comment",
            ""
        ).strip()

        if not submission_file:

            messages.error(
                request,
                "Please select a file to upload."
            )

            return redirect(
                "academics:student_submit_assignment",
                assignment_id=assignment.id,
            )

        existing_submission = (
            AssignmentSubmission.objects
            .filter(
                assignment=assignment,
                student=request.user,
            )
            .first()
        )

        if existing_submission:

            existing_submission.submission_file = (
                submission_file
            )

            existing_submission.comment = comment

            existing_submission.save()

            messages.success(
                request,
                "Assignment submission updated successfully."
            )

        else:

            AssignmentSubmission.objects.create(
                assignment=assignment,
                student=request.user,
                submission_file=submission_file,
                comment=comment,
            )

            messages.success(
                request,
                "Assignment submitted successfully."
            )

        return redirect(
            "academics:student_assignments"
        )

    return render(
        request,
        "academics/student_submit_assignment.html",
        {
            "student": credential,
            "assignment": assignment,
            "breadcrumb": (
                "Student / Assignments / Submit"
            ),
        },
    )


# =========================================================
# STUDENT - DOWNLOAD ASSIGNMENT
# =========================================================

@login_required
def student_download_assignment(
    request,
    assignment_id,
):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "Student profile not found."
        )

    if request.user.profile.role != "student":
        return HttpResponseForbidden(
            "Only students can download assignments."
        )

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "class_section"
        ),
        id=assignment_id,
    )

    credential = (
        StudentAdmissionApplication.objects
        .filter(
            credential__user=request.user,
            credential__is_active=True,
            status="account_created",
        )
        .select_related("class_section")
        .first()
    )

    if not credential:
        return HttpResponseForbidden(
            "Student account is not linked correctly."
        )

    if assignment.class_section_id != credential.class_section_id:
        return HttpResponseForbidden(
            "You cannot access this assignment."
        )

    if not assignment.assignment_file:
        return HttpResponseForbidden(
            "Assignment file is not available."
        )

    return FileResponse(
        assignment.assignment_file.open("rb"),
        as_attachment=True,
        filename=assignment.assignment_file.name.split("/")[-1],
    )


# =========================================================
# STUDENT - DOWNLOAD SUBMISSION
# =========================================================

@login_required
def student_download_submission(
    request,
    submission_id,
):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "Student profile not found."
        )

    if request.user.profile.role != "student":
        return HttpResponseForbidden(
            "Only students can download submissions."
        )

    submission = get_object_or_404(
        AssignmentSubmission.objects
        .select_related(
            "assignment",
            "assignment__subject",
        ),
        id=submission_id,
        student=request.user,
    )

    if not submission.submission_file:
        return HttpResponseForbidden(
            "Submission file is not available."
        )

    return FileResponse(
        submission.submission_file.open("rb"),
        as_attachment=True,
        filename=(
            submission.submission_file.name
            .split("/")[-1]
        ),
    )

# =========================================================
# STUDENT / PARENT - TIMETABLE
# =========================================================

@login_required
def student_timetable(request):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden("User profile not found.")

    role = str(request.user.profile.role).lower()

    if role not in ["student", "parent"]:
        return HttpResponseForbidden(
            "Only students and parents can access this timetable."
        )

    student = get_academic_student(request)

    if not student:
        return render(
            request,
            "academics/student_timetable.html",
            {
                "student": None,
                "class_section": None,
                "timetable_entries": [],
                "days": [],
                "periods": [],
                "timetable_grid": {},
                "academic_year": "",
                "parent_children": [],
                "is_parent_view": role == "parent",
                "error_message": (
                    "No linked student record was found."
                ),
                "breadcrumb": "Academics / Timetable",
            },
        )

    # Verify parent-child relationship
    if role == "parent":
        is_linked = ParentStudent.objects.filter(
            parent=request.user,
            student=student,
            is_active=True,
        ).exists()

        if not is_linked:
            return HttpResponseForbidden(
                "You cannot access this student's timetable."
            )

    class_section = student.class_section

    parent_children = []

    if role == "parent":
        parent_children = list(
            StudentAdmissionApplication.objects
            .filter(
                id__in=ParentStudent.objects.filter(
                    parent=request.user,
                    is_active=True,
                ).values_list("student_id", flat=True),
                status="account_created",
            )
            .order_by("first_name", "last_name")
        )

    if not class_section:
        return render(
            request,
            "academics/student_timetable.html",
            {
                "student": student,
                "class_section": None,
                "timetable_entries": [],
                "days": [],
                "periods": [],
                "timetable_grid": {},
                "academic_year": "",
                "parent_children": parent_children,
                "selected_student_id": student.id,
                "is_parent_view": role == "parent",
                "error_message": (
                    "No Class & Section has been assigned to this student."
                ),
                "breadcrumb": "Academics / Timetable",
            },
        )

    academic_year = class_section.academic_year

    timetable_entries = (
        TimetableEntry.objects
        .filter(
            class_section=class_section,
            academic_year=academic_year,
            is_active=True,
        )
        .select_related(
            "subject",
            "employee",
            "class_section",
        )
        .order_by("day", "period")
    )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]

    periods = sorted(
        set(
            timetable_entries.values_list(
                "period",
                flat=True,
            )
        )
    )

    timetable_grid = {}

    for entry in timetable_entries:
        if entry.day not in timetable_grid:
            timetable_grid[entry.day] = {}

        timetable_grid[entry.day][entry.period] = entry

    return render(
        request,
        "academics/student_timetable.html",
        {
            "student": student,
            "class_section": class_section,
            "timetable_entries": timetable_entries,
            "days": days,
            "periods": periods,
            "timetable_grid": timetable_grid,
            "academic_year": academic_year,
            "parent_children": parent_children,
            "selected_student_id": student.id,
            "is_parent_view": role == "parent",
            "breadcrumb": (
                "Parent / Child Timetable"
                if role == "parent"
                else "Student / My Timetable"
            ),
        },
    )
  
# =========================================================
# STUDENT / PARENT - RESULTS
# =========================================================

@login_required
def student_all_results(request):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden("User profile not found.")

    role = str(request.user.profile.role).lower()

    if role not in ["student", "parent"]:
        return HttpResponseForbidden(
            "Only students and parents can view results."
        )

    # Student: own record
    # Parent: only linked child from ParentStudent
    student = get_academic_student(request)

    parent_children = []

    if role == "parent":
        parent_children = list(
            StudentAdmissionApplication.objects.filter(
                id__in=ParentStudent.objects.filter(
                    parent=request.user,
                    is_active=True,
                ).values_list("student_id", flat=True),
                status="account_created",
            ).select_related("class_section").order_by(
                "first_name",
                "last_name",
            )
        )

    if not student:
        return render(
            request,
            "academics/student_all_results.html",
            {
                "student": None,
                "class_section": None,
                "results": [],
                "total_exams": 0,
                "total_subjects": 0,
                "parent_children": parent_children,
                "selected_student_id": "",
                "is_parent_view": role == "parent",
                "breadcrumb": (
                    "Parent / Child Results"
                    if role == "parent"
                    else "Student / Results"
                ),
                "error_message": (
                    "No linked student record was found."
                ),
            },
        )

    # Extra security: selected child must be linked to this parent
    if role == "parent":
        is_linked = ParentStudent.objects.filter(
            parent=request.user,
            student=student,
            is_active=True,
        ).exists()

        if not is_linked:
            return HttpResponseForbidden(
                "You cannot access this student's results."
            )

    class_section = student.class_section

    if not class_section:
        return render(
            request,
            "academics/student_all_results.html",
            {
                "student": student,
                "class_section": None,
                "results": [],
                "total_exams": 0,
                "total_subjects": 0,
                "parent_children": parent_children,
                "selected_student_id": student.id,
                "is_parent_view": role == "parent",
                "breadcrumb": (
                    "Parent / Child Results"
                    if role == "parent"
                    else "Student / Results"
                ),
                "error_message": (
                    "No Class & Section has been assigned to this student."
                ),
            },
        )

    # Show only published results for the selected child/student
    results = (
        ExamMark.objects
        .filter(
            student=student,
            class_section=class_section,
            status="published",
            examination__status="published",
        )
        .select_related(
            "examination",
            "subject",
            "assignment",
            "class_section",
        )
        .order_by(
            "-examination__start_date",
            "subject__subject_name",
        )
    )

    total_exams = (
        results.values("examination_id")
        .distinct()
        .count()
    )

    total_subjects = (
        results.values("subject_id")
        .distinct()
        .count()
    )

    return render(
        request,
        "academics/student_all_results.html",
        {
            "student": student,
            "class_section": class_section,
            "results": results,
            "total_exams": total_exams,
            "total_subjects": total_subjects,
            "parent_children": parent_children,
            "selected_student_id": student.id,
            "is_parent_view": role == "parent",
            "breadcrumb": (
                "Parent / Child Results"
                if role == "parent"
                else "Student / Results"
            ),
        },
    )

# =========================================================
# PARENT - CHILD TEACHER MESSAGES
# =========================================================

@login_required
def parent_child_messages(request):

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden("User profile not found.")

    role = str(request.user.profile.role).lower()

    if role != "parent":
        return HttpResponseForbidden(
            "Only parents can access child messages."
        )

    # Get only children linked to the logged-in parent
    parent_children = list(
        StudentAdmissionApplication.objects.filter(
            id__in=ParentStudent.objects.filter(
                parent=request.user,
                is_active=True,
            ).values_list("student_id", flat=True),
            status="account_created",
        ).order_by(
            "first_name",
            "last_name",
        )
    )

    # Get the selected linked child
    student = get_academic_student(request)

    if not student:
        return render(
            request,
            "academics/parent_child_messages.html",
            {
                "student": None,
                "parent_children": parent_children,
                "selected_student_id": "",
                "message_history": [],
                "is_parent_view": True,
                "error_message": (
                    "No linked child was found for your account."
                ),
                "breadcrumb": "Parent / Child Messages",
            },
        )

    # Security check: parent must have an active link to this child
    if not ParentStudent.objects.filter(
        parent=request.user,
        student=student,
        is_active=True,
    ).exists():
        return HttpResponseForbidden(
            "You cannot access messages for this student."
        )

    # Show messages sent by teachers to this parent about this child
    message_history = (
        ParentMessage.objects
        .filter(
            parent=request.user,
            student=student,
        )
        .select_related(
            "teacher",
            "student",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "academics/parent_child_messages.html",
        {
            "student": student,
            "parent_children": parent_children,
            "selected_student_id": student.id,
            "message_history": message_history,
            "is_parent_view": True,
            "breadcrumb": "Parent / Child Messages",
        },
    )