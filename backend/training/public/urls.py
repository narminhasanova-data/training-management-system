from django.urls import path

from . import views

urlpatterns = [
    path("preview/<str:signature>/", views.preview, name="survey-preview"),
    path("<str:token>/", views.answer, name="survey-answer"),
]
