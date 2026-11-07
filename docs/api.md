# API reference

Interactive documentation runs at **`/api/docs/`** (Swagger UI) and **`/api/redoc/`**. The raw schema is at `/api/schema/` (OpenAPI 3).

- **Authentication.** `POST /api/auth/login/` returns a token. Send it as `Authorization: Token <token>`.
- **Errors.** Every error has the shape `{"error": "<message>"}`. Validation errors also include `fields`.
- **Status codes.** `400` means the request was rejected by validation or a business rule. `409` means an integration is not connected or has expired.

## Training office (staff token)

| Method | Path | Purpose |
|---|---|---|
| POST / POST / GET | `/api/auth/login/` · `logout/` · `me/` | Sign in, sign out, current user |
| GET, POST | `/api/cohorts/` | Cohort cards (status, current week, Classroom state); create a cohort |
| GET, PATCH | `/api/cohorts/{n}/` | One cohort with attendance, submission, grade and satisfaction rates |
| GET | `/api/cohorts/compare/` | All cohorts side by side |
| PATCH | `/api/cohorts/{n}/weeks/{w}/` | A week's topics per course and a note |
| GET | `/api/cohorts/{n}/reports/weekly/?week=` | Lessons and attendance, homework, survey scores, mentoring, open action items |
| GET, PUT | `/api/courses/` | The course catalogue: weeks and Day 1 / Day 2 weeks |
| GET | `/api/recipients/?channel=email\|whatsapp` | Students reachable on a channel, grouped by cohort |
| GET, PUT | `/api/cohorts/{n}/agenda/?week=&kind=` | Saved agenda or a draft (`kind`: week, midterm, final, career) |
| GET | `/api/cohorts/{n}/agenda/pdf/?week=&kind=` | The saved agenda as a PDF |
| POST | `/api/cohorts/{n}/agenda/send/` | `{week, kind, channel, student_ids \| test_to}` |
| GET, PUT | `/api/cohorts/{n}/survey/?week=` | Saved survey or a draft, with scales, suggestions and results |
| POST | `/api/cohorts/{n}/survey/send/` | Personal links to `student_ids`, or the preview link to `test_to` |
| GET | `/api/cohorts/{n}/gradebook/?week=` | Students × assignments: status, points, %, late flag, link |
| GET | `/api/classroom/classes/` | The connected account's classes grouped by cohort |
| POST | `/api/classroom/import/` | `{number}`: bring a Classroom cohort onto the site |
| POST | `/api/cohorts/{n}/classroom/sync/` | `{add_unmatched?}`: sync now |
| GET | `/api/library/?course=&cohort=` | Courses and the chosen course's Classroom materials |
| POST | `/api/library/send/` | `{course, cohort, material_ids, student_ids \| test_to}` |
| GET | `/api/integrations/` | Mailbox, Classroom and WhatsApp connection state |
| POST | `/api/integrations/{mail\|classroom}/connect/` | Returns the URL of the (mock) consent screen |
| POST | `/api/integrations/{mail\|classroom}/disconnect/` | Remove a connection |

### Records (CRUD, nested under a cohort)
`/api/cohorts/{n}/students/`, `lessons/`, `assignments/`, `materials/`, `recordings/`, `mentoring/` and `action-items/` each have a list/create route and a `{id}/` route for read, update and delete. Also:

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/api/cohorts/{n}/attendance/?week=` | The attendance grid; mark `{lesson, student, present}` |
| POST | `/api/cohorts/{n}/assignments/{id}/grade/` | `{student, points?, submitted?, feedback?}` (entered on the site, so Classroom never overwrites it) |
| GET | `/api/cohorts/{n}/lesson-feedback/` | Students' 1–5 lesson ratings |

## Students (student token)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/student/auth/mock-sign-in/` | `{email}`: demo sign-in (mock mode only) |
| GET / POST | `/api/student/me/` · `logout/` | The student's cohorts, sign out |
| GET | `/api/student/cohorts/{n}/` | Week by week: topics, materials, recordings, assignments with own status, lessons |
| POST | `/api/student/cohorts/{n}/submissions/` | Hand in work: `{assignment, link \| text \| file}` |
| POST | `/api/student/cohorts/{n}/lesson-feedback/` | Rate a lesson: `{lesson, overall, trainer?, materials?, comment?}` |

## Public pages (no login)

| Path | Purpose |
|---|---|
| `/s/{token}/` | A student's personal survey link (GET form, POST answers once) |
| `/s/preview/{signature}/` | Staff preview, valid for 14 days; answers are never saved |
| `/oauth/mock/authorize/?state=` | Mock OAuth consent screen (signed state, valid for 10 minutes) |
