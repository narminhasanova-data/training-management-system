from django.core.management.base import BaseCommand

from integrations import accounts


class Command(BaseCommand):
    help = "Demo helper: mark a connected account as expired to show the reconnect warnings."

    def add_arguments(self, parser):
        parser.add_argument("purpose", choices=["mail", "classroom"])

    def handle(self, purpose, **options):
        done = accounts.expire(purpose)
        self.stdout.write(f"{purpose}: {'marked as expired' if done else 'not connected'}")
