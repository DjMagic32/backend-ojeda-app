from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import DriverProfile, Vehicle, ServiceRequest, TaxiRide, LocationUpdate
from .serializers import (
    DriverProfileSerializer, VehicleSerializer, AvailabilityStatusUpdateSerializer,
    TaxiRideRequestInputSerializer, ServiceRequestOutputSerializer,
    ServiceRequestBriefOutputSerializer, LocationUpdateSerializer
)
from .permissions import (
    IsDriverUser, IsOwnerOfDriverProfile, IsOwnerOfVehicle, IsAdminUser,
    IsClienteUser, IsDriverAndOnline, IsAssignedDriver, IsOwnerOfServiceRequest
)
from store.models import Usuario # To check role

class DriverProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DriverProfile.
    - Current CONDUCTOR user can create their profile (if not exists).
    - Current CONDUCTOR user can view/update their own profile.
    - Admin can list/retrieve/update/delete any profile.
    """
    queryset = DriverProfile.objects.select_related('user').prefetch_related('vehicles').all()
    serializer_class = DriverProfileSerializer

    def get_permissions(self):
        if self.action == 'create':
            # Only a user with CONDUCTOR role who doesn't have a profile yet
            return [permissions.IsAuthenticated(), IsDriverUser()]
        if self.action in ['retrieve', 'update', 'partial_update']:
            # Owner or Admin
            return [permissions.IsAuthenticated(), IsOwnerOfDriverProfile() or IsAdminUser()]
        if self.action == 'destroy':
            return [IsAdminUser()] # Only admin can delete
        if self.action == 'list':
            return [IsAdminUser()] # Only admin can list all profiles
        if self.action == 'set_availability':
            return [permissions.IsAuthenticated(), IsOwnerOfDriverProfile(), IsDriverUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Check if user already has a profile handled in serializer validation
        serializer.save(user=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff: # Admin can see all
            return super().get_queryset()
        if user.is_authenticated and hasattr(user, 'driver_profile'):
            return super().get_queryset().filter(user=user)
        return DriverProfile.objects.none() # Non-admin, non-driver shouldn't see any

    def get_object(self):
        # For retrieve/update/partial_update of the current user's profile
        # without needing pk in URL if desired, or use standard lookup.
        # For simplicity, relying on standard pk lookup and IsOwnerOfDriverProfile.
        return super().get_object()

    # Custom action to update availability
    @action(detail=True, methods=['patch'], serializer_class=AvailabilityStatusUpdateSerializer, url_path='availability')
    def set_availability(self, request, pk=None):
        profile = self.get_object()
        self.check_object_permissions(request, profile) # Ensures owner
        serializer = self.get_serializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DriverProfileSerializer(profile).data)


class VehicleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vehicles owned by a Driver.
    - Driver can create, list, retrieve, update, delete their own vehicles.
    - Admin can manage any vehicle.
    """
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriverUser] # Base permission

    def get_queryset(self):
        user = self.request.user
        if user.is_staff: # Admin sees all
            return Vehicle.objects.all()
        if hasattr(user, 'driver_profile'):
            return Vehicle.objects.filter(driver=user.driver_profile)
        return Vehicle.objects.none()

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
            return [permissions.IsAuthenticated(), IsDriverUser(), IsOwnerOfVehicle() or IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        try:
            driver_profile = self.request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return Response(
                {"detail": "Driver profile does not exist for this user."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save(driver=driver_profile)


# --- Views for later steps (1.2, 1.3, 1.4) ---

class TaxiRideRequestView(generics.CreateAPIView):
    """
    Allows a CLIENTE user to request a taxi ride.
    Creates a ServiceRequest and a linked TaxiRide.
    """
    serializer_class = TaxiRideRequestInputSerializer
    permission_classes = [permissions.IsAuthenticated, IsClienteUser]

    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        service_request = ServiceRequest.objects.create(
            customer=request.user,
            pickup_latitude=data['pickup_latitude'],
            pickup_longitude=data['pickup_longitude'],
            pickup_address_text=data['pickup_address_text'],
            dropoff_latitude=data['dropoff_latitude'],
            dropoff_longitude=data['dropoff_longitude'],
            dropoff_address_text=data['dropoff_address_text'],
            service_type=ServiceRequest.SERVICE_TYPES[0][0], # 'TAXI'
            status=ServiceRequest.STATUS_CHOICES[0][0] # 'PENDING_ASSIGNMENT'
            # estimate_fare will be calculated later
        )

        TaxiRide.objects.create(
            service_request=service_request,
            vehicle_type_preference=data.get('vehicle_type_preference'),
            number_of_passengers=data.get('number_of_passengers', 1),
            ride_specific_notes=data.get('ride_specific_notes', '')
        )

        output_serializer = ServiceRequestOutputSerializer(service_request, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class AvailableTaxiRequestsView(generics.ListAPIView):
    """
    Allows an ONLINE driver to see available taxi requests.
    """
    serializer_class = ServiceRequestBriefOutputSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriverUser, IsDriverAndOnline]

    def get_queryset(self):
        # Later, add proximity filtering, vehicle type matching, etc.
        return ServiceRequest.objects.filter(
            service_type=ServiceRequest.SERVICE_TYPES[0][0], # 'TAXI'
            status=ServiceRequest.STATUS_CHOICES[0][0] # 'PENDING_ASSIGNMENT'
        ).order_by('requested_at')


class AcceptTaxiRequestView(generics.UpdateAPIView):
    """
    Allows an ONLINE driver to accept a specific taxi request.
    """
    queryset = ServiceRequest.objects.filter(
        service_type=ServiceRequest.SERVICE_TYPES[0][0], # 'TAXI'
        status=ServiceRequest.STATUS_CHOICES[0][0] # 'PENDING_ASSIGNMENT'
    )
    serializer_class = ServiceRequestOutputSerializer # Shows the updated request
    permission_classes = [permissions.IsAuthenticated, IsDriverUser, IsDriverAndOnline]

    def update(self, request, *args, **kwargs):
        service_request = self.get_object() # Gets SR based on pk from URL
        driver_profile = request.user.driver_profile

        if service_request.assigned_driver is not None:
            return Response({"detail": "This request has already been assigned."}, status=status.HTTP_400_BAD_REQUEST)

        # Atomically update to prevent race conditions if possible, or use select_for_update
        # For now, simple update.
        service_request.assigned_driver = driver_profile
        service_request.status = ServiceRequest.STATUS_CHOICES[1][0] # 'DRIVER_ASSIGNED'
        service_request.assigned_at = timezone.now() # Ensure timezone is imported from django.utils
        service_request.save()

        driver_profile.availability_status = DriverProfile.AVAILABILITY_STATUS_CHOICES[2][0] # 'BUSY'
        driver_profile.save()

        # TODO: Notify customer (WebSocket/Push Notification)

        serializer = self.get_serializer(service_request)
        return Response(serializer.data)

# Need to import timezone
from django.utils import timezone
