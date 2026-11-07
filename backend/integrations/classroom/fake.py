"""Offline Classroom provider backed by a generated dataset (see training.demo.data)."""

from datetime import date

from django.conf import settings
from django.utils.module_loading import import_string

DEFAULT_DATASET = "training.demo.data.classroom_dataset"


class FakeClassroom:
    _cache: dict = {}

    def __init__(self):
        today = date.today()
        if FakeClassroom._cache.get("day") != today:
            factory = import_string(getattr(settings, "CLASSROOM_FAKE_DATASET", DEFAULT_DATASET))
            FakeClassroom._cache = {"day": today, "data": factory(today)}
        self.data = FakeClassroom._cache["data"]

    def list_courses(self):
        return list(self.data["courses"])

    def _get(self, key, course_id):
        return list(self.data[key].get(course_id, []))

    def list_students(self, course_id):
        return self._get("students", course_id)

    def list_teachers(self, course_id):
        return self._get("teachers", course_id)

    def list_topics(self, course_id):
        return self._get("topics", course_id)

    def list_coursework(self, course_id):
        return self._get("coursework", course_id)

    def list_materials(self, course_id):
        return self._get("materials", course_id)

    def list_submissions(self, course_id):
        return [s for (cid, _), subs in self.data["submissions"].items() if cid == course_id for s in subs]
