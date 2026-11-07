from django.urls import path

from . import views

urlpatterns = [
    path("", views.overview, name="integrations"),
    path("<str:purpose>/connect/", views.connect, name="integrations-connect"),
    path("<str:purpose>/disconnect/", views.disconnect, name="integrations-disconnect"),
]
