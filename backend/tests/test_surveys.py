from django.core import mail
from django.test import Client

from training.models import Survey, SurveyInvite, SurveyResponse
from training.services import surveys


def test_draft_splits_day_1_and_day_2_from_the_catalogue(api):
    d = api.get("/api/cohorts/102/survey/", {"week": 6}).json()
    blocks = [(b["course"], b["day"]) for b in d["blocks"]]
    assert blocks == [("SQL Foundations", 0), ("Python for Data", 1), ("Python for Data", 2)]
    assert d["trainers"] == ["Omar Haddad", "Lucas Moreau"]
    assert d["scales"]["understanding"][0] == "Not at all"


def test_save_rejects_a_survey_without_title(api):
    body = {"week": 6, "title": "", "blocks": [], "trainers": [], "mentors": [], "materials": []}
    assert api.put("/api/cohorts/102/survey/", body, format="json").status_code == 400


def _save(api, week=6):
    d = api.get("/api/cohorts/102/survey/", {"week": week}).json()
    body = {k: d[k] for k in ("title", "blocks", "trainers", "mentors", "materials", "grid_weeks")}
    body["grid_weeks"] = {"mentors": week - 1}
    r = api.put("/api/cohorts/102/survey/", {"week": week, **body}, format="json")
    assert r.status_code == 200
    return Survey.objects.get(cohort__number=102, week=week)


def _answers(survey):
    data = {}
    for q in surveys.questions(survey):
        if q["kind"] == "choice":
            data[q["id"]] = q["options"][3]
        elif q["kind"] == "grid":
            for i, _ in enumerate(q["rows"]):
                data[f"{q['id']}:{i}"] = q["columns"][4]
    data["b0c"] = "Great pace"
    return data


def test_grid_week_changes_the_question(api):
    survey = _save(api)
    mentors = next(q for q in surveys.questions(survey) if q["id"] == "mentors")
    assert mentors["text"].startswith("Week 5:")


def test_send_creates_personal_links(api, cohort102):
    survey = _save(api)
    ids = list(cohort102.students.filter(dropped=False).values_list("id", flat=True)[:4])
    r = api.post("/api/cohorts/102/survey/send/", {"week": 6, "channel": "email", "student_ids": ids}, format="json")
    assert r.json()["sent"] == 4
    invites = SurveyInvite.objects.filter(survey=survey)
    assert invites.count() == 4 and all(i.channels == "email" and i.sent_at for i in invites)
    assert invites[0].token in "".join(m.body for m in mail.outbox)
    assert r.json()["survey"]["results"]["invited"] == 4


def test_public_form_validates_and_accepts_one_answer(api, cohort102):
    survey = _save(api)
    invite = SurveyInvite.objects.create(survey=survey, student=cohort102.students.first())
    client = Client(enforce_csrf_checks=False)
    assert client.get(f"/s/{invite.token}/").status_code == 200
    r = client.post(f"/s/{invite.token}/", {})
    assert r.status_code == 400 and b"highlighted question" in r.content
    r = client.post(f"/s/{invite.token}/", _answers(survey))
    assert r.status_code == 200 and b"Thank you" in r.content
    response = SurveyResponse.objects.get(invite=invite)
    assert response.understanding == 4 and response.trainer_score == 5
    assert response.answers["blocks"][0]["comment"] == "Great pace"
    r = client.post(f"/s/{invite.token}/", _answers(survey))
    assert b"already answered" in r.content and SurveyResponse.objects.filter(invite=invite).count() == 1


def test_preview_never_saves(api):
    survey = _save(api)
    path = surveys.preview_url(survey).split("/s/", 1)[1]
    client = Client()
    assert client.get("/s/" + path).status_code == 200
    r = client.post("/s/" + path, _answers(survey))
    assert b"Preview complete" in r.content and not survey.responses.exists()
    assert client.get("/s/preview/forged/").status_code == 404


def test_results_count_answers(api):
    results = api.get("/api/cohorts/102/survey/", {"week": 5}).json()["results"]
    assert results["invited"] == 17
    assert results["answered"] == sum(1 for p in results["people"] if p["answered_at"])
    block = results["blocks"][0]
    assert sum(block["counts"]) == results["answered"]
    assert 1 <= block["average"] <= 5


def test_scores_ignore_not_applicable_mentors():
    answers = {
        "blocks": [{"level": "Completely"}],
        "trainers": {"A": "Agree"},
        "mentors": {"M": surveys.NOT_APPLICABLE, "N": "Strongly agree"},
        "materials": {},
    }
    assert surveys.scores(answers) == {
        "understanding": 5,
        "trainer_score": 4,
        "mentor_score": 5,
        "materials_score": None,
    }
