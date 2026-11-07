import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from integrations.classroom.fake import FakeClassroom


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Load the fictional demo data once; every test runs in a transaction that is rolled back."""
    with django_db_blocker.unblock():
        call_command("seed_demo", verbosity=0)


@pytest.fixture(autouse=True)
def _fresh_state(db):
    cache.clear()
    FakeClassroom._cache = {}
    yield
    FakeClassroom._cache = {}


@pytest.fixture
def staff():
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(username="coordinator")


@pytest.fixture
def api(staff):
    client = APIClient()
    client.force_authenticate(staff)
    return client


@pytest.fixture
def cohort102():
    from training.models import Cohort

    return Cohort.objects.get(number=102)
