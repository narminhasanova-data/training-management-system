# Local development without Docker. Backend on :8000, web app on :5173 (proxies to the backend).
PY := backend/.venv/bin/python

.PHONY: setup backend frontend worker seed test lint

setup:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install
	cd backend && DJANGO_DEBUG=1 .venv/bin/python manage.py migrate && DJANGO_DEBUG=1 .venv/bin/python manage.py seed_demo

backend:
	cd backend && DJANGO_DEBUG=1 .venv/bin/python manage.py runserver 8000

worker:
	cd backend && DJANGO_DEBUG=1 .venv/bin/python manage.py run_scheduler

frontend:
	cd frontend && npm run dev

seed:
	cd backend && DJANGO_DEBUG=1 .venv/bin/python manage.py seed_demo --reset

test:
	cd backend && DJANGO_DEBUG=1 .venv/bin/pytest

lint:
	cd backend && .venv/bin/ruff check .
	cd frontend && npm run lint
