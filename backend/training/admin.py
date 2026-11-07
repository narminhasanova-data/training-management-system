from django.contrib import admin

from . import models


class StudentInline(admin.TabularInline):
    model = models.Student
    extra = 0
    fields = ("code", "full_name", "email", "phone", "dropped")


@admin.register(models.Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "status", "start_date", "weeks_total", "source", "classroom_synced_at")
    list_filter = ("status", "source")
    search_fields = ("name", "number")
    inlines = [StudentInline]


@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "weeks", "day_split", "position")


@admin.register(models.Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "email", "cohort", "dropped")
    list_filter = ("cohort", "dropped")
    search_fields = ("full_name", "email", "code")


@admin.register(models.Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("cohort", "week", "course", "kind", "date", "start_time", "trainer")
    list_filter = ("cohort", "course", "kind")


@admin.register(models.Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "cohort", "week", "course", "max_points", "published")
    list_filter = ("cohort", "course")
    search_fields = ("title",)


@admin.register(models.Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "submitted_at", "points", "late", "source")
    list_filter = ("source", "late")


@admin.register(models.Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ("cohort", "week", "kind", "updated_at", "emailed_at", "whatsapp_at")
    list_filter = ("cohort", "kind")


@admin.register(models.Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "cohort", "week", "updated_at")
    list_filter = ("cohort",)


@admin.register(models.SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ("survey", "student", "understanding", "trainer_score", "mentor_score", "submitted_at")
    list_filter = ("survey__cohort",)


@admin.register(models.ClassroomClass)
class ClassroomClassAdmin(admin.ModelAdmin):
    list_display = ("name", "cohort", "course", "state", "external_id")
    list_filter = ("cohort", "state")


admin.site.register(
    [
        models.Week,
        models.Attendance,
        models.LearningMaterial,
        models.LessonRecording,
        models.LessonFeedback,
        models.MentoringSession,
        models.ActionItem,
        models.SurveyInvite,
        models.ClassroomMaterial,
    ]
)
