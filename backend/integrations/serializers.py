from rest_framework import serializers

from .models import ConnectedAccount


class ConnectionStatusSerializer(serializers.Serializer):
    connected = serializers.BooleanField()
    mode = serializers.CharField()
    email = serializers.EmailField(required=False)
    connected_at = serializers.DateTimeField(required=False)
    connected_by = serializers.CharField(required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    expired = serializers.BooleanField()
    expiring_soon = serializers.BooleanField()
    scopes = serializers.ListField(child=serializers.CharField(), required=False)


class ChannelSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    mode = serializers.CharField()


class IntegrationsSerializer(serializers.Serializer):
    mail = ConnectionStatusSerializer()
    classroom = ConnectionStatusSerializer()
    whatsapp = ChannelSerializer()


class ConnectSerializer(serializers.Serializer):
    page = serializers.ChoiceField(choices=["agenda", "surveys", "classroom", "tracker"], default="classroom")


class ConnectResponseSerializer(serializers.Serializer):
    url = serializers.CharField()


PURPOSES = [p.value for p in ConnectedAccount.Purpose]
