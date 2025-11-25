# backoffice/permissions.py
from rest_framework.permissions import BasePermission

class IsStaff(BasePermission):
    message = "Staff access only."
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and getattr(u, "is_staff", False))
