from rest_framework import serializers
from .models import DriverProfile, Vehicle, ServiceRequest, TaxiRide, LocationUpdate
from store.models import Usuario # For validating user role

class VehicleSerializer(serializers.ModelSerializer):
    driver = serializers.PrimaryKeyRelatedField(read_only=True) # Set based on authenticated user

    class Meta:
        model = Vehicle
        fields = [
            'id', 'driver', 'type', 'make', 'model', 'year',
            'color', 'license_plate', 'insurance_details',
            'registration_details', 'is_active'
        ]
        read_only_fields = ['id', 'driver']

    def validate_license_plate(self, value):
        # Ensure license_plate is unique upon creation and update if changed
        instance = self.instance
        if instance and instance.license_plate == value: # No change
            return value
        if Vehicle.objects.filter(license_plate=value).exists():
            raise serializers.ValidationError("A vehicle with this license plate already exists.")
        return value

class DriverProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True) # Set to request.user
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    vehicles = VehicleSerializer(many=True, read_only=True) # Nested vehicles

    class Meta:
        model = DriverProfile
        fields = [
            'user', 'username', 'email', # Read-only fields from User model
            'current_latitude', 'current_longitude',
            'availability_status', 'average_rating',
            'documents_verified', 'vehicles', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'username', 'email', 'average_rating', 'documents_verified', 'vehicles', 'created_at', 'updated_at']

    def create(self, validated_data):
        # validated_data here WILL contain 'user' because view called serializer.save(user=self.request.user)
        user = validated_data['user'] # Get the user passed by save()

        if user.rol != Usuario.ES_CONDUCTOR:
            # Use serializers.ValidationError as 'serializers' is imported from rest_framework
            raise serializers.ValidationError("User must have the 'CONDUCTOR' role to create a driver profile.")
        if DriverProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError("Driver profile already exists for this user.")

        profile = DriverProfile.objects.create(**validated_data) # 'user' is in validated_data
        return profile

    def update(self, instance, validated_data):
        # Only availability_status and location can be updated by driver directly for now
        # Other fields like documents_verified are admin-only or internal logic
        instance.availability_status = validated_data.get('availability_status', instance.availability_status)
        instance.current_latitude = validated_data.get('current_latitude', instance.current_latitude)
        instance.current_longitude = validated_data.get('current_longitude', instance.current_longitude)
        instance.save()
        return instance


class AvailabilityStatusUpdateSerializer(serializers.Serializer):
    availability_status = serializers.ChoiceField(choices=DriverProfile.AVAILABILITY_STATUS_CHOICES)

    def update(self, instance, validated_data):
        instance.availability_status = validated_data['availability_status']
        instance.save()
        return instance


# --- Serializers for later steps (1.2, 1.3, 1.4) ---

class TaxiRideRequestInputSerializer(serializers.Serializer):
    pickup_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    pickup_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    pickup_address_text = serializers.CharField(max_length=255, required=True)

    dropoff_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    dropoff_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    dropoff_address_text = serializers.CharField(max_length=255, required=True)

    # TaxiRide specific
    vehicle_type_preference = serializers.ChoiceField(choices=Vehicle.VEHICLE_TYPES, required=False, allow_null=True)
    number_of_passengers = serializers.IntegerField(default=1, min_value=1, max_value=8) # Max 8 for typical cars/vans
    ride_specific_notes = serializers.CharField(required=False, allow_blank=True)


class TaxiRideDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxiRide
        fields = ['vehicle_type_preference', 'number_of_passengers', 'ride_specific_notes']


class ServiceRequestOutputSerializer(serializers.ModelSerializer):
    customer_username = serializers.CharField(source='customer.username', read_only=True)
    assigned_driver_username = serializers.CharField(source='assigned_driver.user.username', read_only=True, allow_null=True)
    taxi_details = TaxiRideDetailsSerializer(read_only=True, allow_null=True)
    # delivery_details will be added later if this serializer is shared

    class Meta:
        model = ServiceRequest
        fields = '__all__' # Or list specific fields
        read_only_fields = [
            'id', 'customer', 'assigned_driver', 'service_type', 'status',
            'requested_at', 'updated_at', 'assigned_at', 'pickup_at',
            'dropped_off_at', 'completed_at', 'cancelled_at', 'payment_status'
        ]

class ServiceRequestBriefOutputSerializer(serializers.ModelSerializer):
    customer_username = serializers.CharField(source='customer.username', read_only=True)
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'customer_username', 'pickup_address_text', 'dropoff_address_text',
            'pickup_latitude', 'pickup_longitude', 'service_type', 'status', 'requested_at',
            'estimated_fare' # Add if available early
        ]

class LocationUpdateSerializer(serializers.ModelSerializer):
    driver = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = LocationUpdate
        fields = ['id', 'driver', 'latitude', 'longitude', 'timestamp', 'heading']
        read_only_fields = ['id', 'driver', 'timestamp']
