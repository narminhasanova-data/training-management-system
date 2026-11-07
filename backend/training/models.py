"""Training data: the course catalogue, cohorts and their students, the weekly teaching plan,
homework and grades, agendas, weekly surveys and the Google Classroom mirror."""

import secrets
from datetime import date

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

PALETTE = ["indigo", "amber", "sky", "rose", "lime"]


def new_token() -> str:
    return secrets.token_urlsafe(24)


class Course(models.Model):
    """A training in the catalogue, e.g. "SQL Foundations". Agendas use it as a module and
    weekly surveys as a question block."""

    class DaySplit(models.TextChoices):
        NONE = "none", "One session per week"
        ALL = "all", "Day 1 and Day 2 every week"
        SOME = "some", "Day 1 and Day 2 in selected weeks"

    name = models.CharField(max_length=80, unique=True)
    weeks = models.PositiveSmallIntegerField(default=4)
    day_split = models.CharField(max_length=4, choices=DaySplit.choices, default=DaySplit.NONE)
    split_weeks = models.JSONField(default=list, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    def days_in_week(self, course_week: int) -> list[int]:
        """[1, 2] when that week of the course is taught as Day 1 / Day 2, else []."""
        if self.day_split == self.DaySplit.ALL or (
            self.day_split == self.DaySplit.SOME and course_week in (self.split_weeks or [])
        ):
            return [1, 2]
        return []


class Cohort(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"

    class Source(models.TextChoices):
        MANUAL = "manual", "Created by staff"
        SEED = "seed", "Demo data"
        CLASSROOM = "classroom", "Imported from Classroom"

    number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=120)
    start_date = models.DateField(null=True, blank=True)
    weeks_total = models.PositiveSmallIntegerField(default=12)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UPCOMING)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    classroom_synced_at = models.DateTimeField(null=True, blank=True)
    classroom_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-number"]

    def __str__(self):
        return self.name

    @property
    def current_week(self) -> int:
        if self.status == self.Status.FINISHED:
            return self.weeks_total
        if not self.start_date or date.today() < self.start_date:
            return 1
        return max(1, min(self.weeks_total, (date.today() - self.start_date).days // 7 + 1))


class Student(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="students")
    code = models.CharField(max_length=20)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, db_index=True)
    phone = models.CharField(max_length=32, blank=True)
    courses = models.JSONField(default=list, blank=True)
    dropped = models.BooleanField(default=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="student_profiles"
    )
    classroom_user_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["cohort", "code"]
        constraints = [models.UniqueConstraint(fields=["cohort", "code"], name="uniq_student_code")]

    def __str__(self):
        return f"{self.full_name} ({self.code})"

    @property
    def first_name(self) -> str:
        return self.full_name.split()[0] if self.full_name else ""


class Week(models.Model):
    """Per-week plan of a cohort: topics by course ({course: [topic, ...]})."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="weeks")
    number = models.PositiveSmallIntegerField()
    topics = models.JSONField(default=dict, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["cohort", "number"]
        constraints = [models.UniqueConstraint(fields=["cohort", "number"], name="uniq_week")]


class Lesson(models.Model):
    class Kind(models.TextChoices):
        LECTURE = "lecture", "Lecture"
        PRACTICE = "practice", "Practice"

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="lessons")
    week = models.PositiveSmallIntegerField()
    course = models.CharField(max_length=80)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.LECTURE)
    title = models.CharField(max_length=150, blank=True)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    trainer = models.CharField(max_length=120, blank=True)
    mentor = models.CharField(max_length=120, blank=True)
    held = models.BooleanField(default=True)

    class Meta:
        ordering = ["cohort", "week", "date", "start_time", "id"]

    def __str__(self):
        return f"{self.cohort} · W{self.week} · {self.course} ({self.kind})"


class Attendance(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="attendance")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance")
    present = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lesson", "student"], name="uniq_attendance")]


class Assignment(models.Model):
    class Kind(models.TextChoices):
        HOMEWORK = "homework", "Homework"
        PROJECT = "project", "Project"

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="assignments")
    week = models.PositiveSmallIntegerField()
    course = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.HOMEWORK)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    max_points = models.FloatField(default=10)
    published = models.BooleanField(default=True)
    attachment = models.FileField(upload_to="assignments/", blank=True)
    external_id = models.CharField(max_length=64, blank=True, db_index=True)
    external_link = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ["cohort", "week", "course", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cohort", "external_id"], condition=~Q(external_id=""), name="uniq_assignment_external"
            )
        ]

    def __str__(self):
        return self.title


class Submission(models.Model):
    class Source(models.TextChoices):
        PORTAL = "portal", "Student portal"
        CLASSROOM = "classroom", "Google Classroom"
        STAFF = "staff", "Entered by staff"

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="submissions")
    submitted_at = models.DateTimeField(null=True, blank=True)
    late = models.BooleanField(default=False)
    link = models.URLField(max_length=500, blank=True)
    text = models.TextField(blank=True)
    file = models.FileField(upload_to="submissions/", blank=True)
    points = models.FloatField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.CharField(max_length=120, blank=True)
    feedback = models.TextField(blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.PORTAL)
    external_state = models.CharField(max_length=32, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["assignment", "student"], name="uniq_submission")]

    @property
    def status(self) -> str:
        if self.points is not None:
            return "graded"
        return "submitted" if self.submitted_at else "missing"


class LearningMaterial(models.Model):
    """A file or link the training office publishes for a cohort's week."""

    class Kind(models.TextChoices):
        SLIDES = "slides", "Slides"
        CODE = "code", "Code"
        DATASET = "dataset", "Dataset"
        READING = "reading", "Reading"
        OTHER = "other", "Other"

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="learning_materials")
    week = models.PositiveSmallIntegerField()
    course = models.CharField(max_length=80, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SLIDES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="materials/", blank=True)
    url = models.URLField(max_length=500, blank=True)
    visible = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["cohort", "week", "position", "id"]


class LessonRecording(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="recordings")
    week = models.PositiveSmallIntegerField()
    course = models.CharField(max_length=80, blank=True)
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name="recordings")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="recordings/", blank=True)
    url = models.URLField(max_length=500, blank=True)
    duration_min = models.PositiveIntegerField(null=True, blank=True)
    recorded_on = models.DateField(null=True, blank=True)
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["cohort", "week", "id"]


class LessonFeedback(models.Model):
    """A student's quick 1–5 rating of one lesson (from the student API)."""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="feedback")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="lesson_feedback")
    overall = models.PositiveSmallIntegerField()
    trainer = models.PositiveSmallIntegerField(null=True, blank=True)
    materials = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lesson", "student"], name="uniq_lesson_feedback")]


class MentoringSession(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="mentoring")
    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL, related_name="mentoring")
    mentor = models.CharField(max_length=120)
    date = models.DateField()
    minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["cohort", "-date", "id"]


class ActionItem(models.Model):
    """Something students raised and what the team does about it."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="action_items")
    week = models.PositiveSmallIntegerField(null=True, blank=True)
    feedback = models.TextField()
    action = models.TextField(blank=True)
    result = models.TextField(blank=True)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["cohort", "done", "-created_at"]


class Agenda(models.Model):
    """The timetable students receive for a week, or for an exam / career day."""

    class Kind(models.TextChoices):
        WEEK = "week", "Week"
        MIDTERM = "midterm", "Midterm exam"
        FINAL = "final", "Final exam"
        CAREER = "career", "Career day"

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="agendas")
    week = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.WEEK)
    days = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=120, blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    emailed_count = models.PositiveIntegerField(default=0)
    whatsapp_at = models.DateTimeField(null=True, blank=True)
    whatsapp_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cohort", "week", "kind"], name="uniq_agenda")]


class Survey(models.Model):
    """The weekly survey of a cohort: one block per course taught that week, then rating grids
    for trainers, mentors and materials. Each grid may ask about its own week (grid_weeks)."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="surveys")
    week = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    blocks = models.JSONField(default=list, blank=True)
    trainers = models.JSONField(default=list, blank=True)
    mentors = models.JSONField(default=list, blank=True)
    materials = models.JSONField(default=list, blank=True)
    grid_weeks = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=120, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cohort", "week"], name="uniq_survey")]

    def __str__(self):
        return self.title


class SurveyInvite(models.Model):
    """A student's personal survey link (/s/<token>/); no login needed."""

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="invites")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="survey_invites")
    token = models.CharField(max_length=48, unique=True, default=new_token)
    channels = models.CharField(max_length=40, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["survey", "student"], name="uniq_invite")]

    def add_channel(self, channel: str) -> None:
        parts = [c for c in self.channels.split(",") if c]
        if channel not in parts:
            parts.append(channel)
        self.channels = ",".join(parts)
        self.sent_at = timezone.now()


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    student = models.ForeignKey(
        Student, null=True, blank=True, on_delete=models.SET_NULL, related_name="survey_responses"
    )
    invite = models.OneToOneField(
        SurveyInvite, null=True, blank=True, on_delete=models.SET_NULL, related_name="response"
    )
    answers = models.JSONField(default=dict)
    understanding = models.FloatField(null=True, blank=True)
    trainer_score = models.FloatField(null=True, blank=True)
    mentor_score = models.FloatField(null=True, blank=True)
    materials_score = models.FloatField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)


class ClassroomClass(models.Model):
    """A Google Classroom class feeding a cohort: one class per course."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="classroom_classes")
    external_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    section = models.CharField(max_length=120, blank=True)
    course = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=20, blank=True)
    teachers = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["cohort", "course", "name"]

    def __str__(self):
        return self.name


class ClassroomMaterial(models.Model):
    """A "material" post of a Classroom class: slides, files, links or videos."""

    classroom_class = models.ForeignKey(ClassroomClass, on_delete=models.CASCADE, related_name="materials")
    external_id = models.CharField(max_length=64)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    topic = models.CharField(max_length=200, blank=True)
    week = models.PositiveSmallIntegerField(null=True, blank=True)
    attachments = models.JSONField(default=list, blank=True)
    link = models.URLField(max_length=500, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["week", "posted_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["classroom_class", "external_id"], name="uniq_classroom_material")
        ]
