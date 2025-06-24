from django.contrib import admin
from .models import DeliveryOrder

@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = (
        'service_request_id', 'get_customer', 'get_status',
        'item_description_short', 'recipient_name', 'recipient_phone'
    )
    list_filter = ('service_request__status', 'service_request__requested_at')
    search_fields = (
        'service_request__id', 'service_request__customer__username',
        'item_description', 'recipient_name', 'recipient_phone'
    )
    raw_id_fields = ('service_request',)
    readonly_fields = ('get_pickup_address', 'get_dropoff_address')

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

    def item_description_short(self, obj):
        return (obj.item_description[:75] + '...') if len(obj.item_description) > 75 else obj.item_description
    item_description_short.short_description = 'Item Description'

    def get_pickup_address(self, obj):
        return obj.service_request.pickup_address_text
    get_pickup_address.short_description = 'Pickup Address'

    def get_dropoff_address(self, obj):
        return obj.service_request.dropoff_address_text
    get_dropoff_address.short_description = 'Dropoff Address'
