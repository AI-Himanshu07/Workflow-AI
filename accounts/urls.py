
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # =====================================================
    # FORGOT PASSWORD / PASSWORD RESET
    # =====================================================

    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
        ),
        name='password_reset'
    ),

    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),

    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    # =====================================================
    # STUDENT PROFILE
    # =====================================================

    path('student/profile/', views.student_profile, name='student_profile'),
    path('student/profile/view/', views.student_profile_view, name='student_profile_view'),
    path('student/profile/delete/', views.student_profile_delete, name='student_profile_delete'),

    # =====================================================
    # COMPANY PROFILE
    # =====================================================

    path('company/profile/', views.company_profile, name='company_profile'),
    path('company/profile/view/', views.company_profile_view, name='company_profile_view'),
    path('company/profile/delete/', views.company_profile_delete, name='company_profile_delete'),

    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # =====================================================
    # MESSAGING SYSTEM
    # =====================================================

    path('messages/', views.message_inbox, name='message_inbox'),
    path('messages/sent/', views.sent_messages, name='sent_messages'),
    path('messages/compose/', views.send_message, name='send_message'),
    path('messages/<int:recipient_id>/', views.message_detail, name='message_detail'),


    path('admin/profile/', views.admin_profile, name='admin_profile'),
path('staff/profile/', views.staff_profile, name='staff_profile'),
]
