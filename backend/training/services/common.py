from statistics import mean

from django.shortcuts import get_object_or_404

from ..models import Cohort


class ServiceError(Exception):
    """A request the business rules reject; shown to the user as is."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def cohort_by_number(number: int) -> Cohort:
    return get_object_or_404(Cohort, number=number)


def who(user) -> str:
    return (user.get_full_name() or user.get_username()) if user and user.is_authenticated else ""


def average(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(mean(values), 2) if values else None


def percent(part: float, whole: float) -> float | None:
    return round(100 * part / whole, 1) if whole else None
