from django.urls import path

from . import views

urlpatterns = [path("authorize/", views.mock_authorize, name="mock-authorize")]
