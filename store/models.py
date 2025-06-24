from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] 
    ES_TIENDA = 'TIENDA'
    ES_CLIENTE = 'CLIENTE'
    ES_CONDUCTOR = 'CONDUCTOR'  # New role for Driver
    ROLES = [
        (ES_TIENDA, 'Tienda'),
        (ES_CLIENTE, 'Cliente'),
        (ES_CONDUCTOR, 'Conductor'),
    ]

    GENERO_MASCULINO = 'M'
    GENERO_FEMENINO = 'F'
    GENERO_OTRO = 'O'
    GENEROS = [
        (GENERO_MASCULINO, 'Masculino'),
        (GENERO_FEMENINO, 'Femenino'),
        (GENERO_OTRO, 'Otro'),
    ]
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=10, choices=ROLES, default=ES_CLIENTE)
    edad = models.PositiveIntegerField(blank=True, null=True)
    genero = models.CharField(max_length=1, choices=GENEROS, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    cedula_pasaporte = models.CharField(max_length=20, unique=True, blank=True, null=True)
    foto_identificacion = models.ImageField(upload_to='identificaciones/', blank=True, null=True)
    ingresos_minimos_mensuales = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"

class Tienda(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': Usuario.ES_TIENDA})
    nombre = models.CharField(max_length=200)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    informacion_fiscal = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

# Represents a product as offered or managed by a specific Tienda.
# Stores manage their inventory/offerings through this model.
# TODO: Review for potential redundancy with the Producto model or for a
# clearer linkage if this represents a store's specific stock/offering
# of a generic Producto from a central catalog.
class ProductoTienda(models.Model):
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre} - {self.tienda.nombre}"

class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.producto.precio

class Pedido(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='pedidos')
    items = models.ManyToManyField(ItemCarrito)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    creado = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    estado_pago = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    payment_intent_id = models.CharField(max_length=100, blank=True, null=True) # For Stripe
    binance_order_id = models.CharField(max_length=100, blank=True, null=True) # For Binance Pay

    # Old 'pagado' field can be removed or kept for backward compatibility if needed
    # For now, let's assume new logic uses 'estado_pago'
    # pagado = models.BooleanField(default=False)

    def __str__(self):
        return f"Pedido {self.id} de {self.usuario.username} - {self.estado_pago}"

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

# Represents a generic product available in the marketplace,
# linked to categories and directly added to customer carts.
class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)

    def __str__(self):
        return self.nombre

class Comentario(models.Model):
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    contenido = models.TextField()
    calificacion = models.PositiveSmallIntegerField(default=5)  # Rango de 1 a 5 estrellas
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.tienda.nombre}: {self.calificacion} estrellas"

class ComentarioProducto(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    texto = models.TextField()
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentario de {self.usuario.username} en {self.producto.nombre}"

class Referencia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='referencias')
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='referencias', blank=True, null=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='referencias', blank=True, null=True)
    es_mal_comprador = models.BooleanField(default=False)
    es_mal_vendedor = models.BooleanField(default=False)
    comentario = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Referencia de {self.usuario.username}"

class Wallet(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='wallet')
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet de {self.usuario.username} - Saldo: {self.saldo}"

# Chat Models
class ChatRoom(models.Model):
    participants = models.ManyToManyField(Usuario, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # To track last message time for sorting

    def __str__(self):
        return f"ChatRoom {self.id} ({self.participants.count()} participants)"

class ChatMessage(models.Model):
    MESSAGE_TYPE_TEXT = 'text'
    MESSAGE_TYPE_PROPOSAL_INITIATE = 'proposal_initiate'
    MESSAGE_TYPE_PROPOSAL_ACCEPT = 'proposal_accept'
    MESSAGE_TYPE_PROPOSAL_REJECT = 'proposal_reject'
    MESSAGE_TYPE_PROPOSAL_CANCEL = 'proposal_cancel' # Added cancel
    MESSAGE_TYPE_PROPOSAL_COMPLETE = 'proposal_complete' # Added complete

    MESSAGE_TYPES = [
        (MESSAGE_TYPE_TEXT, 'Text'),
        (MESSAGE_TYPE_PROPOSAL_INITIATE, 'Proposal Initiated'),
        (MESSAGE_TYPE_PROPOSAL_ACCEPT, 'Proposal Accepted'),
        (MESSAGE_TYPE_PROPOSAL_REJECT, 'Proposal Rejected'),
        (MESSAGE_TYPE_PROPOSAL_CANCEL, 'Proposal Cancelled'),
        (MESSAGE_TYPE_PROPOSAL_COMPLETE, 'Proposal Completed'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True, null=True) # Can be null for non-text messages
    timestamp = models.DateTimeField(auto_now_add=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default=MESSAGE_TYPE_TEXT)
    # related_proposal = models.ForeignKey('ExchangeProposal', null=True, blank=True, on_delete=models.SET_NULL, related_name='chat_messages')

    def __str__(self):
        return f"Message from {self.sender.username} in Room {self.room.id} at {self.timestamp}"

    class Meta:
        ordering = ['timestamp']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the parent room's updated_at timestamp
        self.room.updated_at = self.timestamp
        self.room.save(update_fields=['updated_at'])


class ExchangeProposal(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled' # User who proposed can cancel before acceptance
    STATUS_COMPLETED = 'completed' # Both parties agree it's done

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='exchange_proposals')
    proposing_user = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='made_proposals')
    # Assuming for now that a proposal is about a 'Producto'.
    # If it can be about a 'Service' or other models, GenericForeignKey might be better.
    # Or, have separate fields like `proposed_product` and `proposed_service` (nullable).
    proposed_product = models.ForeignKey(Producto, null=True, blank=True, on_delete=models.SET_NULL)
    # proposed_service_description = models.TextField(null=True, blank=True) # If services are just text based for now

    quantity = models.PositiveIntegerField(default=1, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # Price for the exchange, if any
    terms = models.TextField(blank=True, null=True) # Additional terms or description of the exchange

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Link to the message that initiated this proposal
    initiating_message = models.OneToOneField(ChatMessage, null=True, blank=True, on_delete=models.SET_NULL, related_name='initiated_proposal_in_message')


    def __str__(self):
        item_name = self.proposed_product.name if self.proposed_product else "Ad-hoc service/item"
        return f"Proposal by {self.proposing_user.username} for '{item_name}' in Room {self.chat_room.id} - Status: {self.status}"