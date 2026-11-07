from django.db import models
from django.utils import timezone


class ConnectedAccount(models.Model):
    """An external account connected from the web app, one per purpose: the mailbox that sends
    emails, and the Google Classroom teacher account the sync reads from."""

    class Purpose(models.TextChoices):
        MAIL = "mail", "Sender mailbox"
        CLASSROOM = "classroom", "Google Classroom"

    provider = models.CharField(max_length=20, default="google")
    purpose = models.CharField(max_length=10, choices=Purpose.choices, unique=True)
    email = models.EmailField()
    secret = models.TextField(help_text="Encrypted token payload")
    scopes = models.JSONField(default=list, blank=True)
    connected_at = models.DateTimeField(default=timezone.now)
    connected_by = models.CharField(max_length=120, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_purpose_display()}: {self.email}"

    @property
    def expired(self) -> bool:
        return bool(self.revoked_at or (self.expires_at and timezone.now() >= self.expires_at))


class OutboundMessage(models.Model):
    """Every email and WhatsApp message the system sends (or simulates), for auditing."""

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        SIMULATED = "simulated", "Simulated (mock)"
        FAILED = "failed", "Failed"

    channel = models.CharField(max_length=10, choices=Channel.choices)
    recipient = models.CharField(max_length=200)
    subject = models.CharField(max_length=300, blank=True)
    template = models.CharField(max_length=80, blank=True)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    error = models.TextField(blank=True)
    context = models.CharField(max_length=120, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel} → {self.recipient} ({self.status})"
