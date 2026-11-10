from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):

    # =========================================================
    # DOCUMENT CATEGORY
    # =========================================================

    CATEGORY_CHOICES = (
        ("student", "Student Documents"),
        ("employee", "Employee Documents"),
        ("fee", "Fee Documents"),
        ("report", "Reports Documents"),
        ("transport", "Transport Documents"),
        ("personal", "Personal Documents"),
        ("other", "Other Documents"),
    )


    # =========================================================
    # DOCUMENT TYPE
    # =========================================================

    DOCUMENT_TYPE_CHOICES = (

        # -------------------------
        # STUDENT DOCUMENTS
        # -------------------------

        ("aadhaar", "Aadhaar"),

        ("birth_certificate", "Birth Certificate"),

        ("transfer_certificate", "Transfer Certificate"),

        ("bonafide", "Bonafide Certificate"),

        ("marks_memo", "Marks Memo"),

        ("passport_photo", "Passport Photo"),

        ("student_other", "Other Student Document"),


        # -------------------------
        # EMPLOYEE DOCUMENTS
        # -------------------------

        ("employee_aadhaar", "Employee Aadhaar"),

        ("education_certificate", "Education Certificate"),

        ("experience_certificate", "Experience Certificate"),

        ("joining_document", "Joining Document"),

        ("employee_photo", "Employee Photo"),

        ("employee_other", "Other Employee Document"),


        # -------------------------
        # FEE DOCUMENTS
        # -------------------------

        ("fee_receipt", "Fee Receipt"),

        ("payment_receipt", "Payment Receipt"),

        ("fee_statement", "Fee Statement"),

        ("fee_other", "Other Fee Document"),


        # -------------------------
        # REPORT DOCUMENTS
        # -------------------------

        ("academic_report", "Academic Report"),

        ("attendance_report", "Attendance Report"),

        ("examination_report", "Examination Report"),

        ("management_report", "Management Report"),

        ("report_other", "Other Report Document"),


        # -------------------------
        # TRANSPORT DOCUMENTS
        # -------------------------

        ("driving_license", "Driving License"),

        ("vehicle_document", "Vehicle Document"),

        ("route_document", "Route Document"),

        ("transport_other", "Other Transport Document"),


        # -------------------------
        # PERSONAL DOCUMENTS
        # -------------------------

        ("identity_document", "Identity Document"),

        ("address_proof", "Address Proof"),

        ("personal_other", "Other Personal Document"),


        # -------------------------
        # OTHER
        # -------------------------

        ("other", "Other Document"),
    )


    # =========================================================
    # DOCUMENT OWNER
    # =========================================================

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
    )


    # =========================================================
    # CATEGORY
    # =========================================================

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
    )


    # =========================================================
    # DOCUMENT TYPE
    # =========================================================

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
    )


    # =========================================================
    # DOCUMENT NAME
    # =========================================================

    name = models.CharField(
        max_length=200,
    )


    # =========================================================
    # FILE
    # =========================================================

    file = models.FileField(
        upload_to="documents/%Y/%m/",
    )


    # =========================================================
    # DESCRIPTION
    # =========================================================

    description = models.TextField(
        blank=True,
        null=True,
    )


    # =========================================================
    # UPLOADED BY
    # =========================================================

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )


    # =========================================================
    # VERIFICATION
    # =========================================================

    is_verified = models.BooleanField(
        default=False,
    )


    # =========================================================
    # CREATED / UPDATED
    # =========================================================

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    # =========================================================
    # META
    # =========================================================

    class Meta:

        ordering = [
            "-uploaded_at"
        ]


    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        return (
            f"{self.name} - "
            f"{self.owner.username}"
        )