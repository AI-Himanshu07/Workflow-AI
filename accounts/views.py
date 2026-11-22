
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email

from .models import (
    UserProfile,
    StudentProfile,
    CompanyProfile,
    Notification,
    Message,
    MessageRecipient,
    Application,
)


# =========================================================
# REGISTER
# =========================================================

def register(request):

    if request.method == 'POST':

        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        UserProfile.objects.create(
            user=user,
            role=role
        )

        return redirect('/accounts/login/')

    return render(request, 'accounts/register.html')


# =========================================================
# LOGIN
# =========================================================

def login_view(request):

    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            if user.is_superuser:
                return redirect('admin_dashboard')

            elif user.is_staff:
                return redirect('staff_dashboard')

            try:
                profile = UserProfile.objects.get(user=user)

                if profile.role == 'student':
                    return redirect('/student/dashboard/')

                elif profile.role == 'company':
                    return redirect('/company/dashboard/')

            except UserProfile.DoesNotExist:
                logout(request)

        return render(
            request,
            'accounts/login.html',
            {'error': 'Invalid username or password.'}
        )

    return render(request, 'accounts/login.html')


# =========================================================
# STUDENT PROFILE - EDIT
# =========================================================

@login_required
def student_profile(request):

    profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    email_error = None

    if request.method == 'POST':

        new_email = request.POST.get('email', '').strip().lower()

        try:
            validate_email(new_email)

        except ValidationError:
            email_error = 'Please enter a valid email address.'

        if not email_error:

            if User.objects.filter(
                email__iexact=new_email
            ).exclude(
                id=request.user.id
            ).exists():

                email_error = (
                    'This email address is already registered '
                    'with another account.'
                )

        if email_error:

            return render(
                request,
                'accounts/student_profile.html',
                {
                    'profile': profile,
                    'email_error': email_error,
                    'email_value': new_email,
                }
            )

        # Update registered account email
        request.user.email = new_email

        request.user.save(
            update_fields=['email']
        )

        # Update student information
        profile.full_name = request.POST.get(
            'full_name', ''
        ).strip()

        profile.phone = request.POST.get(
            'phone', ''
        ).strip()

        profile.college = request.POST.get(
            'college', ''
        ).strip()

        profile.degree = request.POST.get(
            'degree', ''
        ).strip()

        profile.graduation_year = (
            request.POST.get('graduation_year') or None
        )

        profile.cgpa = request.POST.get('cgpa') or None

        profile.skills = request.POST.get('skills', '')

        profile.projects = request.POST.get('projects', '')

        profile.certifications = request.POST.get(
            'certifications', ''
        )

        profile.save()

        return redirect('/student/dashboard/')

    return render(
        request,
        'accounts/student_profile.html',
        {
            'profile': profile,
            'email_value': request.user.email,
        }
    )


# =========================================================
# STUDENT PROFILE - VIEW
# =========================================================

@login_required
def student_profile_view(request):

    profile, created = StudentProfile.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        'accounts/student_profile_view.html',
        {
            'profile': profile,
            'email': request.user.email,
        }
    )


# =========================================================
# STUDENT PROFILE - DELETE
# =========================================================

@login_required
def student_profile_delete(request):

    profile = StudentProfile.objects.get(
        user=request.user
    )

    if request.method == 'POST':

        profile.delete()

        return redirect('/student/dashboard/')

    return render(
        request,
        'accounts/student_profile_delete.html',
        {'profile': profile}
    )


# =========================================================
# COMPANY PROFILE - EDIT
# =========================================================

@login_required
def company_profile(request):

    profile, created = CompanyProfile.objects.get_or_create(
        user=request.user
    )

    email_error = None

    if request.method == 'POST':

        new_email = request.POST.get(
            'email', ''
        ).strip().lower()

        try:
            validate_email(new_email)

        except ValidationError:
            email_error = (
                'Please enter a valid registered email address.'
            )

        if not email_error:

            if User.objects.filter(
                email__iexact=new_email
            ).exclude(
                id=request.user.id
            ).exists():

                email_error = (
                    'This email address is already registered '
                    'with another account.'
                )

        if email_error:

            return render(
                request,
                'accounts/company_profile.html',
                {
                    'profile': profile,
                    'email_value': new_email,
                    'email_error': email_error,
                }
            )

        # Update registered account email
        request.user.email = new_email

        request.user.save(
            update_fields=['email']
        )

        # Update company information
        profile.company_name = request.POST.get(
            'company_name', ''
        ).strip()

        profile.industry = request.POST.get(
            'industry', ''
        ).strip()

        profile.location = request.POST.get(
            'location', ''
        ).strip()

        profile.website = request.POST.get(
            'website', ''
        ).strip()

        profile.description = request.POST.get(
            'description', ''
        )

        profile.recruiter_name = request.POST.get(
            'recruiter_name', ''
        ).strip()

        profile.contact_email = request.POST.get(
            'contact_email', ''
        ).strip()

        profile.contact_phone = request.POST.get(
            'contact_phone', ''
        ).strip()

        profile.save()

        return redirect('/company/dashboard/')

    return render(
        request,
        'accounts/company_profile.html',
        {
            'profile': profile,
            'email_value': request.user.email,
        }
    )


# =========================================================
# COMPANY PROFILE - VIEW
# =========================================================

@login_required
def company_profile_view(request):

    profile, created = CompanyProfile.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        'accounts/company_profile_view.html',
        {
            'profile': profile,
            'email': request.user.email,
        }
    )


# =========================================================
# COMPANY PROFILE - DELETE
# =========================================================

@login_required
def company_profile_delete(request):

    profile = CompanyProfile.objects.get(
        user=request.user
    )

    if request.method == 'POST':

        profile.delete()

        return redirect('/company/dashboard/')

    return render(
        request,
        'accounts/company_profile_delete.html',
        {'profile': profile}
    )


# =========================================================
# NOTIFICATION LIST
# =========================================================

@login_required
def notifications_view(request):

    notifications = Notification.objects.filter(
        user=request.user
    )

    unread_count = notifications.filter(
        is_read=False
    ).count()

    return render(
        request,
        'accounts/notifications.html',
        {
            'notifications': notifications,
            'unread_count': unread_count,
        }
    )


# =========================================================
# MARK SINGLE NOTIFICATION AS READ
# =========================================================

@login_required
@require_POST
def mark_notification_read(request, notification_id):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    notification.is_read = True

    notification.save(
        update_fields=['is_read']
    )

    return redirect('notifications')


# =========================================================
# MARK ALL NOTIFICATIONS AS READ
# =========================================================

@login_required
@require_POST
def mark_all_notifications_read(request):

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return redirect('notifications')


# =========================================================
# MESSAGE RECIPIENT PERMISSIONS
# =========================================================

def get_allowed_message_recipients(user):

    """
    Admin:
        Can message all other users.

    Staff:
        Can message students and companies.

    Company:
        Can message students who applied to its jobs.

    Student:
        Cannot send messages.
    """

    if user.is_superuser:

        return User.objects.exclude(
            id=user.id
        ).order_by('username')

    if user.is_staff:

        return User.objects.filter(
            userprofile__role__in=['student', 'company']
        ).exclude(
            id=user.id
        ).distinct().order_by('username')

    try:
        profile = user.userprofile

    except UserProfile.DoesNotExist:
        return User.objects.none()

    if profile.role == 'company':

        applicant_ids = Application.objects.filter(
            job__company__user=user
        ).values_list(
            'student__user_id',
            flat=True
        ).distinct()

        return User.objects.filter(
            id__in=applicant_ids
        ).exclude(
            id=user.id
        ).order_by('username')

    return User.objects.none()


# =========================================================
# MESSAGE INBOX
# =========================================================

@login_required
def message_inbox(request):

    received = MessageRecipient.objects.filter(
        recipient=request.user
    ).select_related(
        'message',
        'message__sender'
    )

    search = request.GET.get('q', '').strip()

    status = request.GET.get('status', '').strip()

    if search:

        received = received.filter(
            Q(message__subject__icontains=search) |
            Q(message__body__icontains=search) |
            Q(message__sender__username__icontains=search)
        )

    if status == 'unread':

        received = received.filter(
            is_read=False
        )

    elif status == 'read':

        received = received.filter(
            is_read=True
        )

    unread_count = MessageRecipient.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return render(
        request,
        'accounts/message_inbox.html',
        {
            'received_messages': received,
            'unread_count': unread_count,
            'search': search,
            'status': status,
        }
    )


# =========================================================
# SENT MESSAGES
# =========================================================

@login_required
def sent_messages(request):

    sent = Message.objects.filter(
        sender=request.user
    ).prefetch_related(
        'recipients__recipient'
    )

    search = request.GET.get('q', '').strip()

    if search:

        sent = sent.filter(
            Q(subject__icontains=search) |
            Q(body__icontains=search) |
            Q(recipients__recipient__username__icontains=search)
        ).distinct()

    return render(
        request,
        'accounts/sent_messages.html',
        {
            'sent_messages': sent,
            'search': search,
        }
    )


# =========================================================
# SEND MESSAGE
# =========================================================

@login_required
def send_message(request):

    allowed_recipients = get_allowed_message_recipients(
        request.user
    )

    if not allowed_recipients.exists():

        return render(
            request,
            'accounts/send_message.html',
            {
                'recipients': allowed_recipients,
                'error': (
                    'You currently do not have permission or '
                    'eligible recipients to send messages.'
                ),
            }
        )

    if request.method == 'POST':

        subject = request.POST.get(
            'subject', ''
        ).strip()

        body = request.POST.get(
            'body', ''
        ).strip()

        message_type = request.POST.get(
            'message_type', 'general'
        )

        recipient_ids = request.POST.getlist(
            'recipients'
        )

        valid_types = dict(Message.MESSAGE_TYPES)

        selected_recipients = allowed_recipients.filter(
            id__in=recipient_ids
        ).distinct()

        if not subject or not body:

            return render(
                request,
                'accounts/send_message.html',
                {
                    'recipients': allowed_recipients,
                    'error': 'Subject and message are required.',
                }
            )

        if not recipient_ids or not selected_recipients.exists():

            return render(
                request,
                'accounts/send_message.html',
                {
                    'recipients': allowed_recipients,
                    'error': (
                        'Please select at least one valid recipient.'
                    ),
                }
            )

        if message_type not in valid_types:

            message_type = 'general'

        email_addresses = []

        with transaction.atomic():

            message = Message.objects.create(
                sender=request.user,
                subject=subject,
                body=body,
                message_type=message_type
            )

            for recipient in selected_recipients:

                message_recipient = MessageRecipient.objects.create(
                    message=message,
                    recipient=recipient
                )

                Notification.objects.create(
                    user=recipient,
                    title=f'New message: {subject}',
                    message=(
                        f'You received a new message from '
                        f'{request.user.username}.'
                    ),
                    notification_type=(
                        'interview'
                        if message_type == 'interview'
                        else 'system'
                    ),
                    link=(
                        f'/accounts/messages/'
                        f'{message_recipient.id}/'
                    )
                )

                if message_type == 'interview' and recipient.email:

                    email_addresses.append(recipient.email)

        # Existing interview email behaviour retained
        if message_type == 'interview' and email_addresses:

            send_mail(
                subject=f'Interview Update: {subject}',
                message=(
                    f'Hello,\n\n'
                    f'You have received an interview-related message '
                    f'from {request.user.username}.\n\n'
                    f'{body}\n\n'
                    f'Please log in to Workflow AI to view your message.'
                ),
                from_email=getattr(
                    settings,
                    'DEFAULT_FROM_EMAIL',
                    None
                ),
                recipient_list=email_addresses,
                fail_silently=True,
            )

        return redirect('sent_messages')

    return render(
        request,
        'accounts/send_message.html',
        {
            'recipients': allowed_recipients,
        }
    )


# =========================================================
# VIEW MESSAGE AND MARK IT AS READ
# =========================================================

@login_required
def message_detail(request, recipient_id):

    message_recipient = get_object_or_404(
        MessageRecipient.objects.select_related(
            'message',
            'message__sender',
        ),
        id=recipient_id,
        recipient=request.user
    )

    if not message_recipient.is_read:

        message_recipient.is_read = True

        message_recipient.read_at = timezone.now()

        message_recipient.save(
            update_fields=['is_read', 'read_at']
        )

    return render(
        request,
        'accounts/message_detail.html',
        {
            'message_recipient': message_recipient,
            'message': message_recipient.message,
        }
    )


# =========================================================
# ADMIN AND STAFF ACCOUNT PROFILE
# =========================================================

def update_account_profile(request, role):

    # Admin-only profile protection
    if role == 'admin':

        if not request.user.is_superuser:
            raise PermissionDenied

    # Staff-only profile protection
    elif role == 'staff':

        if not request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied

    else:
        raise PermissionDenied

    email_error = None

    if request.method == 'POST':

        new_email = request.POST.get(
            'email', ''
        ).strip().lower()

        first_name = request.POST.get(
            'first_name', ''
        ).strip()

        last_name = request.POST.get(
            'last_name', ''
        ).strip()

        # Validate email
        try:
            validate_email(new_email)

        except ValidationError:

            email_error = (
                'Please enter a valid email address.'
            )

        # Check email uniqueness
        if not email_error:

            if User.objects.filter(
                email__iexact=new_email
            ).exclude(
                id=request.user.id
            ).exists():

                email_error = (
                    'This email is already registered '
                    'with another account.'
                )

        if not email_error:

            request.user.email = new_email

            request.user.first_name = first_name

            request.user.last_name = last_name

            request.user.save(
                update_fields=[
                    'email',
                    'first_name',
                    'last_name'
                ]
            )

            if role == 'admin':

                return redirect('admin_profile')

            return redirect('staff_profile')

    return render(
        request,
        'accounts/staff_admin_profile.html',
        {
            'profile_role': role,
            'email_error': email_error,
            'email_value': (
                request.POST.get(
                    'email',
                    request.user.email
                )
                if request.method == 'POST'
                else request.user.email
            ),
        }
    )


# =========================================================
# ADMIN PROFILE
# =========================================================

@login_required
def admin_profile(request):

    return update_account_profile(
        request,
        'admin'
    )


# =========================================================
# STAFF PROFILE
# =========================================================

@login_required
def staff_profile(request):

    return update_account_profile(
        request,
        'staff'
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):

    logout(request)

    return redirect('/')
