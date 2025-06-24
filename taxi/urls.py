from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DriverProfileViewSet, VehicleViewSet,
    TaxiRideRequestView, AvailableTaxiRequestsView, AcceptTaxiRequestView
    # Import other views as they are created e.g. LocationUpdateView
)

router = DefaultRouter()
router.register(r'drivers/profile', DriverProfileViewSet, basename='driverprofile')
# Note: VehicleViewSet actions are implicitly tied to the authenticated driver's profile.
# If we wanted vehicles as a nested resource under driver profile, the URL structure would be different.
# e.g. /api/taxi/drivers/profile/{profile_pk}/vehicles/
# For simplicity now, /api/taxi/vehicles/ will list/create vehicles for the logged-in driver.
router.register(r'vehicles', VehicleViewSet, basename='vehicle')

# TODO: Add LocationUpdateView to router when created.
# router.register(r'drivers/location', LocationUpdateViewSet, basename='locationupdate')


app_name = 'taxi'

urlpatterns = [
    path('', include(router.urls)),

    # Specific paths for ride lifecycle if not using ViewSet actions for everything
    path('rides/request/', TaxiRideRequestView.as_view(), name='taxi-ride-request'),
    path('rides/available/', AvailableTaxiRequestsView.as_view(), name='available-taxi-rides'),
    path('rides/<int:pk>/accept/', AcceptTaxiRequestView.as_view(), name='accept-taxi-ride'),

    # Example for a future view not part of a ViewSet
    # path('drivers/location_update/', LocationUpdateView.as_view(), name='driver-location-update'),
]
