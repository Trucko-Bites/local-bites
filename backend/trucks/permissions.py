from rest_framework import permissions


class IsOwnerOrStaffOrReadOnly(permissions.BasePermission):
    """
    Anyone can read trucks. Any logged-in user can review a truck. Only staff
    (such as the admin account) can create a truck. Only the truck's owner,
    or staff, can change, check in, or delete it.

    Anyone can sign up, so creating trucks is limited to staff to keep fake
    trucks off the public map. Staff assign each truck's owner in Django admin.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Writing anything requires being logged in
        if not (request.user and request.user.is_authenticated):
            return False
        # POST /api/trucks/ (the viewset's "create" action) is staff-only
        if getattr(view, "action", None) == "create":
            return request.user.is_staff
        return True

    def has_object_permission(self, request, view, food_truck):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Any logged-in customer can review any truck. The reviews view itself
        # blocks owners from reviewing their own truck.
        if getattr(view, "action", None) == "reviews":
            return True
        return request.user.is_staff or food_truck.owner_id == request.user.id
