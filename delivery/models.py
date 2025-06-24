from django.db import models
from taxi.models import ServiceRequest # Assuming ServiceRequest is the generic request model

class DeliveryOrder(models.Model):
    # Links to the generic ServiceRequest, ensuring it's of type 'DELIVERY'
    service_request = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='delivery_details',
        limit_choices_to={'service_type': 'DELIVERY'}
    )

    # Delivery-specific fields
    item_description = models.TextField(help_text="Description of the item(s) being delivered.")
    item_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Weight of the item in kilograms.")
    item_dimensions_cm = models.CharField(max_length=100, blank=True, null=True, help_text="LxWxH in centimeters, e.g., '50x30x20'.")

    recipient_name = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=20) # Consider validation for phone numbers

    pickup_instructions = models.TextField(blank=True, null=True, help_text="Special instructions for the driver at pickup.")
    dropoff_instructions = models.TextField(blank=True, null=True, help_text="Special instructions for the driver at dropoff.")

    # Proof of delivery
    proof_of_delivery_image = models.ImageField(upload_to='proof_of_delivery/', blank=True, null=True)
    # Signature could be another ImageField or handled via a third-party service if digital signatures are needed

    # Optional: if deliveries can be scheduled for a specific time window
    # requested_pickup_time_start = models.DateTimeField(null=True, blank=True)
    # requested_pickup_time_end = models.DateTimeField(null=True, blank=True)
    # requested_delivery_time_start = models.DateTimeField(null=True, blank=True)
    # requested_delivery_time_end = models.DateTimeField(null=True, blank=True)

    # Consider if COD (Cash On Delivery) is a feature
    # is_cod = models.BooleanField(default=False)
    # cod_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Delivery for SR #{self.service_request.id} - Item: {self.item_description[:50]}"

# If there are other delivery-specific models, they would go here.
# For example, if there were different types of delivery services (e.g., scheduled, express).
# Or if delivery items needed to be itemized in more detail (e.g. a list of products from a store).
# For now, we assume a single 'package' or 'consignment' per delivery order.
