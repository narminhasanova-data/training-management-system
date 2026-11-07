from django.contrib import admin

from .models import ConnectedAccount, OutboundMessage


@admin.register(ConnectedAccount)
class ConnectedAccountAdmin(admin.ModelAdmin):
    list_display = ("purpose", "email", "connected_at", "connected_by", "expires_at", "revoked_at")
    exclude = ("secret",)


@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "recipient", "subject", "template", "status", "context")
    list_filter = ("channel", "status")
    search_fields = ("recipient", "subject", "context")
    readonly_fields = [f.name for f in OutboundMessage._meta.fields]
