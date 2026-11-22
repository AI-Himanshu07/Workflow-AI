
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.contrib.auth.models import User


# Private storage: documents are not served through public MEDIA_URL.
private_document_storage = FileSystemStorage(
    location=settings.BASE_DIR / 'private_uploads'
)


def validate_verification_document(file):
    allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
    extension = Path(file.name).suffix.lower().lstrip('.')

    if extension not in allowed_extensions:
        raise ValidationError(
            'Only PDF, JPG, JPEG and PNG files are allowed.'
        )

    if file.size > 5 * 1024 * 1024:
        raise ValidationError(
            'The verification document must be 5 MB or smaller.'
        )


# =========================================================
# USER PROFILE
# =========================================================

class UserProfile(models.Model):

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('company', 'Company'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return self.user.username


# =========================================================
# STUDENT PROFILE
# =========================================================

class StudentProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    college = models.CharField(max_length=150, blank=True)
    degree = models.CharField(max_length=100, blank=True)

    graduation_year = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    skills = models.TextField(blank=True)
    projects = models.TextField(blank=True)
    certifications = models.TextField(blank=True)

    def __str__(self):
        return self.user.username


# =========================================================
# COMPANY PROFILE
# =========================================================

class CompanyProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    company_name = models.CharField(max_length=150, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    recruiter_name = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.company_name or self.user.username


# =========================================================
# COMPANY ACCESS REQUEST
# =========================================================

class CompanyAccessRequest(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('more_info', 'More Information Required'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    company = models.OneToOneField(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name='access_request'
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True
    )

    recruiter_designation = models.CharField(
        max_length=100,
        blank=True
    )

    additional_information = models.TextField(blank=True)

    verification_document = models.FileField(
        upload_to='company_verification/',
        storage=private_document_storage,
        validators=[validate_verification_document],
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    admin_notes = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_company_requests'
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f'{self.company.company_name or self.company.user.username}'
            f' - {self.get_status_display()}'
        )


# =========================================================
# JOB
# =========================================================

class Job(models.Model):

    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('internship', 'Internship'),
        ('contract', 'Contract'),
    ]

    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name='jobs'
    )

    title = models.CharField(max_length=150)
    description = models.TextField()
    location = models.CharField(max_length=150)

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPE_CHOICES
    )

    salary = models.CharField(max_length=100, blank=True)
    required_degree = models.CharField(max_length=100, blank=True)

    minimum_cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    required_skills = models.TextField(blank=True)

    application_deadline = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# =========================================================
# APPLICATION
# =========================================================

class Application(models.Model):

    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('selected', 'Selected'),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='applied'
    )

    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.student.user.username + ' - ' + self.job.title


# =========================================================
# ASSESSMENT QUESTION
# =========================================================

class AssessmentQuestion(models.Model):

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='assessment_questions'
    )

    question = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)

    correct_answer = models.CharField(
        max_length=1,
        choices=[
            ('A', 'Option A'),
            ('B', 'Option B'),
            ('C', 'Option C'),
            ('D', 'Option D'),
        ]
    )

    skill = models.CharField(max_length=100, blank=True)
    marks = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question[:60]


# =========================================================
# ASSESSMENT ATTEMPT
# =========================================================

class AssessmentAttempt(models.Model):

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='assessment_attempts'
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='assessment_attempts'
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='assessment_attempts'
    )

    score = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    started_at = models.DateTimeField(auto_now_add=True)

    # Duration is stored per attempt.
    duration_minutes = models.PositiveSmallIntegerField(
        default=30
    )

    # Maximum allowed violations for this attempt.
    max_violations = models.PositiveSmallIntegerField(
        default=2
    )

    # Server-calculated assessment deadline.
    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Number of recorded security violations.
    violation_count = models.PositiveIntegerField(default=0)

    # A terminated attempt cannot accept further answers.
    terminated = models.BooleanField(default=False)

    termination_reason = models.CharField(
        max_length=100,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed = models.BooleanField(default=False)

    def __str__(self):
        return (
            self.student.user.username
            + ' - '
            + self.job.title
            + ' - Assessment'
        )


# =========================================================
# ASSESSMENT SECURITY VIOLATIONS
# =========================================================

class AssessmentViolation(models.Model):

    VIOLATION_TYPES = [
        ('tab_switch', 'Tab Switch'),
        ('window_blur', 'Window Focus Lost'),
    ]

    attempt = models.ForeignKey(
        AssessmentAttempt,
        on_delete=models.CASCADE,
        related_name='violations'
    )

    violation_type = models.CharField(
        max_length=20,
        choices=VIOLATION_TYPES
    )

    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['occurred_at', 'id']
        indexes = [
            models.Index(fields=['attempt', 'occurred_at']),
        ]

    def __str__(self):
        return (
            f'{self.attempt.student.user.username} - '
            f'{self.get_violation_type_display()}'
        )


# =========================================================
# ASSESSMENT ANSWER
# =========================================================

class AssessmentAnswer(models.Model):

    attempt = models.ForeignKey(
        AssessmentAttempt,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    question = models.ForeignKey(
        AssessmentQuestion,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    selected_answer = models.CharField(
        max_length=1,
        choices=[
            ('A', 'Option A'),
            ('B', 'Option B'),
            ('C', 'Option C'),
            ('D', 'Option D'),
        ],
        blank=True
    )

    is_correct = models.BooleanField(default=False)
    marks_obtained = models.PositiveIntegerField(default=0)

    def __str__(self):
        return (
            self.attempt.student.user.username
            + ' - '
            + str(self.question.id)
        )


# =========================================================
# NOTIFICATION SYSTEM
# =========================================================

class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ('application', 'Application Update'),
        ('status', 'Application Status'),
        ('interview', 'Interview Update'),
        ('system', 'System Notification'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system'
    )

    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.title}'


# =========================================================
# MESSAGING SYSTEM
# =========================================================

class Message(models.Model):

    MESSAGE_TYPES = [
        ('general', 'General Message'),
        ('announcement', 'Announcement'),
        ('interview', 'Interview Message'),
        ('system', 'System Message'),
    ]

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )

    subject = models.CharField(max_length=200)
    body = models.TextField()

    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='general'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['-created_at', '-id']),
        ]

    def __str__(self):
        return f'{self.subject} - {self.sender.username}'


# =========================================================
# MESSAGE RECIPIENTS
# =========================================================

class MessageRecipient(models.Model):

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='recipients'
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )

    is_read = models.BooleanField(default=False)

    read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-message__created_at', '-id']

        constraints = [
            models.UniqueConstraint(
                fields=['message', 'recipient'],
                name='unique_message_recipient'
            )
        ]

        indexes = [
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return (
            f'{self.message.subject} -> '
            f'{self.recipient.username}'
        )
