from rest_framework import permissions


class IsOwnerOrStaffOrReadOnly(permissions.BasePermission):
    """
    Anyone can read trucks. Only the truck's owner, or a staff user
    (such as the admin account), can change, check in, or delete it.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Writing anything requires being logged in
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, food_truck):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or food_truck.owner_id == request.user.id
