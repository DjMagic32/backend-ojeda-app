from django.db import models
# from django.contrib.gis.db import models as gis_models # Enable if PostGIS is available
from store.models import Usuario

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('SEDAN', 'Sedan'),
        ('SUV', 'SUV'),
        ('MOTORCYCLE', 'Motorcycle'),
        ('VAN', 'Van'),
        ('OTHER', 'Other'),
    ]
    # driver = models.ForeignKey('DriverProfile', on_delete=models.CASCADE, related_name='vehicles') # Link after DriverProfile is defined
    type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='SEDAN')
    make = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    color = models.CharField(max_length=30, blank=True)
    license_plate = models.CharField(max_length=20, unique=True)
    insurance_details = models.TextField(blank=True, null=True)
    registration_details = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True) # If this vehicle can be used by the driver

    def __str__(self):
        return f"{self.make} {self.model} ({self.license_plate})"

class DriverProfile(models.Model):
    AVAILABILITY_STATUS_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('BUSY', 'Busy'), # On a current trip/delivery
    ]
    user = models.OneToOneField(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': Usuario.ES_CONDUCTOR}, related_name='driver_profile')
    # current_location = gis_models.PointField(null=True, blank=True, srid=4326) # SRID 4326 for WGS84 lat/lon
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    availability_status = models.CharField(max_length=10, choices=AVAILABILITY_STATUS_CHOICES, default='OFFLINE')
    average_rating = models.FloatField(default=0.0)
    documents_verified = models.BooleanField(default=False) # Simplified for now
    # Payout details can be complex, might link to a separate model or use Wallet
    # active_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_driver')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Driver: {self.user.username}"

# Add the ForeignKey to Vehicle model now that DriverProfile is defined
Vehicle.add_to_class('driver', models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='vehicles'))


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING_ASSIGNMENT', 'Pending Assignment'),
        ('DRIVER_ASSIGNED', 'Driver Assigned'),
        ('EN_ROUTE_PICKUP', 'En Route to Pickup'),
        ('AT_PICKUP', 'At Pickup Location'),
        ('EN_ROUTE_DROPOFF', 'En Route to Dropoff'),
        ('AT_DROPOFF', 'At Dropoff Location'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED_CUSTOMER', 'Cancelled by Customer'),
        ('CANCELLED_DRIVER', 'Cancelled by Driver'),
        ('CANCELLED_SYSTEM', 'Cancelled by System'), # e.g. no drivers available
        ('FAILED', 'Failed'), # General failure
    ]
    SERVICE_TYPES = [
        ('TAXI', 'Taxi Ride'),
        ('DELIVERY', 'Product Delivery'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    customer = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='service_requests')
    assigned_driver = models.ForeignKey(DriverProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')

    pickup_address_text = models.TextField()
    # pickup_location = gis_models.PointField(srid=4326)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)

    dropoff_address_text = models.TextField()
    # dropoff_location = gis_models.PointField(srid=4326)
    dropoff_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_longitude = models.DecimalField(max_digits=9, decimal_places=6)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_ASSIGNMENT')
    service_type = models.CharField(max_length=10, choices=SERVICE_TYPES) # To distinguish if using one table for both

    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True) # Estimated or actual
    duration_minutes = models.PositiveIntegerField(null=True, blank=True) # Estimated or actual

    payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    # Could link to store.Pedido or have its own payment transaction ID
    payment_intent_id = models.CharField(max_length=100, blank=True, null=True) # e.g., Stripe PaymentIntent ID

    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Timestamps for various stages
    assigned_at = models.DateTimeField(null=True, blank=True)
    pickup_at = models.DateTimeField(null=True, blank=True) # Actual pickup time
    dropped_off_at = models.DateTimeField(null=True, blank=True) # Actual dropoff time
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        # Consider an abstract base class if TaxiRide and DeliveryOrder will have many shared fields
        # but also many distinct ones. For now, using service_type to differentiate.
        # abstract = True

    def __str__(self):
        return f"{self.get_service_type_display()} #{self.id} - {self.customer.username} - {self.get_status_display()}"


class TaxiRide(models.Model): # Could inherit from ServiceRequest if it becomes abstract
    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, primary_key=True, related_name='taxi_details', limit_choices_to={'service_type': 'TAXI'})
    vehicle_type_preference = models.CharField(max_length=20, choices=Vehicle.VEHICLE_TYPES, blank=True, null=True)
    number_of_passengers = models.PositiveIntegerField(default=1)
    ride_specific_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Taxi Ride for SR #{self.service_request.id}"

class LocationUpdate(models.Model):
    # service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='location_updates', null=True, blank=True)
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='location_history')
    # location = gis_models.PointField(srid=4326)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    heading = models.IntegerField(null=True, blank=True) # Degrees from North, 0-359

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Location for {self.driver.user.username} at {self.timestamp}"

class ServiceRating(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='ratings')
    rater_user = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='given_ratings') # User giving the rating
    rated_user = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='received_ratings') # User (driver/customer) being rated
    # Or have separate rated_driver and rated_customer ForeignKeys if preferred
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)]) # 1 to 5 stars
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('service_request', 'rater_user', 'rated_user') # Ensure one rating per user role per request

    def __str__(self):
        return f"Rating {self.rating}/5 for SR #{self.service_request.id} by {self.rater_user.username} for {self.rated_user.username}"

# Potential Future Models:
# - PayoutLog (for driver payouts)
# - SupportTicket (for issues with rides/deliveries)
# - PromoCode / Discount
# - Geofence / Zone (for pricing or service areas)
# - DriverDocument (for licenses, insurance proofs etc. for verification)
