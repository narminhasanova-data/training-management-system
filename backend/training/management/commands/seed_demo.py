"""Load the fictional demo data.

    python manage.py seed_demo             # load (adds what is missing)
    python manage.py seed_demo --reset     # wipe training data first, then load
    python manage.py seed_demo --if-empty  # do nothing when cohorts already exist (docker-compose start-up)

Creates the course catalogue, cohorts 101 (finished), 102 (running, week 6) and 103 (upcoming) with
students, lessons, attendance, homework and grades, mentoring, action items, two answered surveys and
a sent agenda; connects the mock mailbox and the mock Classroom account and syncs cohort 102 from the
fake Classroom (cohort 104 stays in Classroom, ready to be imported from the Classroom page).
"""

import os
import random
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.permissions import STAFF_GROUP
from integrations import accounts
from integrations.models import ConnectedAccount, OutboundMessage
from training.demo import data as demo
from training.models import (
    ActionItem,
    Agenda,
    Assignment,
    Attendance,
    ClassroomClass,
    Cohort,
    Course,
    LearningMaterial,
    Lesson,
    LessonFeedback,
    LessonRecording,
    MentoringSession,
    Student,
    Submission,
    Survey,
    SurveyInvite,
    SurveyResponse,
    Week,
)
from training.services import agenda as agenda_service
from training.services import classroom
from training.services import surveys as survey_service

DEFAULT_PASSWORD = "coordinator-demo"
COMMENTS = [
    "Clear explanations, thank you!",
    "The pace was good, but the last exercise needed more time.",
    "More real-world examples would help.",
    "Could we get the slides before class?",
    "The practice session was the most useful part of the week.",
    "Some dataset links did not open on Saturday morning.",
]
NOTES = ["Great week overall.", "Recordings a little sooner would help.", "The room was cold on Sunday."]
ACTIONS = [
    ("Slides arrive too late to prepare.", "Publish slides by Friday 18:00.", "Done from week 4.", True),
    ("Exercises in SQL week 2 were too long.", "Split the exercise into two parts.", "", False),
    ("Students asked for more mentoring slots.", "Add a Wednesday evening slot.", "", False),
]


class Command(BaseCommand):
    help = "Load fictional demo data (cohorts, students, grades, surveys, agendas, mock connections)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing training data first.")
        parser.add_argument("--if-empty", action="store_true", help="Skip when cohorts already exist.")
        parser.add_argument("--no-connect", action="store_true", help="Leave the mock accounts disconnected.")

    def handle(self, *args, reset=False, if_empty=False, no_connect=False, **options):
        if if_empty and Cohort.objects.exists():
            self.stdout.write("Cohorts exist; demo data not loaded.")
            return
        self.rng = random.Random(2026)
        self.today = timezone.localdate()
        with transaction.atomic():
            if reset:
                for model in (Cohort, Course, ConnectedAccount, OutboundMessage):
                    model.objects.all().delete()
            password = self.staff_user()
            self.catalogue()
            cohorts = {n: self.cohort(n, status, offset) for n, status, offset in demo.COHORTS}
            for cohort in cohorts.values():
                self.lessons(cohort)
            self.homework(cohorts[101])
            for n in (101, 102):
                self.mentoring(cohorts[n])
                self.actions(cohorts[n])
            if not no_connect:
                self.connect()
                self.link_classroom(cohorts[102])
            self.extras(cohorts[102])
            self.survey(cohorts[101], 10)
            self.survey(cohorts[101], 11)
            self.survey(cohorts[102], cohorts[102].current_week - 1)
            self.agenda(cohorts[102], cohorts[102].current_week - 1)
        self.stdout.write(self.style.SUCCESS("Demo data loaded."))
        self.stdout.write(f"Sign in as 'coordinator' with password '{password}'.")

    # ------------------------------------------------------------------ people and catalogue
    def staff_user(self) -> str:
        password = os.environ.get("DEMO_PASSWORD") or DEFAULT_PASSWORD
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username="coordinator",
            defaults={"first_name": "Training", "last_name": "Coordinator", "email": "coordinator@academy.example"},
        )
        if created or os.environ.get("DEMO_PASSWORD"):
            user.set_password(password)
        user.is_staff = True
        user.save()
        user.groups.add(Group.objects.get_or_create(name=STAFF_GROUP)[0])
        return password

    def catalogue(self):
        for position, (name, weeks, split, split_weeks) in enumerate(demo.CATALOGUE):
            Course.objects.update_or_create(
                name=name,
                defaults={"weeks": weeks, "day_split": split, "split_weeks": split_weeks, "position": position},
            )

    def cohort(self, number, status, offset) -> Cohort:
        cohort, _ = Cohort.objects.update_or_create(
            number=number,
            defaults={
                "name": f"Cohort {number}",
                "status": status,
                "source": Cohort.Source.SEED,
                "weeks_total": 12,
                "start_date": demo.cohort_start(offset, self.today),
            },
        )
        courses = sorted({c for w in range(1, 13) for _, c, _ in demo.plan(w)})
        for p in demo.roster(number):
            Student.objects.update_or_create(
                cohort=cohort,
                code=p["code"],
                defaults={"full_name": p["full_name"], "email": p["email"], "phone": p["phone"], "courses": courses},
            )
        if number in (101, 102):  # one student left each running / finished cohort
            Student.objects.filter(cohort=cohort, code=f"C{number}-{len(demo.roster(number)):02d}").update(dropped=True)
        for week in range(1, 13):
            topics = {course: demo.topics_for(course, cw) for _, course, cw in demo.plan(week)}
            Week.objects.update_or_create(cohort=cohort, number=week, defaults={"topics": topics})
        return cohort

    # ------------------------------------------------------------------ teaching
    def lessons(self, cohort: Cohort):
        if cohort.lessons.exists():
            return
        students = list(cohort.students.all())
        for week in range(1, 13):
            day1 = cohort.start_date + timedelta(weeks=week - 1)
            for track, course, _cw in demo.plan(week):
                for day, kind in ((day1, Lesson.Kind.LECTURE), (day1 + timedelta(days=1), Lesson.Kind.PRACTICE)):
                    lesson = Lesson.objects.create(
                        cohort=cohort,
                        week=week,
                        course=course,
                        kind=kind,
                        title=f"{course} · {'lecture' if kind == 'lecture' else 'practice'}",
                        date=day,
                        start_time=demo.LESSON_TIMES[(track, 1 if kind == "lecture" else 2)],
                        trainer=demo.TRAINERS[course],
                        mentor=demo.MENTORS[(week + (track == "B")) % len(demo.MENTORS)],
                        held=day <= self.today,
                    )
                    if lesson.held:
                        Attendance.objects.bulk_create(
                            Attendance(
                                lesson=lesson,
                                student=s,
                                present=not (s.dropped and week > 4) and self.rng.random() < 0.91,
                            )
                            for s in students
                        )

    def homework(self, cohort: Cohort):
        """Cohort 101 keeps its homework on the site (cohort 102's comes from Classroom)."""
        if cohort.assignments.exists():
            return
        students = list(cohort.students.all())
        for week in range(1, 13):
            day1 = cohort.start_date + timedelta(weeks=week - 1)
            due = timezone.make_aware(datetime.combine(day1 + timedelta(days=4), time(23, 59)))
            for _, course, cw in demo.plan(week):
                topics = demo.topics_for(course, cw)
                works = [(f"Homework {cw}: {topics[1] if len(topics) > 1 else course}", 10)]
                if course == "Python for Data" and cw % 3 == 0:
                    works.append((f"Mini project {cw // 3}", 20))
                for title, points in works:
                    a = Assignment.objects.create(
                        cohort=cohort,
                        week=week,
                        course=course,
                        title=title,
                        max_points=points,
                        due_at=due,
                        kind=Assignment.Kind.PROJECT if points > 10 else Assignment.Kind.HOMEWORK,
                    )
                    for s in students:
                        if (s.dropped and week > 4) or self.rng.random() > 0.9:
                            continue
                        late = self.rng.random() < 0.08
                        Submission.objects.create(
                            assignment=a,
                            student=s,
                            source=Submission.Source.STAFF,
                            submitted_at=due + timedelta(hours=10 if late else -20),
                            late=late,
                            points=round(points * self.rng.uniform(0.5, 1.0), 1),
                            graded_at=due + timedelta(days=3),
                            graded_by="Training Coordinator",
                        )

    def mentoring(self, cohort: Cohort):
        if cohort.mentoring.exists():
            return
        students = list(cohort.students.filter(dropped=False))
        for week in range(1, min(cohort.current_week, 12) + 1):
            for s in self.rng.sample(students, k=min(4, len(students))):
                MentoringSession.objects.create(
                    cohort=cohort,
                    student=s,
                    mentor=self.rng.choice(demo.MENTORS),
                    date=cohort.start_date + timedelta(weeks=week - 1, days=3),
                    minutes=self.rng.choice([30, 45, 60]),
                    notes="Reviewed homework and next steps.",
                    rating=self.rng.choice([4, 5, 5]),
                )

    def actions(self, cohort: Cohort):
        if cohort.action_items.exists():
            return
        for i, (feedback, action, result, done) in enumerate(ACTIONS):
            ActionItem.objects.create(
                cohort=cohort, week=2 + i, feedback=feedback, action=action, result=result, done=done
            )

    def extras(self, cohort: Cohort):
        """Staff-published materials, recordings and a few lesson ratings (student API data)."""
        if cohort.learning_materials.exists():
            return
        for week in range(1, cohort.current_week):
            for _, course, cw in demo.plan(week):
                LearningMaterial.objects.create(
                    cohort=cohort,
                    week=week,
                    course=course,
                    title=f"{course}: week {cw} cheat sheet",
                    url=f"https://example.com/cheatsheets/{course.lower().replace(' ', '-')}-{cw}.pdf",
                )
                LessonRecording.objects.create(
                    cohort=cohort,
                    week=week,
                    course=course,
                    title=f"{course} lecture, week {week}",
                    url=f"https://video.example/recordings/{cohort.number}-{week}-{course.lower().replace(' ', '-')}",
                    duration_min=self.rng.choice([85, 90, 95]),
                    recorded_on=cohort.start_date + timedelta(weeks=week - 1),
                )
        students = list(cohort.students.filter(dropped=False))
        for lesson in cohort.lessons.filter(held=True, kind=Lesson.Kind.LECTURE):
            for s in self.rng.sample(students, k=min(5, len(students))):
                LessonFeedback.objects.get_or_create(
                    lesson=lesson,
                    student=s,
                    defaults={
                        "overall": self.rng.choice([3, 4, 4, 5, 5]),
                        "trainer": self.rng.choice([4, 5, 5]),
                        "materials": self.rng.choice([3, 4, 5]),
                    },
                )

    # ------------------------------------------------------------------ integrations
    def connect(self):
        for purpose in (ConnectedAccount.Purpose.MAIL, ConnectedAccount.Purpose.CLASSROOM):
            if not accounts.account(purpose):
                accounts.complete(
                    {"purpose": purpose, "by": "Training Coordinator"},
                    "coordinator@academy.example",
                    accounts.SCOPES[purpose],
                )

    def link_classroom(self, cohort: Cohort):
        api, _ = classroom.provider()
        for c in api.list_courses():
            info = classroom.describe(c)
            if info and info["number"] == cohort.number:
                ClassroomClass.objects.update_or_create(
                    external_id=c["id"],
                    defaults={
                        "cohort": cohort,
                        "name": c["name"],
                        "state": c.get("courseState", ""),
                        "course": info["course"],
                    },
                )
        classroom.sync(cohort)

    # ------------------------------------------------------------------ surveys and agendas
    def _answer(self, levels, agree):
        return self.rng.choices(levels, weights=[1, 2, 5, 9, 7])[0], self.rng.choices(agree, weights=[1, 1, 3, 9, 8])[0]

    def survey(self, cohort: Cohort, week: int):
        if week < 1 or Survey.objects.filter(cohort=cohort, week=week).exists():
            return
        body = survey_service.draft(cohort, week)
        survey = survey_service.save(cohort, week, body, "Training Coordinator")
        sent = timezone.make_aware(datetime.combine(cohort.start_date + timedelta(weeks=week - 1, days=1), time(17, 0)))
        for student in cohort.students.filter(dropped=False):
            invite = SurveyInvite.objects.create(survey=survey, student=student, channels="email", sent_at=sent)
            if self.rng.random() > 0.72:
                continue
            answers = {"blocks": [], "trainers": {}, "mentors": {}, "materials": {}, "notes": ""}
            for _ in survey.blocks:
                level, _a = self._answer(survey_service.UNDERSTANDING, survey_service.AGREEMENT)
                comment = self.rng.choice(COMMENTS) if self.rng.random() < 0.3 else ""
                answers["blocks"].append({"level": level, "comment": comment})
            for grid in ("trainers", "materials"):
                for row in getattr(survey, grid):
                    answers[grid][row] = self._answer(survey_service.UNDERSTANDING, survey_service.AGREEMENT)[1]
            for row in survey.mentors:
                answers["mentors"][row] = (
                    survey_service.NOT_APPLICABLE
                    if self.rng.random() < 0.3
                    else self._answer(survey_service.UNDERSTANDING, survey_service.AGREEMENT)[1]
                )
            if self.rng.random() < 0.25:
                answers["notes"] = self.rng.choice(NOTES)
            response = SurveyResponse.objects.create(
                survey=survey, student=student, invite=invite, answers=answers, **survey_service.scores(answers)
            )
            SurveyResponse.objects.filter(pk=response.pk).update(submitted_at=sent + timedelta(hours=3))

    def agenda(self, cohort: Cohort, week: int):
        if week < 1 or Agenda.objects.filter(cohort=cohort, week=week, kind="week").exists():
            return
        saved = agenda_service.save(
            cohort, week, "week", agenda_service.draft(cohort, week, "week"), "Training Coordinator"
        )
        saved.emailed_at = timezone.make_aware(
            datetime.combine(cohort.start_date + timedelta(weeks=week - 1, days=-2), time(12, 0))
        )
        saved.emailed_count = cohort.students.filter(dropped=False).count()
        saved.save(update_fields=["emailed_at", "emailed_count"])
