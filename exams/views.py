from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.models import UserProfile

from admissions.models import (
    StudentAdmissionApplication,
    ParentStudent,
)

from academics.models import (
    ClassSection,
    Subject,
    SubjectEmployeeAssignment,
)

from .models import (
    Examination,
    ExamClassSubjectAssignment,
    ExamMark,
)

from .forms import (
    ExaminationForm,
    ExamAssignmentForm,
)

def get_role(user):
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return None


def is_management(user):
    return get_role(user) in [
        "principal",
        "vice_principal",
        "system_administrator",
        "chairman",
    ]


def is_teacher(user):
    return get_role(user) == "teacher"


# =========================================================
# EXAMINATION LIST
# =========================================================

@login_required
def examination_list(request):

    if not is_management(request.user):
        messages.error(
            request,
            "You do not have permission to manage examinations."
        )
        return redirect("dashboard:home")

    examinations = (
        Examination.objects
        .select_related("created_by")
        .order_by("-start_date", "-id")
    )

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    academic_year = request.GET.get("academic_year", "").strip()

    if search:
        examinations = examinations.filter(
            Q(exam_name__icontains=search)
            | Q(exam_type__icontains=search)
        )

    if status:
        examinations = examinations.filter(status=status)

    if academic_year:
        examinations = examinations.filter(
            academic_year=academic_year
        )

    context = {
        "examinations": examinations,

        "search": search,

        "selected_status": status,

        "selected_academic_year": academic_year,

        "total_exams": Examination.objects.count(),

        "published_exams": Examination.objects.filter(
            status="published"
        ).count(),

        "draft_exams": Examination.objects.filter(
            status="draft"
        ).count(),

        "upcoming_exams": Examination.objects.filter(
            status="upcoming"
        ).count(),

        "academic_years": (
            Examination.objects
            .values_list(
                "academic_year",
                flat=True
            )
            .distinct()
            .order_by("-academic_year")
        ),
    }

    return render(
        request,
        "exams/examination_list.html",
        context
    )


# =========================================================
# CREATE EXAMINATION
# =========================================================

@login_required
def examination_create(request):

    if not is_management(request.user):

        messages.error(
            request,
            "You do not have permission to create examinations."
        )

        return redirect("dashboard:home")

    if request.method == "POST":

        form = ExaminationForm(request.POST)

        if form.is_valid():

            examination = form.save(commit=False)

            examination.created_by = request.user

            examination.save()

            messages.success(
                request,
                "Examination created successfully."
            )

            return redirect(
                "exams:examination_detail",
                exam_id=examination.id
            )

    else:

        form = ExaminationForm()

    return render(
        request,
        "exams/examination_form.html",
        {
            "form": form,
            "title": "Create Examination",
        }
    )


# =========================================================
# EDIT EXAMINATION
# =========================================================

@login_required
def examination_edit(request, exam_id):

    if not is_management(request.user):

        messages.error(
            request,
            "You do not have permission."
        )

        return redirect("dashboard:home")

    examination = get_object_or_404(
        Examination,
        id=exam_id
    )

    if examination.status == "published":

        messages.error(
            request,
            "Published examination cannot be edited."
        )

        return redirect(
            "exams:examination_detail",
            exam_id=exam_id
        )

    if request.method == "POST":

        form = ExaminationForm(
            request.POST,
            instance=examination
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Examination updated successfully."
            )

            return redirect(
                "exams:examination_detail",
                exam_id=exam_id
            )

    else:

        form = ExaminationForm(
            instance=examination
        )

    return render(
        request,
        "exams/examination_form.html",
        {
            "form": form,
            "title": "Edit Examination",
            "examination": examination,
        }
    )


# =========================================================
# EXAMINATION DETAIL
# =========================================================

@login_required
def examination_detail(request, exam_id):

    if not is_management(request.user):

        messages.error(
            request,
            "You do not have permission."
        )

        return redirect("dashboard:home")

    examination = get_object_or_404(
        Examination.objects.prefetch_related(
            "assignments__class_section",
            "assignments__subject",
        ),
        id=exam_id
    )

    assignments = examination.assignments.all()

    total_marks = sum(
        (
            assignment.max_marks
            for assignment in assignments
        ),
        Decimal("0")
    )

    context = {

        "examination": examination,

        "assignments": assignments,

        "total_assignments": assignments.count(),

        "total_marks": total_marks,

    }

    return render(
        request,
        "exams/examination_detail.html",
        context
    )

@login_required
def assign_exam_subject(request, exam_id):

    # =========================================
    # 1. PERMISSION CHECK
    # =========================================
    if not is_management(request.user):
        messages.error(request, "You do not have permission.")
        return redirect("dashboard:home")

    # =========================================
    # 2. GET EXAMINATION
    # =========================================
    examination = get_object_or_404(
        Examination,
        id=exam_id
    )

    if examination.status == "published":
        messages.error(
            request,
            "Published examination cannot be modified."
        )
        return redirect(
            "exams:examination_detail",
            exam_id=exam_id
        )

    # =========================================
    # 3. HANDLE FORM
    # =========================================
    if request.method == "POST":

        form = ExamAssignmentForm(request.POST)

        if form.is_valid():

            selected_class_section = (
                form.cleaned_data.get("class_section")
            )

            subject = form.cleaned_data["subject"]
            exam_date = form.cleaned_data["exam_date"]
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            max_marks = form.cleaned_data["max_marks"]
            passing_marks = form.cleaned_data["passing_marks"]

            # =====================================
            # 4. SELECT CLASS SECTIONS
            # =====================================
            if selected_class_section:
                # Individual class/section selected
                class_sections = [selected_class_section]
            else:
                # All Classes & Sections selected
                class_sections = list(
                    ClassSection.objects.all()
                )

            if not class_sections:
                form.add_error(
                    "class_section",
                    "No class sections are available."
                )

            else:
                created_count = 0
                skipped_count = 0

                # =====================================
                # 5. CREATE ASSIGNMENTS
                # =====================================
                try:
                    with transaction.atomic():

                        for class_section in class_sections:

                            # Check for an existing assignment
                            already_exists = (
                                ExamClassSubjectAssignment.objects.filter(
                                    examination=examination,
                                    class_section=class_section,
                                    subject=subject,
                                ).exists()
                            )

                            if already_exists:
                                skipped_count += 1
                                continue

                            ExamClassSubjectAssignment.objects.create(
                                examination=examination,
                                class_section=class_section,
                                subject=subject,
                                exam_date=exam_date,
                                start_time=start_time,
                                end_time=end_time,
                                max_marks=max_marks,
                                passing_marks=passing_marks,
                            )

                            created_count += 1

                    # =====================================
                    # 6. SUCCESS / WARNING MESSAGES
                    # =====================================
                    if created_count > 0:
                        messages.success(
                            request,
                            f"Exam assignment created for "
                            f"{created_count} class section(s)."
                        )

                    if skipped_count > 0:
                        messages.warning(
                            request,
                            f"{skipped_count} class section(s) "
                            f"were skipped because the same "
                            f"subject is already assigned."
                        )

                    if created_count == 0 and skipped_count > 0:
                        messages.info(
                            request,
                            "No new assignments were created."
                        )

                    return redirect(
                        "exams:examination_detail",
                        exam_id=exam_id
                    )

                except IntegrityError:
                    messages.error(
                        request,
                        "A duplicate assignment was detected. "
                        "Please check the existing assignments."
                    )

    else:
        form = ExamAssignmentForm()

    # =========================================
    # 7. RENDER FORM
    # =========================================
    return render(
        request,
        "exams/assignment_form.html",
        {
            "form": form,
            "examination": examination,
        }
    )

@login_required
def remove_exam_assignment(request, assignment_id):

    if not is_management(request.user):

        messages.error(
            request,
            "You do not have permission."
        )

        return redirect("dashboard:home")

    assignment = get_object_or_404(
        ExamClassSubjectAssignment,
        id=assignment_id
    )

    exam = assignment.examination

    if exam.status == "published":

        messages.error(
            request,
            "Published examination cannot be modified."
        )

        return redirect(
            "exams:examination_detail",
            exam_id=exam.id
        )

    assignment.delete()

    messages.success(
        request,
        "Exam assignment removed."
    )

    return redirect(
        "exams:examination_detail",
        exam_id=exam.id
    )

@login_required
def teacher_marks(request):

    # =====================================================
    # TEACHER ROLE CHECK
    # =====================================================

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "User profile not found."
        )

    if request.user.profile.role != "teacher":
        return HttpResponseForbidden(
            "Only teachers can access marks entry."
        )

    # =====================================================
    # IMPORT MODELS
    # =====================================================

    from academics.models import (
        ClassSection,
        Subject,
        SubjectEmployeeAssignment,
    )

    from admissions.models import (
        StudentAdmissionApplication,
    )

    # =====================================================
    # GET ALL CLASSES ASSIGNED TO THIS TEACHER
    #
    # 1. Class teacher assignments
    # 2. Subject teacher assignments
    #
    # We combine both.
    # =====================================================

    class_teacher_classes = (
        ClassSection.objects
        .filter(
            class_teacher=request.user
        )
    )

    subject_teacher_class_ids = (
        SubjectEmployeeAssignment.objects
        .filter(
            employee=request.user,
            is_active=True,
        )
        .values_list(
            "class_section_id",
            flat=True,
        )
        .distinct()
    )

    assigned_classes = (
        ClassSection.objects
        .filter(
            models.Q(
                class_teacher=request.user
            )
            |
            models.Q(
                id__in=subject_teacher_class_ids
            )
        )
        .distinct()
        .order_by(
            "academic_year",
            "grade",
            "section",
        )
    )

    # =====================================================
    # SELECT CLASS
    # =====================================================

    selected_class_id = request.GET.get(
        "class_section"
    )

    selected_class = None

    if selected_class_id:

        selected_class = (
            assigned_classes
            .filter(
                id=selected_class_id
            )
            .first()
        )

    # -----------------------------------------------------
    # DEFAULT CLASS
    # -----------------------------------------------------

    if selected_class is None:

        selected_class = (
            assigned_classes.first()
        )

    # =====================================================
    # GET TEACHER'S SUBJECT ASSIGNMENTS
    #
    # IMPORTANT:
    # Subjects must come from
    # SubjectEmployeeAssignment.
    # =====================================================

    subject_assignments = (
        SubjectEmployeeAssignment.objects
        .filter(
            employee=request.user,
            is_active=True,
        )
        .select_related(
            "subject",
            "class_section",
        )
        .order_by(
            "class_section__grade",
            "class_section__section",
            "subject__subject_name",
        )
    )

    # =====================================================
    # FILTER SUBJECT ASSIGNMENTS BY SELECTED CLASS
    # =====================================================

    selected_subject_assignments = (
        subject_assignments
    )

    if selected_class:

        selected_subject_assignments = (
            subject_assignments
            .filter(
                class_section=selected_class
            )
        )

    # =====================================================
    # SUBJECTS FOR SELECTED CLASS
    # =====================================================

    subjects = (
        Subject.objects
        .filter(
            id__in=selected_subject_assignments
            .values_list(
                "subject_id",
                flat=True,
            )
        )
        .order_by(
            "subject_name"
        )
    )

    # =====================================================
    # SELECT SUBJECT
    # =====================================================

    selected_subject_id = request.GET.get(
        "subject"
    )

    selected_subject = None

    if selected_subject_id:

        selected_subject = (
            subjects
            .filter(
                id=selected_subject_id
            )
            .first()
        )

    # =====================================================
    # STUDENTS
    #
    # Students are taken from the selected
    # ClassSection.
    # =====================================================

    students = (
        StudentAdmissionApplication.objects
        .filter(
            class_section=selected_class,
            status="account_created",
        )
        .order_by(
            "first_name",
            "last_name",
        )
    )

    # =====================================================
    # EXAMINATIONS
    # =====================================================

    examinations = (
        Examination.objects
        .filter(
            status__in=[
                "draft",
                "published",
            ]
        )
        .order_by(
            "-start_date"
        )
    )

    # =====================================================
    # SELECT EXAM
    # =====================================================

    selected_exam_id = request.GET.get(
        "examination"
    )

    selected_examination = None

    if selected_exam_id:

        selected_examination = (
            examinations
            .filter(
                id=selected_exam_id
            )
            .first()
        )

    # =====================================================
    # EXAM ASSIGNMENT
    # =====================================================

    exam_assignment = None

    if (
        selected_examination
        and selected_class
        and selected_subject
    ):

        exam_assignment = (
            ExamClassSubjectAssignment.objects
            .filter(
                examination=selected_examination,
                class_section=selected_class,
                subject=selected_subject,
            )
            .select_related(
                "examination",
                "class_section",
                "subject",
            )
            .first()
        )

    # =====================================================
    # EXISTING MARKS
    # =====================================================

    marks = {}

    if exam_assignment:

        existing_marks = (
            ExamMark.objects
            .filter(
                assignment=exam_assignment,
                student__in=students,
            )
            .select_related(
                "student",
                "assignment",
            )
        )

        marks = {
            mark.student_id: mark
            for mark in existing_marks
        }

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        # Classes
        "assigned_classes": assigned_classes,
        "selected_class": selected_class,

        # Subjects
        "subject_assignments": selected_subject_assignments,
        "subjects": subjects,
        "selected_subject": selected_subject,

        # Students
        "students": students,
        "student_count": students.count(),

        # Exams
        "examinations": examinations,
        "selected_examination": selected_examination,

        # Assignment
        "exam_assignment": exam_assignment,

        # Marks
        "marks": marks,

    }

    return render(
        request,
        "exams/teacher_marks.html",
        context,
    )

@login_required
def save_teacher_marks(request, assignment_id):

    if not is_teacher(request.user):

        messages.error(
            request,
            "Only teachers can enter marks."
        )

        return redirect("dashboard:home")

    assignment = get_object_or_404(
        ExamClassSubjectAssignment.objects.select_related(
            "examination",
            "class_section",
            "subject",
        ),
        id=assignment_id
    )

    teacher_assignment_exists = (
        SubjectEmployeeAssignment.objects
        .filter(
            employee=request.user,
            class_section=assignment.class_section,
            subject=assignment.subject,
            is_active=True,
        )
        .exists()
    )

    if not teacher_assignment_exists:

        messages.error(
            request,
            "You are not assigned to this subject and class."
        )

        return redirect(
            "exams:teacher_marks"
        )

    if assignment.examination.status == "published":

        messages.error(
            request,
            "Published examination cannot be edited."
        )

        return redirect(
            "exams:teacher_marks"
        )

    if request.method != "POST":

        return redirect(
            "exams:teacher_marks"
        )

    student_ids = request.POST.getlist(
        "student_id"
    )

    for student_id in student_ids:

        student = (
            StudentAdmissionApplication.objects
            .filter(
                id=student_id,
                status="account_created",
                class_section=assignment.class_section,
            )
            .first()
        )

        if not student:
            continue

        marks_value = request.POST.get(
            f"obtained_marks_{student.id}",
            ""
        ).strip()

        remarks = request.POST.get(
            f"remarks_{student.id}",
            ""
        ).strip()

        if marks_value == "":
            continue

        try:

            obtained_marks = Decimal(
                marks_value
            )

        except (InvalidOperation, ValueError):

            messages.error(
                request,
                (
                    f"Invalid marks entered for "
                    f"{student.first_name}."
                )
            )

            continue

        if obtained_marks < 0:

            obtained_marks = Decimal("0")

        if obtained_marks > assignment.max_marks:

            messages.error(
                request,
                (
                    f"Marks for {student.first_name} "
                    f"cannot exceed "
                    f"{assignment.max_marks}."
                )
            )

            continue

        mark, created = ExamMark.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={
                "entered_by": request.user,
                "status": "draft",
                "obtained_marks": obtained_marks,
                "remarks": remarks,
            }
        )

        if not created:

            if mark.status == "published":
                continue

            mark.obtained_marks = obtained_marks
            mark.remarks = remarks
            mark.entered_by = request.user
            mark.status = "draft"

            mark.save()

    messages.success(
        request,
        "Marks saved successfully."
    )

    return redirect(
        f"/exams/teacher/marks/?assignment={assignment.id}"
    )

@login_required
def submit_teacher_marks(request, assignment_id):

    if not is_teacher(request.user):

        messages.error(
            request,
            "Only teachers can submit marks."
        )

        return redirect("dashboard:home")

    assignment = get_object_or_404(
        ExamClassSubjectAssignment.objects.select_related(
            "examination",
            "class_section",
            "subject",
        ),
        id=assignment_id
    )

    teacher_assignment_exists = (
        SubjectEmployeeAssignment.objects
        .filter(
            employee=request.user,
            class_section=assignment.class_section,
            subject=assignment.subject,
            is_active=True,
        )
        .exists()
    )

    if not teacher_assignment_exists:

        messages.error(
            request,
            "You are not assigned to this subject."
        )

        return redirect(
            "exams:teacher_marks"
        )

    if request.method != "POST":

        return redirect(
            "exams:teacher_marks"
        )

    if assignment.examination.status == "published":

        messages.error(
            request,
            "Published examination cannot be modified."
        )

        return redirect(
            "exams:teacher_marks"
        )

    students = (
        StudentAdmissionApplication.objects
        .filter(
            status="account_created",
            class_section=assignment.class_section,
        )
    )

    missing_students = []

    for student in students:

        mark = (
            ExamMark.objects
            .filter(
                assignment=assignment,
                student=student,
            )
            .first()
        )

        if not mark:

            missing_students.append(student)

    if missing_students:

        messages.error(
            request,
            (
                "Please enter marks for all students "
                "before submitting."
            )
        )

        return redirect(
            f"/exams/teacher/marks/?assignment={assignment.id}"
        )

    ExamMark.objects.filter(
        assignment=assignment,
        status="draft",
    ).update(
        status="submitted"
    )

    messages.success(
        request,
        "Marks submitted for approval."
    )

    return redirect(
        "exams:teacher_marks"
    )

@login_required
def publish_examination(request, exam_id):

    if not is_management(request.user):

        messages.error(
            request,
            "You do not have permission."
        )

        return redirect("dashboard:home")

    examination = get_object_or_404(
        Examination,
        id=exam_id
    )

    if examination.status == "published":

        messages.info(
            request,
            "Examination is already published."
        )

        return redirect(
            "exams:examination_detail",
            exam_id=exam_id
        )

    assignments = examination.assignments.all()

    if not assignments.exists():

        messages.error(
            request,
            "Assign at least one class and subject first."
        )

        return redirect(
            "exams:examination_detail",
            exam_id=exam_id
        )

    draft_count = ExamMark.objects.filter(
        assignment__examination=examination,
        status="draft",
    ).count()

    if draft_count > 0:

        messages.error(
            request,
            (
                "Some marks are still in Draft status. "
                "Teachers must submit all marks first."
            )
        )

        return redirect(
            "exams:examination_detail",
            exam_id=exam_id
        )

    examination.status = "published"

    examination.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    ExamMark.objects.filter(
        assignment__examination=examination,
        status="submitted",
    ).update(
        status="published"
    )

    messages.success(
        request,
        "Examination results published successfully."
    )

    return redirect(
        "exams:examination_detail",
        exam_id=exam_id
    )

@login_required
def result_list(request):

    if not is_management(request.user):

        messages.error(
            request,
            "You do not have permission."
        )

        return redirect("dashboard:home")

    examinations = (
        Examination.objects
        .filter(
            status="published"
        )
        .select_related("created_by")
        .order_by(
            "-start_date"
        )
    )

    context = {

        "examinations": examinations,

        "total_results": examinations.count(),

        "total_students": (
            ExamMark.objects
            .filter(
                assignment__examination__status="published"
            )
            .values("student")
            .distinct()
            .count()
        ),

        "passed_results": 0,

        "failed_results": 0,

    }

    return render(
        request,
        "exams/RESULT_LIST.HTML",
        context
    )

def get_logged_in_student(user):

    return (
        StudentAdmissionApplication.objects
        .filter(
            credential__user=user,
            credential__is_active=True,
            status="account_created",
        )
        .select_related(
            "class_section"
        )
        .first()
    )

@login_required
def student_marks(request):

    if get_role(request.user) != "student":

        messages.error(
            request,
            "Student access only."
        )

        return redirect("dashboard:home")

    student = get_logged_in_student(
        request.user
    )

    if not student:

        messages.error(
            request,
            "Student account is not linked."
        )

        return redirect("dashboard:home")

    exams = (
        Examination.objects
        .filter(
            status="published",
            assignments__marks__student=student,
            assignments__marks__status="published",
        )
        .distinct()
        .order_by(
            "-start_date"
        )
    )

    selected_exam_id = request.GET.get(
        "exam"
    )

    selected_exam = None

    if selected_exam_id:

        selected_exam = (
            exams
            .filter(
                id=selected_exam_id
            )
            .first()
        )

    if not selected_exam:

        selected_exam = exams.first()

    marks = ExamMark.objects.none()

    if selected_exam:

        marks = (
            ExamMark.objects
            .filter(
                assignment__examination=selected_exam,
                student=student,
                status="published",
            )
            .select_related(
                "assignment",
                "assignment__subject",
                "assignment__class_section",
            )
            .order_by(
                "assignment__subject__subject_name"
            )
        )

    total_obtained = sum(
        (
            mark.obtained_marks
            for mark in marks
            if mark.obtained_marks is not None
        ),
        Decimal("0")
    )

    total_maximum = sum(
        (
            mark.max_marks
            for mark in marks
        ),
        Decimal("0")
    )

    if total_maximum:

        overall_percentage = round(
            (
                float(total_obtained)
                /
                float(total_maximum)
            ) * 100,
            2
        )

    else:

        overall_percentage = 0

    context = {

        "student": student,

        "examinations": exams,

        "exams": exams,

        "selected_examination": selected_exam,

        "selected_exam": selected_exam,

        "marks": marks,

        "total_obtained": total_obtained,

        "total_maximum": total_maximum,

        "overall_percentage": overall_percentage,

    }

    return render(
        request,
        "exams/student_marks.html",
        context
    )

@login_required
def student_results(request):

    if get_role(request.user) != "student":

        messages.error(
            request,
            "Student access only."
        )

        return redirect("dashboard:home")

    student = get_logged_in_student(
        request.user
    )

    if not student:

        messages.error(
            request,
            "Student account is not linked."
        )

        return redirect("dashboard:home")

    exams = (
        Examination.objects
        .filter(
            status="published",
            assignments__marks__student=student,
            assignments__marks__status="published",
        )
        .distinct()
        .order_by(
            "-start_date"
        )
    )

    selected_exam_id = request.GET.get(
        "exam"
    )

    selected_exam = None

    if selected_exam_id:

        selected_exam = (
            exams
            .filter(
                id=selected_exam_id
            )
            .first()
        )

    if not selected_exam:

        selected_exam = exams.first()

    marks = ExamMark.objects.none()

    if selected_exam:

        marks = (
            ExamMark.objects
            .filter(
                assignment__examination=selected_exam,
                student=student,
                status="published",
            )
            .select_related(
                "assignment",
                "assignment__subject",
                "assignment__class_section",
            )
            .order_by(
                "assignment__subject__subject_name"
            )
        )

    total_obtained = sum(
        (
            mark.obtained_marks
            for mark in marks
            if mark.obtained_marks is not None
        ),
        Decimal("0")
    )

    total_maximum = sum(
        (
            mark.max_marks
            for mark in marks
        ),
        Decimal("0")
    )

    if total_maximum:

        overall_percentage = round(
            (
                float(total_obtained)
                /
                float(total_maximum)
            ) * 100,
            2
        )

    else:

        overall_percentage = 0

    context = {

        "student": student,

        "examinations": exams,

        "exams": exams,

        "selected_examination": selected_exam,

        "selected_exam": selected_exam,

        "marks": marks,

        "total_obtained": total_obtained,

        "total_maximum": total_maximum,

        "overall_percentage": overall_percentage,

    }

    return render(
        request,
        "exams/student_results.html",
        context
    )

@login_required
def report_card(
    request,
    exam_id,
    student_id=None,
):

    role = get_role(request.user)

    allowed_roles = [
        "student",
        "parent",
        "principal",
        "vice_principal",
        "system_administrator",
        "chairman",
    ]

    if role not in allowed_roles:

        messages.error(
            request,
            "You do not have permission."
        )

        return redirect("dashboard:home")

    examination = get_object_or_404(
        Examination,
        id=exam_id,
        status="published",
    )

    # -----------------------------------------------------
    # STUDENT
    # -----------------------------------------------------

    if role == "student":

        student = get_logged_in_student(
            request.user
        )

    # -----------------------------------------------------
    # PARENT
    # -----------------------------------------------------

    elif role == "parent":

        if not student_id:

            student_link = (
                ParentStudent.objects
                .filter(
                    parent=request.user,
                    is_active=True,
                )
                .select_related(
                    "student"
                )
                .first()
            )

            student = (
                student_link.student
                if student_link
                else None
            )

        else:

            student = (
                StudentAdmissionApplication.objects
                .filter(
                    id=student_id,
                    parent_links__parent=request.user,
                    parent_links__is_active=True,
                )
                .first()
            )

    # -----------------------------------------------------
    # MANAGEMENT
    # -----------------------------------------------------

    else:

        if not student_id:

            student = None

        else:

            student = (
                StudentAdmissionApplication.objects
                .filter(
                    id=student_id
                )
                .first()
            )

    if not student:

        messages.error(
            request,
            "Student not found."
        )

        if role == "student":

            return redirect(
                "exams:student_results"
            )

        if role == "parent":

            return redirect(
                "exams:parent_results"
            )

        return redirect(
            "exams:result_list"
        )

    marks = (
        ExamMark.objects
        .filter(
            assignment__examination=examination,
            student=student,
            status="published",
        )
        .select_related(
            "assignment",
            "assignment__subject",
            "assignment__class_section",
        )
        .order_by(
            "assignment__subject__subject_name"
        )
    )

    total_obtained = sum(
        (
            mark.obtained_marks
            for mark in marks
            if mark.obtained_marks is not None
        ),
        Decimal("0")
    )

    total_maximum = sum(
        (
            mark.max_marks
            for mark in marks
        ),
        Decimal("0")
    )

    if total_maximum:

        percentage = round(
            (
                float(total_obtained)
                /
                float(total_maximum)
            ) * 100,
            2
        )

    else:

        percentage = 0

    failed = any(
        mark.obtained_marks is not None
        and mark.obtained_marks < mark.assignment.passing_marks
        for mark in marks
    )

    result_status = (
        "FAIL"
        if failed
        else "PASS"
    )

    context = {

        "examination": examination,

        "student": student,

        "marks": marks,

        "total_obtained": total_obtained,

        "total_maximum": total_maximum,

        "overall_percentage": percentage,

        "percentage": percentage,

        "result_status": result_status,

        "is_passed": not failed,

    }

    return render(
        request,
        "exams/report_card.html",
        context
    )

@login_required
def parent_results(request):

    if get_role(request.user) != "parent":

        messages.error(
            request,
            "Parent access only."
        )

        return redirect("dashboard:home")

    children_links = (
        ParentStudent.objects
        .filter(
            parent=request.user,
            is_active=True,
        )
        .select_related(
            "student"
        )
    )

    children = [
        link.student
        for link in children_links
    ]

    selected_child_id = request.GET.get(
        "child"
    )

    selected_exam_id = request.GET.get(
        "exam"
    )

    examinations = (
        Examination.objects
        .filter(
            status="published",
            assignments__marks__status="published",
        )
        .distinct()
        .order_by(
            "-start_date"
        )
    )

    selected_child = None

    if selected_child_id:

        for child in children:

            if str(child.id) == str(
                selected_child_id
            ):

                selected_child = child

                break

    if not selected_child and children:

        selected_child = children[0]

    selected_examination = None

    if selected_exam_id:

        selected_examination = (
            examinations
            .filter(
                id=selected_exam_id
            )
            .first()
        )

    if not selected_examination:

        selected_examination = examinations.first()

    results = []

    if selected_child and selected_examination:

        marks = (
            ExamMark.objects
            .filter(
                assignment__examination=selected_examination,
                student=selected_child,
                status="published",
            )
            .select_related(
                "assignment",
                "assignment__subject",
                "assignment__class_section",
            )
            .order_by(
                "assignment__subject__subject_name"
            )
        )

        for mark in marks:

            if mark.obtained_marks is not None:

                percentage = round(
                    (
                        float(mark.obtained_marks)
                        /
                        float(mark.max_marks)
                    ) * 100,
                    2
                )

            else:

                percentage = 0

            mark.percentage = percentage

            mark.is_passed = (
                mark.obtained_marks is not None
                and mark.obtained_marks >= mark.assignment.passing_marks
            )

            results.append(mark)

    total_obtained = sum(
        (
            mark.obtained_marks
            for mark in results
            if mark.obtained_marks is not None
        ),
        Decimal("0")
    )

    total_maximum = sum(
        (
            mark.max_marks
            for mark in results
        ),
        Decimal("0")
    )

    if total_maximum:

        overall_percentage = round(
            (
                float(total_obtained)
                /
                float(total_maximum)
            ) * 100,
            2
        )

    else:

        overall_percentage = 0

    context = {

        "children": children,

        "examinations": examinations,

        "selected_child": selected_child,

        "selected_examination": selected_examination,

        "results": results,

        "total_obtained": total_obtained,

        "total_maximum": total_maximum,

        "overall_percentage": overall_percentage,

    }

    return render(
        request,
        "exams/parent_results.html",
        context
    )

@login_required
def marks_history(request):

    if not is_management(request.user):

        messages.error(
            request,
            "You do not have permission."
        )

        return redirect("dashboard:home")

    marks = (
        ExamMark.objects
        .select_related(
            "assignment",
            "assignment__examination",
            "assignment__class_section",
            "assignment__subject",
            "student",
            "entered_by",
        )
        .order_by(
            "-updated_at"
        )
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    examination_id = request.GET.get(
        "examination",
        ""
    ).strip()

    class_section_id = request.GET.get(
        "class_section",
        ""
    ).strip()

    subject_id = request.GET.get(
        "subject",
        ""
    ).strip()

    mark_status = request.GET.get(
        "status",
        ""
    ).strip()

    if search:

        marks = marks.filter(
            Q(
                student__first_name__icontains=search
            )
            |
            Q(
                student__last_name__icontains=search
            )
            |
            Q(
                student__application_id__icontains=search
            )
            |
            Q(
                assignment__examination__exam_name__icontains=search
            )
        )

    if examination_id:

        marks = marks.filter(
            assignment__examination_id=examination_id
        )

    if class_section_id:

        marks = marks.filter(
            assignment__class_section_id=class_section_id
        )

    if subject_id:

        marks = marks.filter(
            assignment__subject_id=subject_id
        )

    if mark_status:

        marks = marks.filter(
            status=mark_status
        )

    context = {

        "marks": marks,

        "examinations": Examination.objects.all().order_by(
            "-start_date"
        ),

        "class_sections": ClassSection.objects.all().order_by(
            "grade",
            "section"
        ),

        "subjects": Subject.objects.all().order_by(
            "subject_name"
        ),

        "search": search,

        "selected_examination": examination_id,

        "selected_class_section": class_section_id,

        "selected_subject": subject_id,

        "selected_status": mark_status,

    }

    return render(
        request,
        "exams/marks_histroy.html",
        context
    )