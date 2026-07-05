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
    # False para usuarios creados vía Google que aún no completan el formulario de registro.
    registro_completo = models.BooleanField(default=True)

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
    cedula_foto_frente = models.ImageField(
        upload_to='conductores/cedulas/', blank=True, null=True
    )
    cedula_foto_reverso = models.ImageField(
        upload_to='conductores/cedulas/', blank=True, null=True
    )
    licencia_foto = models.ImageField(
        upload_to='conductores/licencias/', blank=True, null=True
    )
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conductor {self.usuario.email} ({self.estado})"

    @property
    def is_complete(self) -> bool:
        usuario = self.usuario
        required = (
            self.licencia_numero,
            self.vehiculo_tipo,
            self.vehiculo_placa,
            self.vehiculo_color,
            usuario.telefono,
            usuario.cedula_pasaporte,
        )
        campos_ok = all(value not in (None, "") for value in required)
        fotos_ok = bool(
            self.cedula_foto_frente and self.cedula_foto_reverso and self.licencia_foto
        )
        return campos_ok and fotos_ok


class Tienda(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': Usuario.ES_TIENDA})
    nombre = models.CharField(max_length=200)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    informacion_fiscal = models.TextField(blank=True, null=True)
    ubicacion_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    ubicacion_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    ubicacion_actualizada = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

MONEDA_USD = 'USD'
MONEDA_VES = 'VES'
MONEDAS = [
    (MONEDA_USD, 'Dólares (USD)'),
    (MONEDA_VES, 'Bolívares (VES)'),
]


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
    moneda = models.CharField(max_length=3, choices=MONEDAS, default=MONEDA_USD)
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
    moneda = models.CharField(max_length=3, choices=MONEDAS, default=MONEDA_USD)
    tasa_aplicada = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
        help_text='Tasa USD→VES vigente al crear la orden (snapshot).',
    )
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
    TIPO_MENSAJE = 'message'
    TIPO_GENERAL = 'general'
    TIPOS = [
        (TIPO_FAVORITO, 'Favorito'),
        (TIPO_ORDEN, 'Orden'),
        (TIPO_SERVICIO, 'Servicio'),
        (TIPO_MENSAJE, 'Mensaje'),
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
    data = models.JSONField(blank=True, null=True)
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


class Conversation(models.Model):
    """Conversación 1-a-1 entre dos usuarios (típicamente cliente <-> tienda).

    Se asocia opcionalmente a un producto para dar contexto al chat iniciado
    desde la ficha de producto.
    """

    participantes = models.ManyToManyField(
        Usuario,
        related_name='conversaciones',
    )
    producto = models.ForeignKey(
        ProductoTienda,
        on_delete=models.SET_NULL,
        related_name='conversaciones',
        blank=True,
        null=True,
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-actualizado']

    def __str__(self):
        return f"Conversación #{self.id}"

    @classmethod
    def get_or_create_between(cls, user_a: Usuario, user_b: Usuario, producto: 'ProductoTienda | None' = None):
        """Devuelve la conversación existente entre dos usuarios o crea una nueva.

        Si se pasa producto, se prefiere una conversación que coincida con ese producto.
        """
        qs = cls.objects.filter(participantes=user_a).filter(participantes=user_b)
        if producto is not None:
            existente = qs.filter(producto=producto).first()
            if existente:
                return existente, False
        existente = qs.filter(producto__isnull=True).first() if producto is None else qs.first()
        if existente:
            return existente, False
        conversacion = cls.objects.create(producto=producto)
        conversacion.participantes.set([user_a, user_b])
        return conversacion, True


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='mensajes',
    )
    autor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='mensajes_enviados',
    )
    contenido = models.TextField()
    leido = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['creado']
        indexes = [
            models.Index(fields=['conversation', 'creado']),
        ]

    def __str__(self):
        return f"Mensaje #{self.id} de {self.autor.email}"


class TasaCambio(models.Model):
    """Tasa de conversión USD→VES vigente en una fecha dada.

    El sistema toma siempre el registro más reciente (`-creado`) como tasa activa.
    Se registran manualmente por un admin/staff (ej. tasa BCV del día).
    """

    FUENTE_BCV = 'BCV'
    FUENTE_PARALELO = 'PARALELO'
    FUENTE_MANUAL = 'MANUAL'
    FUENTES = [
        (FUENTE_BCV, 'BCV'),
        (FUENTE_PARALELO, 'Paralelo'),
        (FUENTE_MANUAL, 'Manual'),
    ]

    valor_bs = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text='Cuántos bolívares equivalen a 1 USD.',
    )
    fuente = models.CharField(max_length=15, choices=FUENTES, default=FUENTE_BCV)
    registrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name='tasas_registradas',
        blank=True,
        null=True,
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado']
        indexes = [models.Index(fields=['-creado'])]

    def __str__(self):
        return f"1 USD = {self.valor_bs} VES ({self.fuente}, {self.creado:%Y-%m-%d %H:%M})"

    @classmethod
    def vigente(cls) -> 'TasaCambio | None':
        return cls.objects.order_by('-creado').first()


class ExpoPushToken(models.Model):
    """Token de Expo Push Notifications asociado a un usuario y dispositivo."""

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='push_tokens',
    )
    token = models.CharField(max_length=255, unique=True)
    plataforma = models.CharField(max_length=20, blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PushToken {self.usuario.email} ({self.token[:12]}…)"


class PasswordResetCode(models.Model):
    """Código OTP de 6 dígitos para recuperación de contraseña."""

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='password_reset_codes',
    )
    codigo = models.CharField(max_length=6)
    creado = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)
    intentos = models.PositiveSmallIntegerField(default=0)

    VALIDEZ_MINUTOS = 15
    MAX_INTENTOS = 5

    class Meta:
        ordering = ['-creado']

    def esta_vigente(self) -> bool:
        from datetime import timedelta
        if self.usado or self.intentos >= self.MAX_INTENTOS:
            return False
        return timezone.now() <= self.creado + timedelta(minutes=self.VALIDEZ_MINUTOS)

    def __str__(self):
        return f"ResetCode {self.usuario.email} ({'usado' if self.usado else 'activo'})"
