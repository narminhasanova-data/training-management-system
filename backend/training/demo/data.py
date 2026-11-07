"""Fictional demo data shared by `seed_demo` and the fake Google Classroom provider.

Every person here is invented. Emails use example.com / academy.example (reserved domains, never
delivered) and phone numbers use +1 202-555-01xx, a range reserved for fiction. Generation is
deterministic (seeded random) so the seed and the fake Classroom agree on who is in which cohort.
"""

import random
from datetime import UTC, date, datetime, time, timedelta

FIRST_NAMES = [
    "Ada",
    "Bruno",
    "Chiara",
    "Dmitri",
    "Esme",
    "Farid",
    "Greta",
    "Hugo",
    "Ines",
    "Jamal",
    "Kira",
    "Leon",
    "Maya",
    "Nikolai",
    "Olivia",
    "Pavel",
    "Quinn",
    "Rosa",
    "Samir",
    "Tara",
    "Umar",
    "Vera",
    "Wen",
    "Ximena",
    "Yusuf",
    "Zara",
    "Aiko",
    "Basil",
    "Celine",
    "Dario",
]
LAST_NAMES = [
    "Abbott",
    "Brennan",
    "Castillo",
    "Draper",
    "Eklund",
    "Fontaine",
    "Garrido",
    "Holm",
    "Ivers",
    "Jansen",
    "Keller",
    "Lindgren",
    "Marsh",
    "Novak",
    "Ortega",
    "Pryce",
    "Quintero",
    "Rask",
    "Sato",
    "Thorne",
    "Ueda",
    "Valdez",
    "Whitlow",
    "Xu",
    "Yilmaz",
    "Zeller",
    "Ambrose",
    "Becker",
    "Cordova",
    "Dunmore",
]

# Catalogue: (name, weeks, day split, split weeks).
CATALOGUE = [
    ("Spreadsheet Analytics", 3, "none", []),
    ("SQL Foundations", 4, "some", [4]),
    ("BI Dashboards", 3, "none", []),
    ("Data Storytelling", 2, "none", []),
    ("Python for Data", 9, "all", []),
    ("Big Data Tools", 3, "some", [3]),
    ("Statistics", 4, "none", []),
    ("Machine Learning", 4, "some", [3, 4]),
]

# Two courses run in parallel every week: track A (analytics) and track B (programming).
TRACK_A = [("Spreadsheet Analytics", 3), ("SQL Foundations", 4), ("BI Dashboards", 3), ("Data Storytelling", 2)]
TRACK_B = [("Python for Data", 9), ("Big Data Tools", 3)]

TRAINERS = {
    "Spreadsheet Analytics": "Nora Lindqvist",
    "SQL Foundations": "Omar Haddad",
    "BI Dashboards": "Priya Raman",
    "Data Storytelling": "Priya Raman",
    "Python for Data": "Lucas Moreau",
    "Big Data Tools": "Elif Kaya",
    "Statistics": "Daniel Okafor",
    "Machine Learning": "Daniel Okafor",
}
MENTORS = ["Hana Suzuki", "Mateo Rossi", "Amara Diallo", "Jonas Berg"]

TOPICS = {
    "Spreadsheet Analytics": [
        ["Workbook structure and clean data", "Lookup functions", "Conditional logic"],
        ["Pivot tables", "Charts that answer a question", "Dynamic ranges"],
        ["What-if analysis", "Building a small dashboard", "Review and quiz"],
    ],
    "SQL Foundations": [
        ["SELECT, WHERE and ORDER BY", "Aggregates and GROUP BY", "Filtering groups"],
        ["Inner and outer joins", "Join pitfalls", "Subqueries"],
        ["Common table expressions", "Window functions", "Ranking queries"],
        ["Query performance basics", "Case study: sales database", "Review"],
    ],
    "BI Dashboards": [
        ["Data modelling for reports", "Relationships", "First report page"],
        ["Measures and calculations", "Time intelligence", "Filters and slicers"],
        ["Dashboard design", "Publishing and sharing", "Capstone dashboard"],
    ],
    "Data Storytelling": [
        ["Finding the message", "Choosing the right chart", "Annotations"],
        ["Presenting to stakeholders", "Peer review", "Final presentations"],
    ],
    "Python for Data": [
        ["Python syntax and types", "Control flow", "Functions"],
        ["Lists, dicts and comprehensions", "Working with files", "Error handling"],
        ["NumPy arrays", "Vectorised operations", "Mini exercise"],
        ["pandas Series and DataFrames", "Selecting and filtering", "Missing values"],
        ["Grouping and aggregation", "Merging datasets", "Reshaping"],
        ["Visualisation with matplotlib", "Seaborn basics", "Exploratory analysis"],
        ["APIs and JSON", "Web data", "Mini project kickoff"],
        ["Intro to scikit-learn", "Train/test split", "Linear regression"],
        ["Classification basics", "Model evaluation", "Project presentations"],
    ],
    "Big Data Tools": [
        ["Distributed computing ideas", "Spark DataFrames", "Lazy evaluation"],
        ["Spark SQL", "Partitioning", "Performance tips"],
        ["Pipelines end to end", "Cloud storage", "Course wrap-up"],
    ],
}

# (number, status, start offset in weeks from this week's Saturday)
COHORTS = [(101, "finished", -20), (102, "running", -5), (103, "upcoming", 3)]
CLASSROOM_ONLY_COHORT = 104  # exists only in the fake Classroom, to demonstrate importing
ROSTER_SIZE = {101: 20, 102: 18, 103: 16, 104: 12}

LESSON_TIMES = {("A", 1): time(10, 0), ("B", 1): time(13, 30), ("A", 2): time(10, 0), ("B", 2): time(13, 30)}


def this_saturday(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=(today.weekday() - 5) % 7)


def cohort_start(offset_weeks: int, today: date | None = None) -> date:
    return this_saturday(today) + timedelta(weeks=offset_weeks)


def plan(week: int) -> list[tuple[str, str, int]]:
    """[(track, course, week of that course)] taught in cohort week `week` (1-based)."""
    out = []
    for track, courses in (("A", TRACK_A), ("B", TRACK_B)):
        start = 1
        for course, weeks in courses:
            if start <= week < start + weeks:
                out.append((track, course, week - start + 1))
                break
            start += weeks
    return out


def topics_for(course: str, course_week: int) -> list[str]:
    weeks = TOPICS.get(course, [])
    return list(weeks[course_week - 1]) if 0 < course_week <= len(weeks) else []


def roster(number: int) -> list[dict]:
    """Deterministic list of fictional students for a cohort."""
    rng = random.Random(number * 7919)
    pairs = [(f, la) for f in FIRST_NAMES for la in LAST_NAMES]
    rng.shuffle(pairs)
    people = []
    for i, (first, last) in enumerate(pairs[: ROSTER_SIZE.get(number, 15)], start=1):
        people.append(
            {
                "code": f"C{number}-{i:02d}",
                "full_name": f"{first} {last}",
                "email": f"{first}.{last}.{number}@example.com".lower(),
                "phone": f"+1 202 555 01{(number + i) % 100:02d}",
            }
        )
    return people


def trainer_email(name: str) -> str:
    return name.lower().replace(" ", ".") + "@academy.example"


# --------------------------------------------------------------------------- fake Classroom
def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _class_id(number: int, course: str) -> str:
    return f"c{number}-{course.lower().replace(' ', '-')}"


def classroom_dataset(today: date | None = None) -> dict:
    """Google-Classroom-shaped JSON for the fake provider: courses, rosters, topics, coursework,
    submissions and material posts. Cohort 102 mirrors the seeded running cohort; cohort 104
    exists only here; two classes fall outside the import rules (old cohort, no cohort number)."""
    today = today or date.today()
    data = {
        "courses": [],
        "students": {},
        "teachers": {},
        "topics": {},
        "coursework": {},
        "submissions": {},
        "materials": {},
    }
    now = datetime.combine(today, time(9, 0), tzinfo=UTC)

    def add_course(cid, name, state, created):
        data["courses"].append(
            {
                "id": cid,
                "name": name,
                "section": "",
                "courseState": state,
                "creationTime": _iso(created),
                "updateTime": _iso(now),
                "alternateLink": f"https://classroom.example/c/{cid}",
            }
        )
        for key in ("students", "teachers", "topics", "coursework", "materials"):
            data[key][cid] = []

    def person(p):
        return {
            "userId": "u-" + p["email"].split("@")[0].replace(".", "-"),
            "profile": {"name": {"fullName": p["full_name"]}, "emailAddress": p["email"]},
        }

    cohorts = {102: (cohort_start(-5, today), "ACTIVE"), CLASSROOM_ONLY_COHORT: (cohort_start(1, today), "PROVISIONED")}
    for number, (start, state) in cohorts.items():
        current = max(0, min(12, (today - start).days // 7 + 1)) if today >= start else 0
        people = roster(number)
        if number == 102:  # two late joiners who are not on the site yet
            people = people + [
                {"full_name": "Iris Calloway", "email": "iris.calloway.102@example.com"},
                {"full_name": "Malik Osei", "email": "malik.osei.102@example.com"},
            ]
        courses_seen: dict[str, list[tuple[int, int]]] = {}
        for week in range(1, 13):
            for _track, course, cw in plan(week):
                courses_seen.setdefault(course, []).append((week, cw))
        for course, weeks in courses_seen.items():
            first_week = weeks[0][0]
            if number == CLASSROOM_ONLY_COHORT and first_week > 1:
                continue  # only the first courses of an upcoming cohort have classes yet
            if number == 102 and first_week > current:
                continue
            last_week = weeks[-1][0]
            class_state = state if number != 102 or last_week >= current else "ARCHIVED"
            cid = _class_id(number, course)
            add_course(
                cid,
                f"Cohort {number} · {course}",
                class_state,
                datetime.combine(start - timedelta(days=7), time(8, 0), tzinfo=UTC),
            )
            data["students"][cid] = [person(p) for p in people]
            trainer = TRAINERS[course]
            data["teachers"][cid] = [
                person({"full_name": trainer, "email": trainer_email(trainer)}),
                person({"full_name": "Training Office", "email": "coordinator@academy.example"}),
            ]
            rng = random.Random(f"{cid}")
            visible_weeks = [(w, cw) for w, cw in weeks if w <= max(current, 1)]
            for w, cw in visible_weeks:
                topic_id = f"{cid}-t{w}"
                data["topics"][cid].append({"topicId": topic_id, "name": f"Week {w}"})
                topics = topics_for(course, cw)
                day1 = start + timedelta(weeks=w - 1)
                posted = datetime.combine(day1, time(9, 0), tzinfo=UTC)
                # material posts: slides every week, extras on some weeks
                mats = [
                    {
                        "driveFile": {
                            "driveFile": {
                                "title": f"{course} week {cw} slides.pdf",
                                "alternateLink": f"https://example.com/files/{cid}/w{cw}-slides.pdf",
                            }
                        }
                    }
                ]
                if cw % 2 == 1:
                    mats.append(
                        {"link": {"title": "Further reading", "url": f"https://example.org/reading/{cid}/{cw}"}}
                    )
                if course == "Python for Data":
                    mats.append(
                        {
                            "youtubeVideo": {
                                "title": "Walkthrough recording",
                                "alternateLink": f"https://video.example/watch/{cid}-{cw}",
                            }
                        }
                    )
                data["materials"][cid].append(
                    {
                        "id": f"{cid}-m{cw}",
                        "title": f"Week {cw}: {topics[0] if topics else course}",
                        "description": " · ".join(topics),
                        "topicId": topic_id,
                        "materials": mats,
                        "state": "PUBLISHED",
                        "alternateLink": f"https://classroom.example/c/{cid}/m/{cw}",
                        "creationTime": _iso(posted),
                    }
                )
                if number == CLASSROOM_ONLY_COHORT:
                    continue  # no coursework yet for the upcoming cohort
                due = datetime.combine(day1 + timedelta(days=4), time(23, 59), tzinfo=UTC)
                works = [(f"{cid}-w{cw}", f"Homework {cw}: {topics[1] if len(topics) > 1 else course}", 10)]
                if course == "Python for Data" and cw % 3 == 0:
                    works.append((f"{cid}-p{cw}", f"Mini project {cw // 3}", 20))
                for work_id, title, points in works:
                    data["coursework"][cid].append(
                        {
                            "id": work_id,
                            "title": title,
                            "description": "Submit a link to your notebook or file.",
                            "topicId": topic_id,
                            "workType": "ASSIGNMENT",
                            "state": "PUBLISHED",
                            "maxPoints": points,
                            "dueDate": {"year": due.year, "month": due.month, "day": due.day},
                            "dueTime": {"hours": 23, "minutes": 59},
                            "creationTime": _iso(posted),
                            "updateTime": _iso(posted),
                            "alternateLink": f"https://classroom.example/c/{cid}/a/{work_id}",
                        }
                    )
                    subs = []
                    for p in data["students"][cid]:
                        roll = rng.random()
                        past = w < current
                        if (past and roll < 0.88) or (not past and roll < 0.4):
                            returned = past and rng.random() < 0.85
                            sub = {
                                "id": f"{work_id}-{p['userId']}",
                                "courseWorkId": work_id,
                                "userId": p["userId"],
                                "state": "RETURNED" if returned else "TURNED_IN",
                                "late": rng.random() < 0.1,
                                "updateTime": _iso(min(due, now)),
                                "alternateLink": f"https://classroom.example/s/{work_id}/{p['userId']}",
                                "assignmentSubmission": {
                                    "attachments": [
                                        {
                                            "link": {
                                                "url": f"https://example.com/work/{p['userId']}/{work_id}",
                                                "title": "My work",
                                            }
                                        }
                                    ]
                                },
                            }
                            if returned:
                                sub["assignedGrade"] = round(points * rng.uniform(0.55, 1.0), 1)
                            subs.append(sub)
                        else:
                            subs.append(
                                {
                                    "id": f"{work_id}-{p['userId']}",
                                    "courseWorkId": work_id,
                                    "userId": p["userId"],
                                    "state": "CREATED",
                                    "late": False,
                                    "updateTime": _iso(posted),
                                }
                            )
                    data["submissions"][(cid, work_id)] = subs

    # outside the import rules: an old cohort and a class without a cohort number
    for cid, name in (("c98-sql", "Cohort 98 · SQL Foundations"), ("staff-room", "Instructor resources")):
        add_course(cid, name, "ARCHIVED", now - timedelta(days=400))
    return data
