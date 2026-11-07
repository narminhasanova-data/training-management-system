from django.core import mail

from integrations.models import ConnectedAccount


def test_library_uses_the_fullest_set_and_flags_other_cohorts(api):
    api.post("/api/classroom/import/", {"number": 104}, format="json")
    d = api.get("/api/library/", {"course": "Python for Data", "cohort": 104}).json()
    assert d["source"]["number"] == 102 and d["materials_permission"]
    own = [i for i in d["items"] if not i["from_other_cohort"]]
    assert len(own) == 1 and own[0]["cohort"] == 104
    assert all(i["cohort"] == 102 for i in d["items"] if i["from_other_cohort"])


def test_library_send(api, cohort102):
    d = api.get("/api/library/", {"course": "SQL Foundations", "cohort": 102}).json()
    ids = [i["id"] for i in d["items"]]
    students = list(cohort102.students.filter(dropped=False).values_list("id", flat=True)[:2])
    body = {"course": "SQL Foundations", "cohort": 102, "material_ids": ids, "student_ids": students}
    r = api.post("/api/library/send/", body, format="json")
    assert r.json()["sent"] == 2 and "SQL Foundations materials" in mail.outbox[0].subject


def test_materials_need_their_permission(api):
    ConnectedAccount.objects.filter(purpose="classroom").update(scopes=["openid", "email"])
    assert api.get("/api/library/").json()["materials_permission"] is False


def test_gradebook_matrix(api):
    d = api.get("/api/cohorts/102/gradebook/").json()
    assert d["cohort"]["classroom_linked"] and d["weeks"] == [1, 2, 3, 4, 5, 6]
    person = d["people"][0]
    assert set(person["cells"]) == {str(a["id"]) for a in d["assignments"]}
    statuses = {c["status"] for p in d["people"] for c in p["cells"].values()}
    assert statuses == {"graded", "submitted", "missing"}
    week = api.get("/api/cohorts/102/gradebook/", {"week": 6}).json()
    assert {a["week"] for a in week["assignments"]} == {6}
