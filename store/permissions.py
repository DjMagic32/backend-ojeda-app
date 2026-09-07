from rest_framework.permissions import BasePermission

class EsTienda(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'rol', None) == 'TIENDA'
        )
