"""The Google Classroom operations the sync needs. Responses keep the Classroom REST API's JSON
shapes (courses, students, teachers, topics, courseWork, studentSubmissions, courseWorkMaterials)
so a real HTTP client can be dropped in behind the same interface."""

from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string


class ClassroomError(Exception):
    pass


class ClassroomProvider(Protocol):
    def list_courses(self) -> list[dict]: ...
    def list_students(self, course_id: str) -> list[dict]: ...
    def list_teachers(self, course_id: str) -> list[dict]: ...
    def list_topics(self, course_id: str) -> list[dict]: ...
    def list_coursework(self, course_id: str) -> list[dict]: ...
    def list_submissions(self, course_id: str) -> list[dict]: ...
    def list_materials(self, course_id: str) -> list[dict]: ...


PROVIDERS = {"fake": "integrations.classroom.fake.FakeClassroom"}


def get_provider() -> ClassroomProvider:
    name = settings.TMS["CLASSROOM_PROVIDER"]
    if name not in PROVIDERS:
        raise ClassroomError(f"Classroom provider '{name}' is not available in this demo (use 'fake').")
    return import_string(PROVIDERS[name])()
