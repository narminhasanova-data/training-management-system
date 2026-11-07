"""The background worker: keeps Classroom data fresh.

    python manage.py run_scheduler          # loop forever (docker-compose "worker" service)
    python manage.py run_scheduler --once   # one pass, e.g. from cron

Each pass syncs the linked cohorts that are due (running cohorts every CLASSROOM_SYNC_MINUTES,
others daily) and, with CLASSROOM_AUTO_IMPORT=1, imports new Classroom cohorts once an hour.
Several workers can run safely: a PostgreSQL advisory lock lets only one of them sync at a time.
"""

import logging
import signal
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from integrations.accounts import IntegrationError
from integrations.classroom.base import ClassroomError
from training.services import classroom

log = logging.getLogger("training.scheduler")
IMPORT_EVERY = 3600


class Command(BaseCommand):
    help = "Run the background scheduler (Classroom sync and auto-import)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run one pass and exit.")

    def handle(self, *args, once=False, **options):
        self.running = True
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        tick = settings.TMS["SCHEDULER_TICK_SECONDS"]
        last_import = None
        log.info("scheduler started (tick %ss, auto-import %s)", tick, settings.TMS["CLASSROOM_AUTO_IMPORT"])
        while self.running:
            close_old_connections()
            if classroom.connected():
                due = last_import is None or time.monotonic() - last_import >= IMPORT_EVERY
                if settings.TMS["CLASSROOM_AUTO_IMPORT"] and due:
                    last_import = time.monotonic()
                    self.run("auto-import", classroom.auto_import)
                self.run("sync", classroom.sync_due)
            if once:
                break
            self.sleep(tick)
        log.info("scheduler stopped")

    def run(self, name, job):
        try:
            done = job()
            if done:
                self.stdout.write(f"{name}: cohorts {', '.join(map(str, done))}")
        except (ClassroomError, IntegrationError) as exc:
            log.warning("%s skipped: %s", name, exc)
        except Exception:
            log.exception("%s failed", name)

    def sleep(self, seconds):
        end = time.monotonic() + seconds
        while self.running and time.monotonic() < end:
            time.sleep(min(1, end - time.monotonic()))

    def stop(self, *_):
        self.running = False
