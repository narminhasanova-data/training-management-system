from rest_framework.permissions import BasePermission

STAFF_GROUP = "training-staff"


def is_staff_member(user) -> bool:
    """Training-office staff: Django staff users or members of the training-staff group."""
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and (user.is_staff or user.groups.filter(name=STAFF_GROUP).exists())
    )


class IsStaffMember(BasePermission):
    message = "A training-office account is required."

    def has_permission(self, request, view):
        return is_staff_member(request.user)
