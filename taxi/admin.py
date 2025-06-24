from django.contrib import admin
from .models import DriverProfile, Vehicle, ServiceRequest, TaxiRide, LocationUpdate, ServiceRating

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'driver', 'type', 'make', 'model', 'is_active')
    list_filter = ('type', 'is_active', 'driver')
    search_fields = ('license_plate', 'make', 'model', 'driver__user__username')

@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'availability_status', 'average_rating', 'documents_verified', 'current_latitude', 'current_longitude')
    list_filter = ('availability_status', 'documents_verified')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',) # For easier user selection

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'service_type', 'status', 'assigned_driver',
        'pickup_address_text', 'dropoff_address_text',
        'requested_at', 'estimated_fare', 'actual_fare', 'payment_status'
    )
    list_filter = ('status', 'service_type', 'payment_status', 'requested_at', 'assigned_driver')
    search_fields = (
        'id', 'customer__username', 'assigned_driver__user__username',
        'pickup_address_text', 'dropoff_address_text'
    )
    raw_id_fields = ('customer', 'assigned_driver')
    readonly_fields = ('requested_at', 'updated_at', 'assigned_at', 'pickup_at', 'dropped_off_at', 'completed_at', 'cancelled_at')

@admin.register(TaxiRide)
class TaxiRideAdmin(admin.ModelAdmin):
    list_display = ('service_request_id', 'get_customer', 'get_status', 'vehicle_type_preference', 'number_of_passengers')
    search_fields = ('service_request__id', 'service_request__customer__username')
    raw_id_fields = ('service_request',)

    def service_request_id(self, obj):
        return obj.service_request.id
    service_request_id.short_description = 'SR ID'

    def get_customer(self, obj):
        return obj.service_request.customer
    get_customer.short_description = 'Customer'
    get_customer.admin_order_field = 'service_request__customer'

    def get_status(self, obj):
        return obj.service_request.get_status_display()
    get_status.short_description = 'Status'
    get_status.admin_order_field = 'service_request__status'


@admin.register(LocationUpdate)
class LocationUpdateAdmin(admin.ModelAdmin):
    list_display = ('driver', 'latitude', 'longitude', 'timestamp', 'heading')
    list_filter = ('timestamp', 'driver')
    search_fields = ('driver__user__username',)
    readonly_fields = ('timestamp',)

@admin.register(ServiceRating)
class ServiceRatingAdmin(admin.ModelAdmin):
    list_display = ('service_request_id', 'rater_user', 'rated_user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('service_request__id', 'rater_user__username', 'rated_user__username')
    raw_id_fields = ('service_request', 'rater_user', 'rated_user')

    def service_request_id(self, obj):
        return obj.service_request.id
    service_request_id.short_description = 'SR ID'
