import copy

import pytest
from django.utils import timezone

from integrations import accounts
from integrations.classroom.fake import FakeClassroom
from training.models import Assignment, Cohort, Submission
from training.services import classroom


def test_classes_are_grouped_by_cohort(api):
    d = api.get("/api/classroom/classes/").json()
    numbers = [c["number"] for c in d["cohorts"]]
    assert numbers == [104, 102] and d["left_out"] == 2
    c104 = d["cohorts"][0]
    assert not c104["on_site"] and c104["new_classes"] == 2
    assert {x["course"] for x in c104["classes"]} == {"Spreadsheet Analytics", "Python for Data"}


def test_import_creates_the_cohort_with_its_students(api):
    r = api.post("/api/classroom/import/", {"number": 104}, format="json")
    assert r.status_code == 201
    cohort = Cohort.objects.get(number=104)
    assert cohort.source == "classroom" and cohort.status == "upcoming"
    assert cohort.students.count() == 12 and cohort.classroom_classes.count() == 2
    assert api.post("/api/classroom/import/", {"number": 999}, format="json").status_code == 404


def test_sync_is_idempotent(cohort102):
    first = classroom.sync(cohort102)
    counts = (
        Assignment.objects.filter(cohort=cohort102).count(),
        Submission.objects.filter(assignment__cohort=cohort102).count(),
    )
    second = classroom.sync(cohort102)
    assert first == second
    assert counts == (
        Assignment.objects.filter(cohort=cohort102).count(),
        Submission.objects.filter(assignment__cohort=cohort102).count(),
    )
    assert len(first["unmatched"]) == 2


def test_grades_entered_on_the_site_win(cohort102):
    sub = Submission.objects.filter(assignment__cohort=cohort102, points__isnull=False).first()
    sub.points, sub.source = 1.0, Submission.Source.STAFF
    sub.save()
    classroom.sync(cohort102)
    sub.refresh_from_db()
    assert sub.points == 1.0


def test_unmatched_students_can_be_added(api, cohort102):
    r = api.post("/api/cohorts/102/classroom/sync/", {"add_unmatched": True}, format="json")
    assert r.status_code == 200
    assert set(cohort102.students.filter(code__startswith="CL-").values_list("full_name", flat=True)) == {
        "Iris Calloway",
        "Malik Osei",
    }


def test_coursework_deleted_in_classroom_disappears(cohort102):
    FakeClassroom()  # build the dataset
    data = copy.deepcopy(FakeClassroom._cache["data"])
    removed = data["coursework"]["c102-sql-foundations"].pop()
    FakeClassroom._cache["data"] = data
    classroom.sync(cohort102)
    assert not Assignment.objects.filter(external_id=f"c102-sql-foundations:{removed['id']}").exists()


def test_expired_connection_is_reported(api, cohort102):
    accounts.expire("classroom")
    r = api.post("/api/cohorts/102/classroom/sync/", {}, format="json")
    assert r.status_code == 409 and "expired" in r.json()["error"]
    assert api.get("/api/classroom/classes/").status_code == 409


def test_sync_due_respects_the_interval(cohort102):
    Cohort.objects.filter(pk=cohort102.pk).update(classroom_synced_at=timezone.now())
    assert classroom.sync_due() == []
    Cohort.objects.filter(pk=cohort102.pk).update(classroom_synced_at=None)
    assert classroom.sync_due() == [102]


@pytest.mark.parametrize(
    "week, expected", [(1, {"Spreadsheet Analytics", "Python for Data"}), (6, {"SQL Foundations", "Python for Data"})]
)
def test_week_courses_from_classroom(cohort102, week, expected):
    assert {c for c, _, _ in classroom.week_courses(cohort102, week)} == expected


def test_auto_import_brings_new_cohorts():
    assert classroom.auto_import() == [104]
    assert classroom.auto_import() == []
