from django.core import mail

from integrations import accounts
from integrations.models import OutboundMessage


def test_week_draft_comes_from_lessons_and_topics(api):
    d = api.get("/api/cohorts/102/agenda/", {"week": 6, "kind": "week"}).json()
    assert d["saved"] is False
    class_days = [day for day in d["days"] if not day["free"]]
    assert len(class_days) == 2
    assert [t["course"] for t in class_days[0]["tracks"]] == ["SQL Foundations", "Python for Data"]
    first_topics = [r["text"] for r in class_days[0]["rows"] if r["track"] == 0]
    assert first_topics[0] == "Common table expressions"
    assert class_days[1]["rows"][0]["text"] == "Guided practice"  # day 2 is practice
    assert "heading" in d["days"][2]  # the optional extra section


def test_exam_drafts_have_free_rows(api):
    for kind in ("midterm", "final", "career"):
        days = api.get("/api/cohorts/102/agenda/", {"week": 6, "kind": kind}).json()["days"]
        assert days and all(day["free"] for day in days)


def test_save_validates_and_stores(api):
    days = api.get("/api/cohorts/102/agenda/", {"week": 6, "kind": "week"}).json()["days"]
    days[0]["rows"][0]["text"] = "Edited topic"
    r = api.put("/api/cohorts/102/agenda/", {"week": 6, "kind": "week", "days": days}, format="json")
    assert r.status_code == 200 and r.json()["saved"] and r.json()["days"][0]["rows"][0]["text"] == "Edited topic"
    days[0]["date"] = "2026-13-40"
    assert (
        api.put("/api/cohorts/102/agenda/", {"week": 6, "kind": "week", "days": days}, format="json").status_code == 400
    )
    days[0]["date"] = ""
    days[0]["tracks"][0]["color"] = "neon"
    assert (
        api.put("/api/cohorts/102/agenda/", {"week": 6, "kind": "week", "days": days}, format="json").status_code == 400
    )


def _saved(api, week=6, kind="week"):
    days = api.get("/api/cohorts/102/agenda/", {"week": week, "kind": kind}).json()["days"]
    api.put("/api/cohorts/102/agenda/", {"week": week, "kind": kind, "days": days}, format="json")


def test_pdf_requires_a_saved_agenda(api):
    assert api.get("/api/cohorts/102/agenda/pdf/", {"week": 7, "kind": "week"}).status_code == 404
    _saved(api)
    r = api.get("/api/cohorts/102/agenda/pdf/", {"week": 6, "kind": "week"})
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf" and r.content.startswith(b"%PDF")


def test_email_goes_to_chosen_students_with_the_pdf(api, cohort102):
    _saved(api)
    ids = list(cohort102.students.filter(dropped=False).values_list("id", flat=True)[:3])
    r = api.post(
        "/api/cohorts/102/agenda/send/",
        {"week": 6, "kind": "week", "channel": "email", "student_ids": ids},
        format="json",
    )
    assert r.status_code == 200 and r.json()["sent"] == 3
    assert len(mail.outbox) == 3
    assert mail.outbox[0].attachments[0][0] == "agenda-cohort-102-week-6.pdf"
    assert r.json()["agenda"]["emailed_count"] == 3


def test_test_send_and_whatsapp_mock(api, cohort102):
    _saved(api)
    r = api.post(
        "/api/cohorts/102/agenda/send/",
        {"week": 6, "kind": "week", "channel": "email", "test_to": "me@example.com"},
        format="json",
    )
    assert r.json()["sent"] == 1 and mail.outbox[0].subject.startswith("[Test]")
    ids = list(cohort102.students.filter(dropped=False).values_list("id", flat=True)[:2])
    r = api.post(
        "/api/cohorts/102/agenda/send/",
        {"week": 6, "kind": "week", "channel": "whatsapp", "student_ids": ids},
        format="json",
    )
    assert r.json()["sent"] == 2
    messages = OutboundMessage.objects.filter(channel="whatsapp", context="agenda:102:6:week")
    assert messages.count() == 2 and all(m.status == "simulated" for m in messages)


def test_sending_needs_a_live_mailbox(api, cohort102):
    _saved(api)
    accounts.expire("mail")
    ids = list(cohort102.students.values_list("id", flat=True)[:1])
    r = api.post(
        "/api/cohorts/102/agenda/send/",
        {"week": 6, "kind": "week", "channel": "email", "student_ids": ids},
        format="json",
    )
    assert r.status_code == 400 and "mailbox" in r.json()["error"]


def test_send_requires_students_or_a_test_address(api):
    _saved(api)
    r = api.post("/api/cohorts/102/agenda/send/", {"week": 6, "kind": "week", "channel": "email"}, format="json")
    assert r.status_code == 400


def test_pdf_escapes_markup_in_user_text(api):
    days = api.get("/api/cohorts/102/agenda/", {"week": 6, "kind": "week"}).json()["days"]
    days[0]["rows"][0]["text"] = "Q&A <b>bold?</b>"
    api.put("/api/cohorts/102/agenda/", {"week": 6, "kind": "week", "days": days}, format="json")
    r = api.get("/api/cohorts/102/agenda/pdf/", {"week": 6, "kind": "week"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
