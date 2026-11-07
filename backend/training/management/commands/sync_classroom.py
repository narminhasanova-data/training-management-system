from django.core.management.base import BaseCommand, CommandError

from training.models import Cohort
from training.services import classroom


class Command(BaseCommand):
    help = "Sync cohorts from Google Classroom now (all linked cohorts, or one with --cohort)."

    def add_arguments(self, parser):
        parser.add_argument("--cohort", type=int, help="Cohort number")
        parser.add_argument(
            "--add-unmatched", action="store_true", help="Create students Classroom has but the site lacks"
        )

    def handle(self, *args, cohort=None, add_unmatched=False, **options):
        cohorts = Cohort.objects.filter(classroom_classes__isnull=False).distinct()
        if cohort:
            cohorts = cohorts.filter(number=cohort)
            if not cohorts:
                raise CommandError(f"Cohort {cohort} is not linked to Classroom.")
        for c in cohorts:
            summary = classroom.sync_or_record(c, add_unmatched)
            status = (
                f"error: {summary['error']}"
                if summary.get("error")
                else (
                    f"{summary['students']} students, {summary['assignments']} assignments, {summary['graded']} grades"
                )
            )
            self.stdout.write(f"{c.name}: {status}")
