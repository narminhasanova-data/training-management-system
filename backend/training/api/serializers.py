from rest_framework import serializers

from ..models import (
    PALETTE,
    ActionItem,
    Agenda,
    Assignment,
    Attendance,
    Cohort,
    Course,
    LearningMaterial,
    Lesson,
    LessonFeedback,
    LessonRecording,
    MentoringSession,
    Student,
    Week,
)

CHANNELS = [("email", "Email"), ("whatsapp", "WhatsApp")]


# --------------------------------------------------------------------------- catalogue and cohorts
class CourseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Course
        fields = ["id", "name", "weeks", "day_split", "split_weeks", "position"]
        extra_kwargs = {"name": {"validators": []}, "position": {"read_only": True}}

    def validate_weeks(self, value):
        if not 1 <= value <= 52:
            raise serializers.ValidationError("Between 1 and 52 weeks.")
        return value

    def validate_split_weeks(self, value):
        if not all(isinstance(w, int) and 1 <= w <= 52 for w in value):
            raise serializers.ValidationError("Weeks must be numbers between 1 and 52.")
        return value


class CatalogueSerializer(serializers.Serializer):
    courses = CourseSerializer(many=True)


class CohortSerializer(serializers.ModelSerializer):
    current_week = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cohort
        fields = ["number", "name", "start_date", "weeks_total", "status", "source", "current_week"]
        read_only_fields = ["source"]


class WeekSerializer(serializers.ModelSerializer):
    class Meta:
        model = Week
        fields = ["number", "topics", "note"]
        read_only_fields = ["number"]


# --------------------------------------------------------------------------- sending
class SendSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=CHANNELS)
    student_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    test_to = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")

    def validate(self, attrs):
        if bool(attrs["student_ids"]) == bool(attrs["test_to"]):
            raise serializers.ValidationError(
                "Send either to chosen students (student_ids) or a test address (test_to)."
            )
        if attrs["test_to"] and attrs["channel"] == "email":
            serializers.EmailField().run_validation(attrs["test_to"])
        return attrs


class SendResultSerializer(serializers.Serializer):
    sent = serializers.IntegerField()
    failed = serializers.ListField(child=serializers.DictField())


# --------------------------------------------------------------------------- agenda
class AgendaQuerySerializer(serializers.Serializer):
    week = serializers.IntegerField(min_value=1, max_value=52)
    kind = serializers.ChoiceField(choices=Agenda.Kind.choices, default=Agenda.Kind.WEEK)


class AgendaRowSerializer(serializers.Serializer):
    time = serializers.CharField(allow_blank=True, max_length=24)
    text = serializers.CharField(allow_blank=True, max_length=240)
    track = serializers.IntegerField(allow_null=True, min_value=0)


class AgendaTrackSerializer(serializers.Serializer):
    course = serializers.CharField(allow_blank=True, max_length=80)
    color = serializers.ChoiceField(choices=PALETTE)


class AgendaDaySerializer(serializers.Serializer):
    heading = serializers.CharField(required=False, allow_blank=True, max_length=120)
    date = serializers.CharField(allow_blank=True, max_length=10)
    free = serializers.BooleanField()
    tracks = AgendaTrackSerializer(many=True)
    rows = AgendaRowSerializer(many=True)


class AgendaSaveSerializer(AgendaQuerySerializer):
    days = AgendaDaySerializer(many=True)


class AgendaSendSerializer(AgendaQuerySerializer, SendSerializer):
    pass


# --------------------------------------------------------------------------- survey
class SurveyBlockSerializer(serializers.Serializer):
    course = serializers.CharField(max_length=80)
    course_week = serializers.IntegerField(min_value=1, max_value=52)
    day = serializers.ChoiceField(choices=[0, 1, 2])
    trainer = serializers.CharField(allow_blank=True, max_length=120, required=False, default="")
    week = serializers.IntegerField(min_value=1, max_value=52)


class SurveyQuerySerializer(serializers.Serializer):
    week = serializers.IntegerField(min_value=1, max_value=52)


class SurveySaveSerializer(SurveyQuerySerializer):
    title = serializers.CharField(max_length=200)
    blocks = SurveyBlockSerializer(many=True)
    trainers = serializers.ListField(child=serializers.CharField(max_length=120, allow_blank=True), max_length=20)
    mentors = serializers.ListField(child=serializers.CharField(max_length=120, allow_blank=True), max_length=20)
    materials = serializers.ListField(child=serializers.CharField(max_length=120, allow_blank=True), max_length=20)
    grid_weeks = serializers.DictField(
        child=serializers.IntegerField(min_value=1, max_value=52), required=False, default=dict
    )


class SurveySendSerializer(SurveyQuerySerializer, SendSerializer):
    pass


# --------------------------------------------------------------------------- classroom and library
class ClassroomImportSerializer(serializers.Serializer):
    number = serializers.IntegerField(min_value=1)


class ClassroomSyncSerializer(serializers.Serializer):
    add_unmatched = serializers.BooleanField(required=False, default=False)


class LibraryQuerySerializer(serializers.Serializer):
    course = serializers.CharField(required=False, allow_blank=True, default="")
    cohort = serializers.IntegerField(required=False, allow_null=True, default=None)


class LibrarySendSerializer(serializers.Serializer):
    course = serializers.CharField(max_length=80)
    cohort = serializers.IntegerField()
    material_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    student_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    test_to = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if bool(attrs["student_ids"]) == bool(attrs["test_to"]):
            raise serializers.ValidationError(
                "Send either to chosen students (student_ids) or a test address (test_to)."
            )
        return attrs


class WeekQuerySerializer(serializers.Serializer):
    week = serializers.IntegerField(min_value=1, max_value=52, required=False, allow_null=True, default=None)


class ChannelQuerySerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=CHANNELS, default="email")


# --------------------------------------------------------------------------- records (backend API)
class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["id", "code", "full_name", "email", "phone", "courses", "dropped", "classroom_user_id"]
        read_only_fields = ["classroom_user_id"]

    def validate_code(self, value):
        cohort = self.context["cohort"]
        clash = Student.objects.filter(cohort=cohort, code=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("This code is already used in the cohort.")
        return value


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "week", "course", "kind", "title", "date", "start_time", "trainer", "mentor", "held"]


class AttendanceMarkSerializer(serializers.Serializer):
    lesson = serializers.IntegerField()
    student = serializers.IntegerField()
    present = serializers.BooleanField()


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["lesson", "student", "present"]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "id",
            "week",
            "course",
            "title",
            "kind",
            "description",
            "due_at",
            "max_points",
            "published",
            "attachment",
            "external_id",
            "external_link",
        ]
        read_only_fields = ["external_id", "external_link"]


class GradeSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    points = serializers.FloatField(required=False, allow_null=True, min_value=0)
    submitted = serializers.BooleanField(required=False)
    feedback = serializers.CharField(required=False, allow_blank=True)


class LearningMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningMaterial
        fields = ["id", "week", "course", "kind", "title", "file", "url", "visible", "position", "created_at"]

    def validate(self, attrs):
        file = attrs.get("file", getattr(self.instance, "file", None))
        url = attrs.get("url", getattr(self.instance, "url", ""))
        if not file and not url:
            raise serializers.ValidationError("Upload a file or give a link.")
        return attrs


class LessonRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonRecording
        fields = [
            "id",
            "week",
            "course",
            "lesson",
            "title",
            "file",
            "url",
            "duration_min",
            "recorded_on",
            "visible",
            "created_at",
        ]

    def validate(self, attrs):
        file = attrs.get("file", getattr(self.instance, "file", None))
        url = attrs.get("url", getattr(self.instance, "url", ""))
        if not file and not url:
            raise serializers.ValidationError("Upload a file or give a link.")
        return attrs


class LessonFeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    course = serializers.CharField(source="lesson.course", read_only=True)
    week = serializers.IntegerField(source="lesson.week", read_only=True)

    class Meta:
        model = LessonFeedback
        fields = [
            "id",
            "lesson",
            "week",
            "course",
            "student",
            "student_name",
            "overall",
            "trainer",
            "materials",
            "comment",
            "created_at",
        ]


class MentoringSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentoringSession
        fields = ["id", "student", "mentor", "date", "minutes", "notes", "rating"]


class ActionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionItem
        fields = ["id", "week", "feedback", "action", "result", "done", "created_at", "updated_at"]


# --------------------------------------------------------------------------- student API
class StudentSignInSerializer(serializers.Serializer):
    email = serializers.EmailField()


class StudentSubmitSerializer(serializers.Serializer):
    assignment = serializers.IntegerField()
    link = serializers.URLField(required=False, allow_blank=True, default="")
    text = serializers.CharField(required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        if not (attrs["link"] or attrs["text"] or attrs["file"]):
            raise serializers.ValidationError("Attach a file, a link or some text.")
        return attrs


class StudentLessonRatingSerializer(serializers.Serializer):
    lesson = serializers.IntegerField()
    overall = serializers.IntegerField(min_value=1, max_value=5)
    trainer = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    materials = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")
