from rest_framework.permissions import BasePermission

class EsTienda(BasePermission):
    def has_permission(self, request, view):
        return request.user.rol == 'TIENDA'
