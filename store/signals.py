from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario, Wallet, Carrito

@receiver(post_save, sender=Usuario)
def crear_wallet_y_carrito(sender, instance, created, **kwargs):
    if created:  # Solo se ejecuta al crear un usuario, no al actualizarlo
        # Crear la wallet del usuario
        Wallet.objects.get_or_create(usuario=instance)
        
        # Crear el carrito del usuario (opcional, dependiendo de tu lógica)
        Carrito.objects.get_or_create(usuario=instance)
