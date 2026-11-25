
from functools import wraps
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import (
    FileResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_POST

from accounts.models import (
    UserProfile,
    StudentProfile,
    CompanyProfile,
    CompanyAccessRequest,
    Job,
    Application,
    AssessmentQuestion,
    AssessmentAttempt,
    AssessmentAnswer,
    AssessmentViolation,
    Notification,
)


# =========================================================
# ASSESSMENT SECURITY SETTINGS
# =========================================================

ASSESSMENT_DURATION_MINUTES = 30
ASSESSMENT_MAX_VIOLATIONS = 2


def get_attempt_expiry(attempt):
    """
    Return the server-side expiry time for an assessment.

    Older attempts without an expiry timestamp receive one
    based on their original start time.
    """

    if not attempt.expires_at:
        attempt.expires_at = (
            attempt.started_at
            + timedelta(minutes=ASSESSMENT_DURATION_MINUTES)
        )
        attempt.save(update_fields=['expires_at'])

    return attempt.expires_at


def terminate_assessment(attempt, reason):
    """
    Terminate an assessment and prevent further submissions.
    """

    if attempt.completed:
        return

    attempt.terminated = True
    attempt.completed = True
    attempt.termination_reason = reason
    attempt.completed_at = timezone.now()

    attempt.save(
        update_fields=[
            'terminated',
            'completed',
            'termination_reason',
            'completed_at',
        ]
    )


def check_assessment_expiry(attempt):
    """
    Check expiry using server time.

    Returns True when the assessment has expired.
    """

    if attempt.completed:
        return True

    expiry_time = get_attempt_expiry(attempt)

    if timezone.now() >= expiry_time:
        terminate_assessment(
            attempt,
            'time_expired'
        )
        return True

    return False


def assessment_remaining_seconds(attempt):
    """
    Calculate remaining time using the server-side deadline.
    """

    if attempt.completed:
        return 0

    expiry_time = get_attempt_expiry(attempt)

    remaining = (
        expiry_time - timezone.now()
    ).total_seconds()

    return max(0, int(remaining))


# =========================================================
# PERMISSION HELPERS
# =========================================================

def has_role(user, role):
    return (
        user.is_authenticated
        and UserProfile.objects.filter(
            user=user,
            role=role
        ).exists()
    )


def student_required(view_func):

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not has_role(request.user, 'student'):
            return HttpResponseForbidden(
                'You do not have permission to access this page.'
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def company_access_required(view_func):

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not has_role(request.user, 'company'):
            return HttpResponseForbidden(
                'You do not have permission to access this page.'
            )

        company, created = CompanyProfile.objects.get_or_create(
            user=request.user
        )

        access_request = CompanyAccessRequest.objects.filter(
            company=company
        ).first()

        if not access_request or access_request.status != 'approved':
            return redirect('company_access_status')

        return view_func(request, *args, **kwargs)

    return wrapper


def staff_required(view_func):

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_staff:
            return HttpResponseForbidden(
                'Staff permission required.'
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_superuser:
            return HttpResponseForbidden(
                'Administrator permission required.'
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def notify_company(access_request, subject, message):

    recipient = (
        access_request.company.contact_email
        or access_request.company.user.email
    )

    if recipient:
        send_mail(
            subject,
            message,
            None,
            [recipient],
            fail_silently=False
        )


# =========================================================
# HOME
# =========================================================

def home(request):
    return render(request, 'core/home.html')


# =========================================================
# COMPANY ACCESS REQUEST - COMPANY
# =========================================================

@login_required
def company_access_request(request):

    if not has_role(request.user, 'company'):
        return HttpResponseForbidden(
            'Only registered company accounts can submit requests.'
        )

    company, created = CompanyProfile.objects.get_or_create(
        user=request.user
    )

    access_request = CompanyAccessRequest.objects.filter(
        company=company
    ).first()

    if access_request and access_request.status == 'approved':
        messages.success(
            request,
            'Your company has already been approved.'
        )
        return redirect('company_dashboard')

    if request.method == 'POST':

        company.company_name = request.POST.get(
            'company_name', ''
        ).strip()

        company.industry = request.POST.get(
            'industry', ''
        ).strip()

        company.location = request.POST.get(
            'location', ''
        ).strip()

        company.website = request.POST.get(
            'website', ''
        ).strip()

        company.description = request.POST.get(
            'description', ''
        ).strip()

        company.recruiter_name = request.POST.get(
            'recruiter_name', ''
        ).strip()

        company.contact_email = request.POST.get(
            'contact_email', ''
        ).strip()

        company.contact_phone = request.POST.get(
            'contact_phone', ''
        ).strip()

        registration_number = request.POST.get(
            'registration_number', ''
        ).strip()

        recruiter_designation = request.POST.get(
            'recruiter_designation', ''
        ).strip()

        additional_information = request.POST.get(
            'additional_information', ''
        ).strip()

        if not all([
            company.company_name,
            company.industry,
            company.location,
            company.recruiter_name,
            company.contact_email,
            company.contact_phone,
            registration_number,
            recruiter_designation
        ]):

            messages.error(
                request,
                'Please complete all required company and recruiter details.'
            )

        else:

            company.save()

            if not access_request:
                access_request = CompanyAccessRequest(
                    company=company
                )

            access_request.registration_number = registration_number
            access_request.recruiter_designation = recruiter_designation
            access_request.additional_information = additional_information

            uploaded_document = request.FILES.get(
                'verification_document'
            )

            if uploaded_document:
                access_request.verification_document = uploaded_document

            access_request.status = 'pending'
            access_request.admin_notes = ''
            access_request.reviewed_by = None
            access_request.reviewed_at = None

            try:
                access_request.full_clean()
                access_request.save()

                notify_company(
                    access_request,
                    'Workflow AI - Company Request Submitted',
                    (
                        'Your company access request has been submitted '
                        'successfully. Our team will review your details '
                        'and notify you about the result.'
                    )
                )

                messages.success(
                    request,
                    'Your company access request has been submitted.'
                )

                return redirect('company_access_status')

            except Exception as error:

                messages.error(
                    request,
                    f'Unable to submit your request: {error}'
                )

    return render(
        request,
        'core/company_access_request.html',
        {
            'company': company,
            'access_request': access_request,
        }
    )


# =========================================================
# COMPANY ACCESS STATUS
# =========================================================

@login_required
def company_access_status(request):

    if not has_role(request.user, 'company'):
        return HttpResponseForbidden(
            'Only company accounts can view this page.'
        )

    company, created = CompanyProfile.objects.get_or_create(
        user=request.user
    )

    access_request = CompanyAccessRequest.objects.filter(
        company=company
    ).first()

    return render(
        request,
        'core/company_access_status.html',
        {
            'company': company,
            'access_request': access_request,
        }
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@student_required
def student_dashboard(request):

    profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    applications = Application.objects.filter(
        student=profile
    ).select_related(
        'job',
        'job__company'
    ).order_by('-applied_at')

    return render(
        request,
        'core/student_dashboard.html',
        {
            'profile': profile,
            'applications': applications,
            'total_applications': applications.count(),
            'pending_applications': applications.filter(
                status='applied'
            ).count(),
            'shortlisted_applications': applications.filter(
                status='shortlisted'
            ).count(),
            'selected_applications': applications.filter(
                status='selected'
            ).count(),
            'rejected_applications': applications.filter(
                status='rejected'
            ).count(),
        }
    )


# =========================================================
# STUDENT JOBS
# =========================================================

@student_required
def student_jobs(request):

    jobs = Job.objects.select_related(
        'company'
    ).all().order_by('-created_at')

    return render(
        request,
        'core/student_jobs.html',
        {'jobs': jobs}
    )


# =========================================================
# STUDENT JOB DETAIL
# =========================================================

@student_required
def student_job_detail(request, job_id):

    job = get_object_or_404(Job, id=job_id)

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    application = Application.objects.filter(
        student=student_profile,
        job=job
    ).first()

    assessment_questions_count = AssessmentQuestion.objects.filter(
        job=job
    ).count()

    assessment_attempt = None

    if application:
        assessment_attempt = AssessmentAttempt.objects.filter(
            application=application
        ).order_by('-started_at').first()

    return render(
        request,
        'core/student_job_detail.html',
        {
            'job': job,
            'already_applied': application is not None,
            'application': application,
            'assessment_questions_count': assessment_questions_count,
            'assessment_attempt': assessment_attempt,
        }
    )



# =========================================================
# APPLY FOR JOB
# =========================================================

@student_required
def apply_job(request, job_id):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    job = get_object_or_404(Job, id=job_id)

    if request.method == 'POST':

        # Prevent applying again if an assessment was
        # previously started for this student and job.
        previous_attempt = AssessmentAttempt.objects.filter(
            student=student_profile,
            job=job
        ).exists()

        if previous_attempt:
            messages.error(
                request,
                'You have already started or submitted an assessment '
                'for this job. You cannot apply again or get another attempt.'
            )

            return redirect(
                'student_job_detail',
                job_id=job.id
            )

        application, application_created = Application.objects.get_or_create(
            student=student_profile,
            job=job
        )

        if application_created:

            Notification.objects.create(
                user=job.company.user,
                title='New Job Application',
                message=(
                    f'{request.user.username} has applied for '
                    f'your job "{job.title}".'
                ),
                notification_type='application'
            )

            messages.success(
                request,
                'Your application has been submitted successfully.'
            )

        else:

            messages.info(
                request,
                'You have already applied for this job.'
            )

    return redirect('student_job_detail', job_id=job.id)


# =========================================================
# MY APPLICATIONS
# =========================================================

@student_required
def my_applications(request):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    applications = Application.objects.filter(
        student=student_profile
    ).select_related(
        'job',
        'job__company'
    ).order_by('-applied_at')

    return render(
        request,
        'core/my_applications.html',
        {'applications': applications}
    )


# =========================================================
# WITHDRAW APPLICATION
# =========================================================

@student_required
def withdraw_application(request, application_id):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    application = get_object_or_404(
        Application,
        id=application_id,
        student=student_profile
    )

    # Check all attempts for this student and job,
    # not just attempts linked to the current application.
    assessment_started = AssessmentAttempt.objects.filter(
        student=student_profile,
        job=application.job
    ).exists()

    if assessment_started:

        messages.error(
            request,
            'You cannot withdraw this application because you have '
            'already started an assessment. Your application is locked.'
        )

        return redirect('my_applications')

    if request.method == 'POST':

        application.delete()

        messages.success(
            request,
            'Your application has been withdrawn successfully.'
        )

        return redirect('my_applications')

    return render(
        request,
        'core/delete_application.html',
        {'application': application}
    )



# =========================================================
# START ASSESSMENT
# =========================================================

@student_required
def start_assessment(request, application_id):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    with transaction.atomic():

        application = get_object_or_404(
            Application.objects.select_for_update(),
            id=application_id,
            student=student_profile
        )

        questions = AssessmentQuestion.objects.filter(
            job=application.job
        ).order_by('id')

        if not questions.exists():
            return render(
                request,
                'core/assessment_not_available.html',
                {
                    'application': application,
                    'job': application.job
                }
            )

        attempt = AssessmentAttempt.objects.filter(
            application=application
        ).order_by('-started_at').first()

        if attempt:

            attempt = AssessmentAttempt.objects.select_for_update().get(
                id=attempt.id
            )

            if attempt.completed or attempt.terminated:
                return redirect(
                    'assessment_result',
                    attempt_id=attempt.id
                )

            if check_assessment_expiry(attempt):
                return redirect(
                    'assessment_result',
                    attempt_id=attempt.id
                )

        else:

            total_marks = sum(
                question.marks for question in questions
            )

            attempt = AssessmentAttempt.objects.create(
                student=student_profile,
                job=application.job,
                application=application,
                total_marks=total_marks,
                expires_at=(
                    timezone.now()
                    + timedelta(minutes=ASSESSMENT_DURATION_MINUTES)
                )
            )

    return render(
        request,
        'core/assessment.html',
        {
            'application': application,
            'job': application.job,
            'questions': questions,
            'attempt': attempt,
            'remaining_seconds': assessment_remaining_seconds(attempt),
            'max_violations': ASSESSMENT_MAX_VIOLATIONS,
        }
    )


# =========================================================
# RECORD ASSESSMENT SECURITY VIOLATION
# =========================================================

@student_required
@require_POST
def record_assessment_violation(request, attempt_id):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    violation_type = request.POST.get(
        'violation_type',
        ''
    ).strip()

    allowed_types = [
        'tab_switch',
        'window_blur',
    ]

    if violation_type not in allowed_types:
        return JsonResponse(
            {
                'success': False,
                'message': 'Invalid violation type.'
            },
            status=400
        )

    with transaction.atomic():

        attempt = get_object_or_404(
            AssessmentAttempt.objects.select_for_update(),
            id=attempt_id,
            student=student_profile
        )

        if attempt.completed or attempt.terminated:
            return JsonResponse(
                {
                    'success': False,
                    'terminated': True,
                    'violation_count': attempt.violation_count,
                    'message': 'This assessment is already closed.',
                    'redirect_url': redirect(
                        'assessment_result',
                        attempt_id=attempt.id
                    ).url,
                },
                status=409
            )

        if check_assessment_expiry(attempt):
            return JsonResponse(
                {
                    'success': False,
                    'terminated': True,
                    'violation_count': attempt.violation_count,
                    'message': 'Your assessment time has expired.',
                    'redirect_url': redirect(
                        'assessment_result',
                        attempt_id=attempt.id
                    ).url,
                },
                status=403
            )

        AssessmentViolation.objects.create(
            attempt=attempt,
            violation_type=violation_type
        )

        attempt.violation_count = attempt.violations.count()

        if attempt.violation_count >= ASSESSMENT_MAX_VIOLATIONS:

            terminate_assessment(
                attempt,
                'maximum_violations'
            )

            return JsonResponse(
                {
                    'success': True,
                    'terminated': True,
                    'violation_count': attempt.violation_count,
                    'max_violations': ASSESSMENT_MAX_VIOLATIONS,
                    'message': (
                        'Your assessment has been automatically '
                        'terminated because you reached the maximum '
                        'number of security violations.'
                    ),
                    'redirect_url': redirect(
                        'assessment_result',
                        attempt_id=attempt.id
                    ).url,
                }
            )

        attempt.save(
            update_fields=['violation_count']
        )

        return JsonResponse(
            {
                'success': True,
                'terminated': False,
                'violation_count': attempt.violation_count,
                'max_violations': ASSESSMENT_MAX_VIOLATIONS,
                'remaining_violations': (
                    ASSESSMENT_MAX_VIOLATIONS
                    - attempt.violation_count
                ),
                'message': (
                    f'Security warning: violation '
                    f'{attempt.violation_count} of '
                    f'{ASSESSMENT_MAX_VIOLATIONS}.'
                ),
            }
        )


# =========================================================
# SUBMIT ASSESSMENT
# =========================================================

@student_required
@require_POST
def submit_assessment(request, application_id):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    with transaction.atomic():

        application = get_object_or_404(
            Application.objects.select_for_update(),
            id=application_id,
            student=student_profile
        )

        attempt = AssessmentAttempt.objects.filter(
            application=application
        ).order_by('-started_at').first()

        if not attempt:
            return redirect(
                'start_assessment',
                application_id=application.id
            )

        attempt = AssessmentAttempt.objects.select_for_update().get(
            id=attempt.id
        )

        if attempt.completed or attempt.terminated:
            return redirect(
                'assessment_result',
                attempt_id=attempt.id
            )

        if check_assessment_expiry(attempt):
            return redirect(
                'assessment_result',
                attempt_id=attempt.id
            )

        questions = list(
            AssessmentQuestion.objects.filter(
                job=application.job
            ).order_by('id')
        )

        if not questions:
            return redirect(
                'student_job_detail',
                job_id=application.job.id
            )

        AssessmentAnswer.objects.filter(
            attempt=attempt
        ).delete()

        score = 0
        total_marks = 0

        for question in questions:

            total_marks += question.marks

            selected_answer = request.POST.get(
                f'question_{question.id}',
                ''
            )

            if selected_answer not in ['A', 'B', 'C', 'D']:
                selected_answer = ''

            is_correct = (
                selected_answer != ''
                and selected_answer == question.correct_answer
            )

            marks_obtained = (
                question.marks if is_correct else 0
            )

            if is_correct:
                score += question.marks

            AssessmentAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_answer=selected_answer,
                is_correct=is_correct,
                marks_obtained=marks_obtained
            )

        percentage = (
            (score / total_marks) * 100
            if total_marks > 0
            else 0
        )

        attempt.score = score
        attempt.total_marks = total_marks
        attempt.percentage = round(percentage, 2)
        attempt.completed = True
        attempt.completed_at = timezone.now()

        attempt.save(
            update_fields=[
                'score',
                'total_marks',
                'percentage',
                'completed',
                'completed_at',
            ]
        )

    return redirect(
        'assessment_result',
        attempt_id=attempt.id
    )


# =========================================================
# STUDENT ASSESSMENT RESULT
# =========================================================

@student_required
def assessment_result(request, attempt_id):

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    attempt = get_object_or_404(
        AssessmentAttempt,
        id=attempt_id,
        student=student_profile
    )

    answers = attempt.answers.select_related(
        'question'
    ).all()

    violations = attempt.violations.all()

    return render(
        request,
        'core/assessment_result.html',
        {
            'attempt': attempt,
            'answers': answers,
            'violations': violations,
        }
    )


# =========================================================
# COMPANY ASSESSMENT QUESTION MANAGEMENT
# =========================================================

@company_access_required
def manage_assessment_questions(request, job_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    job = get_object_or_404(
        Job,
        id=job_id,
        company=company_profile
    )

    questions = AssessmentQuestion.objects.filter(
        job=job
    ).order_by('id')

    return render(
        request,
        'core/manage_assessment_questions.html',
        {
            'job': job,
            'questions': questions,
            'total_questions': questions.count(),
            'total_marks': sum(q.marks for q in questions),
        }
    )



@company_access_required
def add_assessment_question(request, job_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    job = get_object_or_404(
        Job,
        id=job_id,
        company=company_profile
    )

    if request.method == 'POST':

        try:
            total_questions = int(
                request.POST.get('total_questions', 0)
            )
        except (TypeError, ValueError):
            total_questions = 0

        if total_questions < 1 or total_questions > 100:
            return render(
                request,
                'core/add_assessment_question.html',
                {
                    'job': job,
                    'error': 'Please add between 1 and 100 questions.'
                }
            )

        questions_to_create = []
        errors = []

        for index in range(total_questions):

            question = request.POST.get(
                f'question_{index}', ''
            ).strip()

            option_a = request.POST.get(
                f'option_a_{index}', ''
            ).strip()

            option_b = request.POST.get(
                f'option_b_{index}', ''
            ).strip()

            option_c = request.POST.get(
                f'option_c_{index}', ''
            ).strip()

            option_d = request.POST.get(
                f'option_d_{index}', ''
            ).strip()

            correct_answer = request.POST.get(
                f'correct_answer_{index}', ''
            ).strip()

            skill = request.POST.get(
                f'skill_{index}', ''
            ).strip()

            try:
                marks = int(
                    request.POST.get(f'marks_{index}', 1)
                )
            except (TypeError, ValueError):
                marks = 0

            if (
                not question
                or not option_a
                or not option_b
                or not option_c
                or not option_d
                or correct_answer not in ['A', 'B', 'C', 'D']
                or marks <= 0
            ):
                errors.append(
                    f'Please complete all required fields '
                    f'for Question {index + 1}.'
                )
                continue

            questions_to_create.append(
                AssessmentQuestion(
                    job=job,
                    question=question,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_answer=correct_answer,
                    skill=skill,
                    marks=marks
                )
            )

        if errors:
            return render(
                request,
                'core/add_assessment_question.html',
                {
                    'job': job,
                    'error': ' '.join(errors)
                }
            )

        try:
            with transaction.atomic():
                AssessmentQuestion.objects.bulk_create(
                    questions_to_create
                )

            messages.success(
                request,
                f'{len(questions_to_create)} assessment '
                f'questions added successfully.'
            )

            return redirect(
                'manage_assessment_questions',
                job_id=job.id
            )

        except Exception:
            messages.error(
                request,
                'Unable to save questions. Please try again.'
            )

    return render(
        request,
        'core/add_assessment_question.html',
        {'job': job}
    )

@company_access_required
def delete_assessment_question(request, question_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    question = get_object_or_404(
        AssessmentQuestion,
        id=question_id,
        job__company=company_profile
    )

    job_id = question.job.id

    if request.method == 'POST':
        question.delete()

        messages.success(request, 'Question deleted.')

        return redirect(
            'manage_assessment_questions',
            job_id=job_id
        )

    return render(
        request,
        'core/delete_assessment_question.html',
        {'question': question}
    )


# =========================================================
# COMPANY ASSESSMENT RESULT
# =========================================================

@company_access_required
def company_assessment_result(request, attempt_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related(
            'application',
            'application__student',
            'application__job'
        ),
        id=attempt_id,
        application__job__company=company_profile
    )

    answers = attempt.answers.select_related(
        'question'
    ).all()

    violations = attempt.violations.all()

    return render(
        request,
        'core/company_assessment_result.html',
        {
            'application': attempt.application,
            'attempt': attempt,
            'answers': answers,
            'violations': violations,
        }
    )


# =========================================================
# COMPANY DASHBOARD
# =========================================================

@company_access_required
def company_dashboard(request):

    profile = CompanyProfile.objects.get(
        user=request.user
    )

    return render(
        request,
        'core/company_dashboard.html',
        {'profile': profile}
    )


# =========================================================
# CREATE JOB
# =========================================================

@company_access_required
def create_job(request):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    if request.method == 'POST':

        Job.objects.create(
            company=company_profile,
            title=request.POST['title'],
            description=request.POST['description'],
            location=request.POST['location'],
            job_type=request.POST['job_type'],
            salary=request.POST.get('salary', ''),
            required_degree=request.POST.get('required_degree', ''),
            minimum_cgpa=request.POST.get('minimum_cgpa') or None,
            required_skills=request.POST.get('required_skills', ''),
            application_deadline=request.POST.get(
                'application_deadline'
            ) or None
        )

        messages.success(request, 'Job created successfully.')

        return redirect('company_dashboard')

    return render(request, 'core/create_job.html')


# =========================================================
# COMPANY JOBS
# =========================================================

@company_access_required
def company_jobs(request):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    jobs = Job.objects.filter(
        company=company_profile
    ).order_by('-created_at')

    return render(
        request,
        'core/company_jobs.html',
        {'jobs': jobs}
    )


# =========================================================
# COMPANY JOB DETAIL
# =========================================================

@company_access_required
def job_detail(request, job_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    job = get_object_or_404(
        Job,
        id=job_id,
        company=company_profile
    )

    return render(
        request,
        'core/job_detail.html',
        {'job': job}
    )


# =========================================================
# EDIT JOB
# =========================================================

@company_access_required
def edit_job(request, job_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    job = get_object_or_404(
        Job,
        id=job_id,
        company=company_profile
    )

    if request.method == 'POST':

        job.title = request.POST['title']
        job.description = request.POST['description']
        job.location = request.POST['location']
        job.job_type = request.POST['job_type']
        job.salary = request.POST.get('salary', '')
        job.required_degree = request.POST.get(
            'required_degree', ''
        )
        job.minimum_cgpa = request.POST.get(
            'minimum_cgpa'
        ) or None
        job.required_skills = request.POST.get(
            'required_skills', ''
        )
        job.application_deadline = request.POST.get(
            'application_deadline'
        ) or None

        job.save()

        messages.success(request, 'Job updated successfully.')

        return redirect('job_detail', job_id=job.id)

    return render(
        request,
        'core/edit_job.html',
        {'job': job}
    )


# =========================================================
# DELETE JOB
# =========================================================

@company_access_required
def delete_job(request, job_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    job = get_object_or_404(
        Job,
        id=job_id,
        company=company_profile
    )

    if request.method == 'POST':
        job.delete()

        messages.success(request, 'Job deleted.')

        return redirect('company_jobs')

    return render(
        request,
        'core/delete_job.html',
        {'job': job}
    )


# =========================================================
# COMPANY APPLICANTS
# =========================================================

@company_access_required
def company_applicants(request, job_id=None):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    applications = Application.objects.filter(
        job__company=company_profile
    ).select_related(
        'student',
        'student__user',
        'job'
    )

    if job_id is not None:
        applications = applications.filter(
            job_id=job_id
        )

    applications = applications.order_by('-applied_at')

    return render(
        request,
        'core/company_applicants.html',
        {'applications': applications}
    )


# =========================================================
# APPLICANT PROFILE
# =========================================================

@company_access_required
def applicant_profile(request, application_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    application = get_object_or_404(
        Application,
        id=application_id,
        job__company=company_profile
    )

    student = application.student

    assessment_attempt = AssessmentAttempt.objects.filter(
        application=application,
        completed=True
    ).order_by('-completed_at').first()

    return render(
        request,
        'core/applicant_profile.html',
        {
            'application': application,
            'student': student,
            'assessment_attempt': assessment_attempt
        }
    )


# =========================================================
# APPLICANT RANKING
# =========================================================

@company_access_required
def applicant_ranking(request, job_id=None):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    jobs = Job.objects.filter(
        company=company_profile
    ).order_by('-created_at')

    if job_id is None:

        job_data = []

        for job in jobs:

            applications = Application.objects.filter(job=job)

            total_applicants = applications.count()

            completed_count = AssessmentAttempt.objects.filter(
                application__job=job,
                completed=True,
                terminated=False
            ).values('application').distinct().count()

            job_data.append({
                'job': job,
                'total_applicants': total_applicants,
                'completed_count': completed_count,
            })

        return render(
            request,
            'core/company_ranking_jobs.html',
            {
                'job_data': job_data,
            }
        )

    job = get_object_or_404(
        Job,
        id=job_id,
        company=company_profile
    )

    applications = list(
        Application.objects.filter(
            job=job
        ).select_related(
            'student',
            'student__user',
            'job'
        ).order_by('-applied_at')
    )

    for application in applications:

        application.assessment_attempt = (
            AssessmentAttempt.objects.filter(
                application=application,
                completed=True,
                terminated=False
            ).order_by('-completed_at').first()
        )

        if application.assessment_attempt:

            application.assessment_score = float(
                application.assessment_attempt.percentage or 0
            )

            application.has_completed_assessment = True

        else:

            application.assessment_score = None
            application.has_completed_assessment = False

    ranked_applications = [
        application for application in applications
        if application.has_completed_assessment
    ]

    ranked_applications.sort(
        key=lambda item: (
            item.assessment_score or 0,
            float(item.student.cgpa or 0),
            item.applied_at
        ),
        reverse=True
    )

    return render(
        request,
        'core/applicant_ranking.html',
        {
            'job': job,
            'ranked_applications': ranked_applications,
            'total_applicants': len(applications),
            'completed_count': len(ranked_applications),
        }
    )


# =========================================================
# HIRING WORKFLOW
# =========================================================

@company_access_required
def hiring_workflow(request, job_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    job = get_object_or_404(
        Job,
        id=job_id,
        company=company_profile
    )

    applications = Application.objects.filter(
        job=job
    ).select_related(
        'student',
        'student__user',
        'job'
    ).order_by('-applied_at')

    applied_applications = applications.filter(
        status='applied'
    )

    shortlisted_applications = applications.filter(
        status='shortlisted'
    )

    selected_applications = applications.filter(
        status='selected'
    )

    rejected_applications = applications.filter(
        status='rejected'
    )

    context = {
        'job': job,
        'applications': applications,
        'applied_applications': applied_applications,
        'shortlisted_applications': shortlisted_applications,
        'selected_applications': selected_applications,
        'rejected_applications': rejected_applications,
        'total_applications': applications.count(),
        'total_applied': applied_applications.count(),
        'total_shortlisted': shortlisted_applications.count(),
        'total_selected': selected_applications.count(),
        'total_rejected': rejected_applications.count(),
    }

    return render(
        request,
        'core/hiring_workflow.html',
        context
    )


@company_access_required
def hiring_workflow_jobs(request):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    jobs = Job.objects.filter(
        company=company_profile
    ).order_by('-created_at')

    return render(
        request,
        'core/hiring_workflow_jobs.html',
        {
            'jobs': jobs,
        }
    )


# =========================================================
# MANAGE APPLICANT
# =========================================================

@company_access_required
def manage_applicant(request, application_id):

    company_profile = CompanyProfile.objects.get(
        user=request.user
    )

    application = get_object_or_404(
        Application,
        id=application_id,
        job__company=company_profile
    )

    if request.method == 'POST':

        new_status = request.POST.get('status')

        allowed_statuses = [
            'applied',
            'shortlisted',
            'selected',
            'rejected'
        ]

        old_status = application.status

        if new_status in allowed_statuses and new_status != old_status:

            application.status = new_status
            application.save(update_fields=['status'])

            Notification.objects.create(
                user=application.student.user,
                title='Application Status Updated',
                message=(
                    f'Your application for "{application.job.title}" '
                    f'has been updated to '
                    f'{application.get_status_display()}.'
                ),
                notification_type='status'
            )

            messages.success(
                request,
                'Application status updated and student notified.'
            )

    return redirect(
        'hiring_workflow',
        job_id=application.job.id
    )


# =========================================================
# ADMIN / STAFF DASHBOARD
# =========================================================

@staff_required
def admin_dashboard(request):

    return render(
        request,
        'core/admin_dashboard.html',
        {
            'is_admin': request.user.is_superuser,
            'is_staff_member': not request.user.is_superuser,
        }
    )


# =========================================================
# ADMIN / STAFF APPLICATIONS
# =========================================================

@staff_required
def admin_applications(request):

    applications = Application.objects.select_related(
        'student',
        'student__user',
        'job',
        'job__company'
    ).order_by('-applied_at')

    return render(
        request,
        'core/admin_applications.html',
        {'applications': applications}
    )



# =========================================================
# ADMIN ONLY - DELETE APPLICATION
# =========================================================

@admin_required
def admin_delete_application(request, application_id):

    application = get_object_or_404(
        Application,
        id=application_id
    )

    # Check whether this application has an assessment attempt.
    assessment_exists = AssessmentAttempt.objects.filter(
        application=application
    ).exists()

    if request.method == 'POST':

        # Never delete an application with assessment history.
        if assessment_exists:

            messages.error(
                request,
                'This application cannot be deleted because an '
                'assessment attempt is linked to it. Assessment '
                'history must be preserved.'
            )

            return redirect('admin_applications')

        application.delete()

        messages.success(
            request,
            'Application deleted successfully.'
        )

        return redirect('admin_applications')

    return render(
        request,
        'core/admin_delete_application.html',
        {
            'application': application,
            'assessment_exists': assessment_exists,
        }
    )



# =========================================================
# ADMIN ONLY - WITHDRAW APPLICATION
# =========================================================

@admin_required
def admin_withdraw_application(request, application_id):

    if request.method != 'POST':
        messages.error(
            request,
            'Invalid request. Please use the withdraw button.'
        )
        return redirect('admin_applications')

    application = get_object_or_404(
        Application,
        id=application_id
    )

    if application.status == 'withdrawn':

        messages.info(
            request,
            'This application is already withdrawn.'
        )

        return redirect('admin_applications')

    # Change status only.
    # Never delete the application or assessment history.
    application.status = 'withdrawn'
    application.save(update_fields=['status'])

    # Notify the student.
    Notification.objects.create(
        user=application.student.user,
        title='Application Withdrawn',
        message=(
            f'Your application for {application.job.title} '
            'has been withdrawn by the platform administrator.'
        ),
        notification_type='status'
    )

    messages.success(
        request,
        'Application withdrawn successfully. Assessment history has been preserved.'
    )

    return redirect('admin_applications')


# =========================================================
# ADMIN / STAFF - COMPANY REQUEST LIST
# =========================================================

@staff_required
def admin_company_requests(request):

    requests = CompanyAccessRequest.objects.select_related(
        'company',
        'company__user',
        'reviewed_by'
    ).order_by('-created_at')

    return render(
        request,
        'core/admin_company_requests.html',
        {
            'requests': requests,
            'is_admin': request.user.is_superuser,
        }
    )


# =========================================================
# ADMIN / STAFF - COMPANY REQUEST DETAILS
# =========================================================

@staff_required
def admin_company_request_detail(request, request_id):

    access_request = get_object_or_404(
        CompanyAccessRequest.objects.select_related(
            'company',
            'company__user',
            'reviewed_by'
        ),
        id=request_id
    )

    return render(
        request,
        'core/admin_company_request_detail.html',
        {
            'access_request': access_request,
            'is_admin': request.user.is_superuser,
        }
    )


# =========================================================
# REVIEW COMPANY REQUEST
# =========================================================

@staff_required
@require_POST
def review_company_access_request(request, request_id):

    access_request = get_object_or_404(
        CompanyAccessRequest,
        id=request_id
    )

    new_status = request.POST.get('status')

    admin_notes = request.POST.get(
        'admin_notes', ''
    ).strip()

    staff_allowed_statuses = [
        'under_review',
        'more_info'
    ]

    admin_allowed_statuses = [
        'under_review',
        'more_info',
        'approved',
        'rejected'
    ]

    if request.user.is_superuser:
        allowed_statuses = admin_allowed_statuses
    else:
        allowed_statuses = staff_allowed_statuses

    if new_status not in allowed_statuses:
        return HttpResponseForbidden(
            'You are not authorized to perform this action.'
        )

    access_request.status = new_status
    access_request.admin_notes = admin_notes
    access_request.reviewed_by = request.user
    access_request.reviewed_at = timezone.now()
    access_request.save()

    status_label = access_request.get_status_display()

    email_message = (
        f"Hello {access_request.company.recruiter_name or 'Recruiter'},\n\n"
        f"Your company access request has been updated.\n\n"
        f"Company: {access_request.company.company_name}\n"
        f"Status: {status_label}\n\n"
        f"Review message: {admin_notes or 'No additional message.'}\n\n"
        f"Regards,\nWorkflow AI Team"
    )

    notify_company(
        access_request,
        f'Workflow AI - Company Request {status_label}',
        email_message
    )

    messages.success(
        request,
        f'Company request updated to {status_label}.'
    )

    return redirect(
        'admin_company_request_detail',
        request_id=access_request.id
    )


# =========================================================
# PROTECTED COMPANY VERIFICATION DOCUMENT
# =========================================================

@staff_required
def company_verification_document(request, request_id):

    access_request = get_object_or_404(
        CompanyAccessRequest,
        id=request_id
    )

    if not access_request.verification_document:
        messages.error(request, 'No document was uploaded.')
        return redirect(
            'admin_company_request_detail',
            request_id=access_request.id
        )

    document = access_request.verification_document

    try:
        response = FileResponse(
            document.open('rb'),
            as_attachment=True,
            filename=document.name.split('/')[-1]
        )
        return response

    except (OSError, ValueError):
        messages.error(request, 'Unable to open this document.')

        return redirect(
            'admin_company_request_detail',
            request_id=access_request.id
        )


# =========================================================
# ADMIN ONLY - MANAGE STUDENTS
# =========================================================

@staff_required
def admin_students(request):

    student_profiles = UserProfile.objects.filter(
        role='student'
    ).select_related(
        'user'
    ).order_by('-user__date_joined')

    search = request.GET.get('search', '').strip()

    if search:
        student_profiles = student_profiles.filter(
            Q(user__username__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__studentprofile__full_name__icontains=search)
            | Q(user__studentprofile__college__icontains=search)
        ).distinct()

    students = []

    for user_profile in student_profiles:
        user = user_profile.user

        student = StudentProfile.objects.filter(
            user=user
        ).first()

        students.append({
            'user': user,
            'profile': student,
        })

    all_students = UserProfile.objects.filter(
        role='student'
    ).select_related('user')

    return render(
        request,
        'core/admin_students.html',
        {
            'students': students,
            'search': search,
            'total_students': all_students.count(),
            'active_students': all_students.filter(
                user__is_active=True
            ).count(),
            'inactive_students': all_students.filter(
                user__is_active=False
            ).count(),
        }
    )


# =========================================================
# ADMIN ONLY - ACTIVATE / DEACTIVATE STUDENT
# =========================================================

@staff_required
@require_POST
def admin_toggle_student(request, user_id):

    student = get_object_or_404(
        User.objects.filter(
            userprofile__role='student'
        ),
        id=user_id
    )

    student.is_active = not student.is_active
    student.save(update_fields=['is_active'])

    if student.is_active:
        messages.success(
            request,
            f'{student.username} has been activated.'
        )
    else:
        messages.success(
            request,
            f'{student.username} has been deactivated.'
        )

    return redirect('admin_students')


# =========================================================
# ADMIN ONLY - DELETE STUDENT
# =========================================================

@staff_required
@require_POST
def admin_delete_student(request, user_id):

    student = get_object_or_404(
        User.objects.filter(
            userprofile__role='student'
        ),
        id=user_id
    )

    username = student.username
    student.delete()

    messages.success(
        request,
        f'Student account "{username}" has been deleted.'
    )

    return redirect('admin_students')


# =========================================================
# ADMIN ONLY - MANAGE COMPANIES
# =========================================================

@staff_required
def admin_companies(request):

    company_profiles = CompanyProfile.objects.filter(
        user__userprofile__role='company'
    ).select_related(
        'user'
    ).order_by('-user__date_joined')

    search = request.GET.get('search', '').strip()

    if search:
        company_profiles = company_profiles.filter(
            Q(company_name__icontains=search)
            | Q(industry__icontains=search)
            | Q(location__icontains=search)
            | Q(contact_email__icontains=search)
            | Q(recruiter_name__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
        ).distinct()

    companies = []

    for company in company_profiles:

        access_request = CompanyAccessRequest.objects.filter(
            company=company
        ).first()

        companies.append({
            'company': company,
            'user': company.user,
            'access_request': access_request,
        })

    all_companies = CompanyProfile.objects.filter(
        user__userprofile__role='company'
    ).select_related('user')

    approved_count = CompanyAccessRequest.objects.filter(
        company__user__userprofile__role='company',
        status='approved'
    ).count()

    pending_count = CompanyAccessRequest.objects.filter(
        company__user__userprofile__role='company',
        status__in=['pending', 'under_review', 'more_info']
    ).count()

    return render(
        request,
        'core/admin_companies.html',
        {
            'companies': companies,
            'search': search,
            'total_companies': all_companies.count(),
            'active_companies': all_companies.filter(
                user__is_active=True
            ).count(),
            'inactive_companies': all_companies.filter(
                user__is_active=False
            ).count(),
            'approved_count': approved_count,
            'pending_count': pending_count,
        }
    )


# =========================================================
# ADMIN ONLY - ACTIVATE / DEACTIVATE COMPANY
# =========================================================

@staff_required
@require_POST
def admin_toggle_company(request, user_id):

    company_user = get_object_or_404(
        User.objects.filter(
            userprofile__role='company'
        ),
        id=user_id
    )

    company_user.is_active = not company_user.is_active

    company_user.save(
        update_fields=['is_active']
    )

    if company_user.is_active:

        messages.success(
            request,
            f'Company account "{company_user.username}" activated.'
        )

    else:

        messages.success(
            request,
            f'Company account "{company_user.username}" deactivated.'
        )

    return redirect('admin_companies')


# =========================================================
# ADMIN ONLY - DELETE COMPANY
# =========================================================

@staff_required
@require_POST
def admin_delete_company(request, user_id):

    company_user = get_object_or_404(
        User.objects.filter(
            userprofile__role='company'
        ),
        id=user_id
    )

    username = company_user.username
    company_user.delete()

    messages.success(
        request,
        f'Company account "{username}" has been deleted.'
    )

    return redirect('admin_companies')


# =========================================================
# STAFF DASHBOARD
# =========================================================

@staff_required
def staff_dashboard(request):

    total_students = UserProfile.objects.filter(
        role='student'
    ).count()

    total_companies = UserProfile.objects.filter(
        role='company'
    ).count()

    pending_requests = CompanyAccessRequest.objects.filter(
        status__in=['pending', 'under_review', 'more_info']
    ).count()

    total_jobs = Job.objects.count()
    total_applications = Application.objects.count()

    context = {
        'total_students': total_students,
        'total_companies': total_companies,
        'pending_requests': pending_requests,
        'total_jobs': total_jobs,
        'total_applications': total_applications,
        'is_admin': request.user.is_superuser,
        'is_staff_member': not request.user.is_superuser,
    }

    return render(
        request,
        'core/staff_dashboard.html',
        context
    )


# =========================================================
# ADMIN - MANAGE STAFF
# =========================================================

@admin_required
def admin_staff(request):

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not username or not email or not password:
            messages.error(request, 'Please fill in all fields.')

        elif User.objects.filter(username=username).exists():
            messages.error(request, 'This username already exists.')

        elif len(password) < 8:
            messages.error(request, 'Password must contain at least 8 characters.')

        else:
            staff_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True
            )

            messages.success(
                request,
                f'Staff account {staff_user.username} created successfully.'
            )

            return redirect('admin_staff')

    staff_members = User.objects.filter(
        is_staff=True,
        is_superuser=False
    ).order_by('-date_joined')

    return render(
        request,
        'core/admin_staff.html',
        {'staff_members': staff_members}
    )


# =========================================================
# ADMIN - ACTIVATE / DEACTIVATE STAFF
# =========================================================

@admin_required
@require_POST
def admin_toggle_staff(request, user_id):

    staff_user = get_object_or_404(
        User.objects.filter(
            is_staff=True,
            is_superuser=False
        ),
        id=user_id
    )

    staff_user.is_active = not staff_user.is_active
    staff_user.save(update_fields=['is_active'])

    messages.success(
        request,
        f'Staff account {staff_user.username} updated successfully.'
    )

    return redirect('admin_staff')


# =========================================================
# ADMIN - DELETE STAFF
# =========================================================

@admin_required
@require_POST
def admin_delete_staff(request, user_id):

    staff_user = get_object_or_404(
        User.objects.filter(
            is_staff=True,
            is_superuser=False
        ),
        id=user_id
    )

    username = staff_user.username
    staff_user.delete()

    messages.success(
        request,
        f'Staff account {username} deleted successfully.'
    )

    return redirect('admin_staff')
