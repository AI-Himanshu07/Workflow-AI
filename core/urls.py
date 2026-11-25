
from django.urls import path
from . import views


urlpatterns = [

    # =========================
    # HOME
    # =========================
    path('', views.home, name='home'),

    # =========================
    # STUDENT DASHBOARD
    # =========================
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/jobs/', views.student_jobs, name='student_jobs'),
    path('student/job/<int:job_id>/', views.student_job_detail, name='student_job_detail'),
    path('student/apply/<int:job_id>/', views.apply_job, name='apply_job'),
    path('student/applications/', views.my_applications, name='my_applications'),
    path('student/withdraw/<int:application_id>/', views.withdraw_application, name='withdraw_application'),

    # =========================
    # STUDENT ASSESSMENT
    # =========================
    path(
        'student/assessment/<int:application_id>/',
        views.start_assessment,
        name='start_assessment'
    ),
    path(
        'student/assessment/<int:application_id>/submit/',
        views.submit_assessment,
        name='submit_assessment'
    ),
    path(
        'student/assessment/attempt/<int:attempt_id>/violation/',
        views.record_assessment_violation,
        name='record_assessment_violation'
    ),
    path(
        'student/assessment/result/<int:attempt_id>/',
        views.assessment_result,
        name='assessment_result'
    ),

    # =========================
    # COMPANY ACCESS REQUEST
    # =========================
    path('company/access-request/', views.company_access_request, name='company_access_request'),
    path('company/access-status/', views.company_access_status, name='company_access_status'),

    # =========================
    # COMPANY DASHBOARD
    # =========================
    path('company/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('company/create-job/', views.create_job, name='create_job'),
    path('company/jobs/', views.company_jobs, name='company_jobs'),
    path('company/job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('company/job/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('company/job/<int:job_id>/delete/', views.delete_job, name='delete_job'),

    # =========================
    # COMPANY APPLICANTS
    # =========================
    path(
        'company/job/<int:job_id>/applicants/',
        views.company_applicants,
        name='company_applicants'
    ),
    path(
        'company/applicants/',
        views.company_applicants,
        name='company_all_applicants'
    ),
    path(
        'company/applicant/<int:application_id>/',
        views.applicant_profile,
        name='applicant_profile'
    ),
    path(
        'company/rankings/',
        views.applicant_ranking,
        name='applicant_ranking'
    ),
    path(
        'company/job/<int:job_id>/ranking/',
        views.applicant_ranking,
        name='applicant_ranking'
    ),
    path(
        'company/job/<int:job_id>/hiring-workflow/',
        views.hiring_workflow,
        name='hiring_workflow'
    ),
    path(
        'company/hiring-workflows/',
        views.hiring_workflow_jobs,
        name='hiring_workflow_jobs'
    ),
    path(
        'company/manage-applicant/<int:application_id>/',
        views.manage_applicant,
        name='manage_applicant'
    ),

    # =========================
    # COMPANY ASSESSMENTS
    # =========================
    path(
        'company/job/<int:job_id>/assessments/',
        views.manage_assessment_questions,
        name='manage_assessment_questions'
    ),
    path(
        'company/job/<int:job_id>/assessments/add/',
        views.add_assessment_question,
        name='add_assessment_question'
    ),
    path(
        'company/assessment/question/<int:question_id>/delete/',
        views.delete_assessment_question,
        name='delete_assessment_question'
    ),
    path(
        'company/assessment/result/<int:attempt_id>/',
        views.company_assessment_result,
        name='company_assessment_result'
    ),

    # =========================
    # CUSTOM ADMIN DASHBOARD
    # =========================
    path('workflow-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('workflow-admin/applications/', views.admin_applications, name='admin_applications'),
    path(
        'workflow-admin/applications/<int:application_id>/delete/',
        views.admin_delete_application,
        name='admin_delete_application'
    ),

    # =========================
    # ADMIN COMPANY VERIFICATION
    # =========================
    path('workflow-admin/company-requests/', views.admin_company_requests, name='admin_company_requests'),
    path(
        'workflow-admin/company-requests/<int:request_id>/',
        views.admin_company_request_detail,
        name='admin_company_request_detail'
    ),
    path(
        'workflow-admin/company-requests/<int:request_id>/review/',
        views.review_company_access_request,
        name='review_company_access_request'
    ),
    path(
        'workflow-admin/company-requests/<int:request_id>/document/',
        views.company_verification_document,
        name='company_verification_document'
    ),

    # =========================
    # STUDENT MANAGEMENT
    # =========================
    path('workflow-admin/students/', views.admin_students, name='admin_students'),
    path(
        'workflow-admin/students/<int:user_id>/toggle/',
        views.admin_toggle_student,
        name='admin_toggle_student'
    ),
    path(
        'workflow-admin/students/<int:user_id>/delete/',
        views.admin_delete_student,
        name='admin_delete_student'
    ),

    # =========================
    # COMPANY MANAGEMENT
    # =========================
    path('workflow-admin/companies/', views.admin_companies, name='admin_companies'),
    path(
        'workflow-admin/companies/<int:user_id>/toggle/',
        views.admin_toggle_company,
        name='admin_toggle_company'
    ),
    path(
        'workflow-admin/companies/<int:user_id>/delete/',
        views.admin_delete_company,
        name='admin_delete_company'
    ),

    # =========================
    # STAFF DASHBOARD
    # =========================
    path('workflow-staff/', views.staff_dashboard, name='staff_dashboard'),

    # =========================
    # STAFF MANAGEMENT (ADMIN ONLY)
    # =========================
    path('workflow-admin/staff/', views.admin_staff, name='admin_staff'),
    path(
        'workflow-admin/staff/<int:user_id>/toggle/',
        views.admin_toggle_staff,
        name='admin_toggle_staff'
    ),
    path(
        'workflow-admin/staff/<int:user_id>/delete/',
        views.admin_delete_staff,
        name='admin_delete_staff'
    ),

    path(
    'workflow-admin/applications/<int:application_id>/withdraw/',
    views.admin_withdraw_application,
    name='admin_withdraw_application'
),
]
 