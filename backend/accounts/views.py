from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .permissions import is_staff_member
from .serializers import LoginResponseSerializer, LoginSerializer, UserSerializer, user_data


class LoginThrottle(ScopedRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


@extend_schema(request=LoginSerializer, responses={200: LoginResponseSerializer}, auth=[])
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login(request):
    """Exchange a staff username and password for an API token."""
    data = LoginSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    user = authenticate(request, **data.validated_data)
    if user is None or not is_staff_member(user):
        return Response({"error": "Wrong username or password."}, status=status.HTTP_400_BAD_REQUEST)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": user_data(user)})


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """Invalidate the current token."""
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses={200: UserSerializer})
@api_view(["GET"])
def me(request):
    """The signed-in staff member."""
    return Response(user_data(request.user))
