from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class StudentAdmissionApplication(models.Model):

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
    ("submitted", "Submitted"),
    ("system_admin_pending", "System Admin Pending"),
    ("system_admin_accepted", "System Admin Accepted"),
    ("system_admin_rejected", "System Admin Rejected"),
    ("vp_pending", "VP Pending"),
    ("vp_approved", "VP Approved"),
    ("vp_rejected", "VP Rejected"),
    ("account_created", "Account Created"),
    ]

    # -----------------------------------------------------
    # APPLICATION INFORMATION
    # -----------------------------------------------------

    application_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    # -----------------------------------------------------
    # PERSONAL DETAILS
    # -----------------------------------------------------

    first_name = models.CharField(
        max_length=50,
    )

    last_name = models.CharField(
        max_length=50,
        blank=True,
    )

    date_of_birth = models.DateField()

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
    )

    phone = models.CharField(
        max_length=15,
    )

    email = models.EmailField(
        blank=True,
    )

    address = models.TextField()

    # -----------------------------------------------------
    # PARENT DETAILS
    # -----------------------------------------------------

    father_name = models.CharField(
        max_length=100,
    )

    mother_name = models.CharField(
        max_length=100,
    )

    parent_phone = models.CharField(
        max_length=15,
    )

    parent_email = models.EmailField(
        blank=True,
    )

    # -----------------------------------------------------
    # ACADEMIC DETAILS
    # -----------------------------------------------------

    applying_class = models.CharField(
        max_length=50,
    )
    class_section = models.ForeignKey(
        "academics.ClassSection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    previous_school = models.CharField(
        max_length=150,
        blank=True,
    )

    previous_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # STUDENT DOCUMENTS
    # -----------------------------------------------------

    student_photo = models.ImageField(
        upload_to="student_applications/photos/",
        blank=True,
        null=True,
    )

    birth_certificate = models.FileField(
        upload_to="student_applications/birth_certificate/",
        blank=True,
        null=True,
    )

    aadhaar_card = models.FileField(
        upload_to="student_applications/aadhaar/",
        blank=True,
        null=True,
    )

    previous_school_certificate = models.FileField(
        upload_to="student_applications/school_certificate/",
        blank=True,
        null=True,
    )

    transfer_certificate = models.FileField(
        upload_to="student_applications/transfer_certificate/",
        blank=True,
        null=True,
    )
    bus_required = models.BooleanField(
    default=False,
    verbose_name="Bus Required",)
    bus_location = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name="Location",
    )
    bus_route = models.ForeignKey(
    "transport.BusRoute",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="student_applications",
    verbose_name="Bus Route",
    )
    pickup_stop = models.ForeignKey(
    "transport.BusStop",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="student_applications",
    verbose_name="Pickup Stop",)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="submitted",
    )

    # -----------------------------------------------------
    # SUBMISSION INFORMATION
    # -----------------------------------------------------

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_student_applications",
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # -----------------------------------------------------
    # STRING REPRESENTATION
    # -----------------------------------------------------

    def __str__(self):
        return (
            f"{self.application_id} - "
            f"{self.first_name} {self.last_name}"
        )

class StudentCredential(models.Model):
    student_application = models.OneToOneField(
        StudentAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="credential",
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_credential",
    )

    username = models.CharField(
        max_length=150,
        unique=True,
    )
    account_email = models.EmailField(
        blank=True
    )

    temporary_password = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.username} - "
            f"{self.student_application.application_id}"
        )

class EmployeeAdmissionApplication(models.Model):

    STAFF_ROLE_CHOICES = (
        ("teacher", "Teaching Staff"),
        ("admission_staff", "Admission Staff"),
        ("principal", "Principal"),
        ("vice_principal", "Vice Principal"),
        ("chairman", "Chairman"),
        ("accountant", "Accountant"),
        ("system_administrator", "System Administrator"),
        ("bus_driver", "Bus Driver"),
    )

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
    ("submitted", "Submitted"),
    ("system_admin_pending", "System Admin Pending"),
    ("system_admin_accepted", "System Admin Accepted"),
    ("system_admin_rejected", "System Admin Rejected"),
    ("vp_pending", "VP Pending"),
    ("vp_approved", "VP Approved"),
    ("vp_rejected", "VP Rejected"),
    ("account_created", "Account Created"),
    ]

    # -----------------------------------------------------
    # APPLICATION INFORMATION
    # -----------------------------------------------------

    application_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    # -----------------------------------------------------
    # PERSONAL DETAILS
    # -----------------------------------------------------

    first_name = models.CharField(
        max_length=50,
    )

    last_name = models.CharField(
        max_length=50,
        blank=True,
    )

    date_of_birth = models.DateField()

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
    )

    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        blank=True,
    )

    # -----------------------------------------------------
    # CONTACT DETAILS
    # -----------------------------------------------------

    email = models.EmailField(
        blank=True,
    )

    phone = models.CharField(
        max_length=15,
    )

    alternate_phone = models.CharField(
        max_length=15,
        blank=True,
    )

    # -----------------------------------------------------
    # PROFESSIONAL DETAILS
    # -----------------------------------------------------

    designation = models.CharField(
        max_length=100,
    )

    staff_role = models.CharField(
        max_length=30,
        choices=STAFF_ROLE_CHOICES,
        null=True,
        blank=True,
    )

    department = models.CharField(
        max_length=100,
        blank=True,
    )

    joining_date = models.DateField()

    qualification = models.CharField(
        max_length=150,
    )

    specialization = models.CharField(
        max_length=150,
        blank=True,
    )

    experience_years = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0,
    )

    previous_organization = models.CharField(
        max_length=150,
        blank=True,
    )

    previous_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # ADDRESS DETAILS
    # -----------------------------------------------------

    address = models.TextField()

    city = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
    )

    pincode = models.CharField(
        max_length=10,
    )

    # -----------------------------------------------------
    # EMERGENCY CONTACT
    # -----------------------------------------------------

    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
    )

    emergency_contact_phone = models.CharField(
        max_length=15,
        blank=True,
    )

    emergency_contact_relation = models.CharField(
        max_length=50,
        blank=True,
    )

    # -----------------------------------------------------
    # EMPLOYEE DOCUMENTS
    # -----------------------------------------------------

    employee_photo = models.ImageField(
        upload_to="employee_applications/photos/",
        blank=True,
        null=True,
    )

    aadhaar_card = models.FileField(
        upload_to="employee_applications/aadhaar/",
        blank=True,
        null=True,
    )

    pan_card = models.FileField(
        upload_to="employee_applications/pan/",
        blank=True,
        null=True,
    )

    educational_certificate = models.FileField(
        upload_to="employee_applications/education/",
        blank=True,
        null=True,
    )

    experience_certificate = models.FileField(
        upload_to="employee_applications/experience/",
        blank=True,
        null=True,
    )

    resume = models.FileField(
        upload_to="employee_applications/resume/",
        blank=True,
        null=True,
    )

    joining_document = models.FileField(
        upload_to="employee_applications/joining/",
        blank=True,
        null=True,
    )
    bus_required = models.BooleanField(
    default=False,
    verbose_name="Bus Required",
    )
    bus_location = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name="Location",
    )

    bus_route = models.ForeignKey(
    "transport.BusRoute",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="employee_applications",
    verbose_name="Bus Route",
    )
    pickup_stop = models.ForeignKey(
    "transport.BusStop",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="employee_applications",
    verbose_name="Pickup Stop",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="submitted",
    )

    # -----------------------------------------------------
    # SUBMISSION INFORMATION
    # -----------------------------------------------------

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_employee_applications",
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # -----------------------------------------------------
    # STRING REPRESENTATION
    # -----------------------------------------------------

    def __str__(self):
        return (
            f"{self.application_id} - "
            f"{self.first_name} {self.last_name}"
        )

class EmployeeCredential(models.Model):
    employee_application = models.OneToOneField(
        EmployeeAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="credential",
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee_credential",
    )

    username = models.CharField(
        max_length=150,
        unique=True,
    )
    account_email = models.EmailField(
        blank=True,
    )

    temporary_password = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.username} - "
            f"{self.employee_application.application_id}"
        )

class ApplicationApproval(models.Model):

    APPLICATION_TYPE_CHOICES = (
        ("Student", "Student"),
        ("Employee", "Employee"),
    )

    STAGE_CHOICES = (
        ("system_admin", "System Administrator"),
        ("vice_principal", "Vice Principal"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )

    application_type = models.CharField(
        max_length=20,
        choices=APPLICATION_TYPE_CHOICES,
    )

    application_id = models.CharField(
        max_length=30,
    )

    stage = models.CharField(
        max_length=30,
        choices=STAGE_CHOICES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_approvals_reviewed",
    )

    review_comment = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.application_type} - "
            f"{self.application_id} - "
            f"{self.stage} - "
            f"{self.status}"
        )

class ParentStudent(models.Model):

    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="parent_students",
    )

    student = models.ForeignKey(
        StudentAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="parent_links",
    )

    relationship = models.CharField(
        max_length=50,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = (
            "parent",
            "student",
        )

    def __str__(self):
        return (
            f"{self.parent.username} - "
            f"{self.student.application_id}"
        )

class ParentMessage(models.Model):

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_parent_messages",
    )

    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_parent_messages",
    )

    student = models.ForeignKey(
        StudentAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="parent_messages",
    )

    subject = models.CharField(
        max_length=200,
        default="Message from Teacher",
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.teacher.username} → "
            f"{self.parent.username} → "
            f"{self.student.application_id}"
        )