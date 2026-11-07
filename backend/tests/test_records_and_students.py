from rest_framework.test import APIClient

from training.models import Assignment, Student


def test_student_codes_are_unique_per_cohort(api):
    r = api.post("/api/cohorts/103/students/", {"code": "C103-01", "full_name": "Test Person"}, format="json")
    assert r.status_code == 400 and "already used" in r.json()["error"]
    r = api.post("/api/cohorts/103/students/", {"code": "C103-99", "full_name": "Test Person"}, format="json")
    assert r.status_code == 201


def test_attendance_grid_and_marking(api):
    grid = api.get("/api/cohorts/101/attendance/", {"week": 1}).json()
    lesson, student = grid["lessons"][0]["id"], grid["students"][0]["id"]
    r = api.post(
        "/api/cohorts/101/attendance/", {"lesson": lesson, "student": student, "present": False}, format="json"
    )
    assert r.status_code == 200 and r.json()["present"] is False


def test_grade_cannot_exceed_max_points(api):
    a = Assignment.objects.filter(cohort__number=101).first()
    s = Student.objects.filter(cohort__number=101).first()
    assert (
        api.post(
            f"/api/cohorts/101/assignments/{a.id}/grade/", {"student": s.id, "points": 99}, format="json"
        ).status_code
        == 400
    )
    r = api.post(f"/api/cohorts/101/assignments/{a.id}/grade/", {"student": s.id, "points": 7}, format="json")
    assert r.json()["status"] == "graded"


def test_catalogue_rejects_duplicates(api):
    courses = api.get("/api/courses/").json()["courses"]
    r = api.put(
        "/api/courses/",
        {"courses": courses + [{"name": courses[0]["name"], "weeks": 2, "day_split": "none", "split_weeks": []}]},
        format="json",
    )
    assert r.status_code == 400


def test_weekly_report_and_compare(api):
    report = api.get("/api/cohorts/102/reports/weekly/", {"week": 5}).json()
    assert report["survey"]["invited"] == 17 and report["lessons"]
    assert {c["number"] for c in api.get("/api/cohorts/compare/").json()["cohorts"]} == {101, 102, 103}


def test_student_api_flow():
    client = APIClient()
    student = Student.objects.filter(cohort__number=102, dropped=False).first()
    r = client.post("/api/student/auth/mock-sign-in/", {"email": student.email}, format="json")
    assert r.status_code == 200 and r.json()["cohorts"] == [102]
    client.credentials(HTTP_AUTHORIZATION=f"Token {r.json()['token']}")
    view = client.get("/api/student/cohorts/102/").json()
    assert len(view["weeks"]) == 6
    assignment = Assignment.objects.filter(cohort__number=102, week=6).first()
    r = client.post(
        "/api/student/cohorts/102/submissions/",
        {"assignment": assignment.id, "link": "https://example.com/work"},
        format="json",
    )
    assert r.status_code == 200
    lesson = view["weeks"][0]["lessons"][0]["id"]
    assert (
        client.post(
            "/api/student/cohorts/102/lesson-feedback/", {"lesson": lesson, "overall": 5}, format="json"
        ).status_code
        == 200
    )
    assert client.get("/api/student/cohorts/101/").status_code == 403
    assert client.get("/api/cohorts/").status_code == 403
