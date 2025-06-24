from rest_framework import permissions
from store.models import Usuario # To check roles
from .models import DriverProfile

class IsDriverUser(permissions.BasePermission):
    """
    Allows access only to users with the 'CONDUCTOR' role.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == Usuario.ES_CONDUCTOR

class IsOwnerOfDriverProfile(permissions.BasePermission):
    """
    Allows access only if the request.user is the user associated with the DriverProfile.
    Assumes the view's object is a DriverProfile instance.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class IsOwnerOfVehicle(permissions.BasePermission):
    """
    Allows access only if the request.user is the driver associated with the Vehicle.
    Assumes the view's object is a Vehicle instance.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            driver_profile = request.user.driver_profile
            return obj.driver == driver_profile
        except DriverProfile.DoesNotExist:
            return False

class IsDriverAndOnline(permissions.BasePermission):
    """
    Allows access only to 'CONDUCTOR' role users who are 'ONLINE'.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.rol == Usuario.ES_CONDUCTOR):
            return False
        try:
            driver_profile = request.user.driver_profile
            return driver_profile.availability_status == DriverProfile.AVAILABILITY_STATUS_CHOICES[0][0] # 'ONLINE'
        except DriverProfile.DoesNotExist:
            return False # No profile means cannot be online as a driver

class IsClienteUser(permissions.BasePermission):
    """
    Allows access only to users with the 'CLIENTE' role.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == Usuario.ES_CLIENTE


# --- Permissions for later steps ---

class IsAssignedDriver(permissions.BasePermission):
    """
    Allows access only if the request.user is the driver assigned to the ServiceRequest.
    """
    def has_object_permission(self, request, view, obj): # obj is ServiceRequest
        if not (request.user and request.user.is_authenticated and request.user.rol == Usuario.ES_CONDUCTOR):
            return False
        try:
            driver_profile = request.user.driver_profile
            return obj.assigned_driver == driver_profile
        except DriverProfile.DoesNotExist:
            return False

class IsOwnerOfServiceRequest(permissions.BasePermission):
    """
    Allows access only if the request.user is the customer who created the ServiceRequest.
    """
    def has_object_permission(self, request, view, obj): # obj is ServiceRequest
        return obj.customer == request.user

# Combined permissions might be useful too, e.g. IsOwnerOrAdmin, IsDriverOrAdmin etc.
# For now, keeping them specific.

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows all authenticated users for read-only requests (GET, HEAD, OPTIONS).
    Allows only admin users for write requests (POST, PUT, PATCH, DELETE).
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff # is_staff typically denotes admin

class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff
