from django.urls import path

from . import student

urlpatterns = [
    path("auth/mock-sign-in/", student.mock_sign_in, name="student-sign-in"),
    path("me/", student.me, name="student-me"),
    path("logout/", student.logout, name="student-logout"),
    path("cohorts/<int:number>/", student.cohort_view, name="student-cohort"),
    path("cohorts/<int:number>/submissions/", student.submit, name="student-submit"),
    path("cohorts/<int:number>/lesson-feedback/", student.rate_lesson, name="student-rate-lesson"),
]
