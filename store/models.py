from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] 
    ES_TIENDA = 'TIENDA'
    ES_CLIENTE = 'CLIENTE'
    ES_CONDUCTOR = 'CONDUCTOR'
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
    es_conductor = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"


class DriverProfile(models.Model):
    ESTADO_OFFLINE = 'offline'
    ESTADO_DISPONIBLE = 'available'
    ESTADO_EN_VIAJE = 'on_trip'
    ESTADOS = [
        (ESTADO_OFFLINE, 'Fuera de línea'),
        (ESTADO_DISPONIBLE, 'Disponible'),
        (ESTADO_EN_VIAJE, 'En viaje'),
    ]

    VEHICULO_AUTO = 'auto'
    VEHICULO_MOTO = 'moto'
    VEHICULO_BICI = 'bici'
    TIPOS_VEHICULO = [
        (VEHICULO_AUTO, 'Auto'),
        (VEHICULO_MOTO, 'Moto'),
        (VEHICULO_BICI, 'Bicicleta'),
    ]

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='perfil_conductor',
    )
    licencia_numero = models.CharField(max_length=64, blank=True, null=True)
    vehiculo_tipo = models.CharField(max_length=20, choices=TIPOS_VEHICULO, blank=True, null=True)
    vehiculo_placa = models.CharField(max_length=20, blank=True, null=True)
    vehiculo_color = models.CharField(max_length=30, blank=True, null=True)
    capacidad_paquetes = models.PositiveSmallIntegerField(
        default=1,
        help_text='Capacidad de paquetes o pasajeros permitidos.',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_OFFLINE,
    )
    ubicacion_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    ubicacion_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
    )
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conductor {self.usuario.email} ({self.estado})"


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

class ProductoTienda(models.Model):
    TIPO_PRODUCTO = 'PRODUCTO'
    TIPO_SERVICIO = 'SERVICIO'
    TIPOS = [
        (TIPO_PRODUCTO, 'Producto'),
        (TIPO_SERVICIO, 'Servicio'),
    ]

    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(blank=True, null=True)
    tipo = models.CharField(max_length=15, choices=TIPOS, default=TIPO_PRODUCTO)
    imagen = models.ImageField(upload_to='productos_tienda/', blank=True, null=True)
    categoria = models.ForeignKey('Categoria', on_delete=models.SET_NULL, null=True, blank=True, related_name='productos_tienda')

    def __str__(self):
        return f"{self.nombre} - {self.tienda.nombre} ({self.tipo})"


class StoreOrder(models.Model):
    ESTADO_PENDIENTE = 'pending'
    ESTADO_EN_CURSO = 'ongoing'
    ESTADO_COMPLETADO = 'completed'
    ESTADO_CANCELADO = 'cancelled'

    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_CURSO, 'En curso'),
        (ESTADO_COMPLETADO, 'Completado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='store_orders')
    producto = models.ForeignKey(ProductoTienda, on_delete=models.CASCADE, related_name='orders')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"Orden #{self.id} - {self.usuario.email} -> {self.producto.nombre}"


class ServiceRequest(models.Model):
    TIPO_TAXI = 'taxi'
    TIPO_DELIVERY = 'delivery'
    TIPOS = [
        (TIPO_TAXI, 'Taxi'),
        (TIPO_DELIVERY, 'Delivery'),
    ]

    ESTADO_PENDIENTE = 'pending'
    ESTADO_ASIGNADO = 'assigned'
    ESTADO_EN_CURSO = 'in_progress'
    ESTADO_COMPLETADO = 'completed'
    ESTADO_CANCELADO = 'cancelled'
    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_ASIGNADO, 'Asignado'),
        (ESTADO_EN_CURSO, 'En curso'),
        (ESTADO_COMPLETADO, 'Completado'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPOS)
    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='solicitudes_cliente',
    )
    driver = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name='solicitudes_conductor',
        blank=True,
        null=True,
        limit_choices_to={'es_conductor': True},
    )
    store_order = models.ForeignKey(
        StoreOrder,
        on_delete=models.SET_NULL,
        related_name='service_requests',
        blank=True,
        null=True,
    )
    pickup_direccion = models.CharField(max_length=255, blank=True, null=True)
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    dropoff_direccion = models.CharField(max_length=255, blank=True, null=True)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_PENDIENTE,
    )
    distancia_metros = models.PositiveIntegerField(blank=True, null=True)
    duracion_segundos = models.PositiveIntegerField(blank=True, null=True)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    ruta_geojson = models.JSONField(blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    asignado_en = models.DateTimeField(blank=True, null=True)
    completado_en = models.DateTimeField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']

    def marcar_asignado(self, driver: Usuario | None = None):
        self.driver = driver
        self.estado = self.ESTADO_ASIGNADO
        self.asignado_en = timezone.now()
        self.save(update_fields=['driver', 'estado', 'asignado_en', 'actualizado'])

    def marcar_completado(self):
        self.estado = self.ESTADO_COMPLETADO
        self.completado_en = timezone.now()
        self.save(update_fields=['estado', 'completado_en', 'actualizado'])

    def __str__(self):
        return f"Servicio #{self.id} ({self.tipo}) - {self.estado}"


class StoreOrderReview(models.Model):
    order = models.OneToOneField(
        StoreOrder,
        on_delete=models.CASCADE,
        related_name='review',
    )
    producto = models.ForeignKey(
        ProductoTienda,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='store_order_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comentario = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"Reseña #{self.id} - Orden {self.order_id} ({self.rating} estrellas)"


class StoreOrderSellerReview(models.Model):
    order = models.OneToOneField(
        StoreOrder,
        on_delete=models.CASCADE,
        related_name='seller_review',
    )
    tienda = models.ForeignKey(
        Tienda,
        on_delete=models.CASCADE,
        related_name='seller_reviews',
    )
    comprador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='store_order_seller_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comentario = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"Reseña vendedor #{self.id} - Orden {self.order_id}"

class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto_tienda = models.ForeignKey('ProductoTienda', on_delete=models.CASCADE, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad} x {self.producto_tienda.nombre}"

    @property
    def subtotal(self) -> Decimal:
        return self.cantidad * self.producto_tienda.precio

class Pedido(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='pedidos')
    items = models.ManyToManyField(ItemCarrito)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    creado = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(default=False)

    def __str__(self):
        return f"Pedido {self.id} de {self.usuario.username}"


class ProductoFavorito(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='favoritos')
    producto = models.ForeignKey(ProductoTienda, on_delete=models.CASCADE, related_name='favoritado_por')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'producto')
        ordering = ['-creado']

    def __str__(self):
        return f"Favorito: {self.usuario.email} -> {self.producto.nombre}"


class Notificacion(models.Model):
    TIPO_FAVORITO = 'favorite'
    TIPO_ORDEN = 'order'
    TIPO_SERVICIO = 'service'
    TIPO_GENERAL = 'general'
    TIPOS = [
        (TIPO_FAVORITO, 'Favorito'),
        (TIPO_ORDEN, 'Orden'),
        (TIPO_SERVICIO, 'Servicio'),
        (TIPO_GENERAL, 'General'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default=TIPO_GENERAL)
    leido = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"{self.usuario.email} - {self.titulo}"

class Categoria(models.Model):
    TIPO_PRODUCTO = 'PRODUCTO'
    TIPO_SERVICIO = 'SERVICIO'
    TIPOS = [
        (TIPO_PRODUCTO, 'Producto'),
        (TIPO_SERVICIO, 'Servicio'),
    ]

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=15, choices=TIPOS, default=TIPO_PRODUCTO)
    thumbnail = models.ImageField(upload_to='categorias/', blank=True, null=True)

    def __str__(self):
        return self.nombre

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
