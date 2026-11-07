from django.urls import path

from . import records, views

C = "cohorts/<int:number>/"


def pair(prefix, views_pair, name):
    listing, detail = views_pair
    return [
        path(C + prefix + "/", listing, name=f"{name}-list"),
        path(C + prefix + "/<int:pk>/", detail, name=f"{name}-detail"),
    ]


urlpatterns = [
    path("cohorts/", views.cohorts, name="cohorts"),
    path("cohorts/compare/", views.compare, name="cohorts-compare"),
    path(C, views.cohort_detail, name="cohort-detail"),
    path(C + "weeks/<int:week>/", views.week_detail, name="cohort-week"),
    path(C + "reports/weekly/", views.weekly_report, name="cohort-weekly-report"),
    path(C + "agenda/", views.agenda, name="agenda"),
    path(C + "agenda/pdf/", views.agenda_pdf, name="agenda-pdf"),
    path(C + "agenda/send/", views.agenda_send, name="agenda-send"),
    path(C + "survey/", views.survey, name="survey"),
    path(C + "survey/send/", views.survey_send, name="survey-send"),
    path(C + "gradebook/", views.gradebook_view, name="gradebook"),
    path(C + "classroom/sync/", views.classroom_sync, name="classroom-sync"),
    path(C + "attendance/", records.attendance, name="attendance"),
    path(C + "assignments/<int:pk>/grade/", records.grade, name="assignment-grade"),
    path(C + "lesson-feedback/", records.LessonFeedbackList.as_view(), name="lesson-feedback"),
    *pair("students", records.students, "student"),
    *pair("lessons", records.lessons, "lesson"),
    *pair("assignments", records.assignments, "assignment"),
    *pair("materials", records.materials, "material"),
    *pair("recordings", records.recordings, "recording"),
    *pair("mentoring", records.mentoring, "mentoring"),
    *pair("action-items", records.action_items, "action-item"),
    path("courses/", views.courses, name="courses"),
    path("recipients/", views.recipient_list, name="recipients"),
    path("classroom/classes/", views.classroom_classes, name="classroom-classes"),
    path("classroom/import/", views.classroom_import, name="classroom-import"),
    path("library/", views.library_view, name="library"),
    path("library/send/", views.library_send, name="library-send"),
]
