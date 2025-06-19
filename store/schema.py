import graphene
from graphene_django import DjangoObjectType
from .models import Usuario, Tienda, Producto, Categoria, Pedido, Carrito, ItemCarrito, Comentario, ComentarioProducto, Referencia, Wallet, ProductoTienda

# Object Types
class UsuarioType(DjangoObjectType):
    class Meta:
        model = Usuario
        fields = "__all__" # In a real app, exclude sensitive fields like password

class TiendaType(DjangoObjectType):
    class Meta:
        model = Tienda
        fields = "__all__"

class ProductoTiendaType(DjangoObjectType):
    class Meta:
        model = ProductoTienda
        fields = "__all__"

class CarritoType(DjangoObjectType):
    class Meta:
        model = Carrito
        fields = "__all__"

class ItemCarritoType(DjangoObjectType):
    class Meta:
        model = ItemCarrito
        fields = "__all__"

class PedidoType(DjangoObjectType):
    class Meta:
        model = Pedido
        fields = "__all__"

class CategoriaType(DjangoObjectType):
    class Meta:
        model = Categoria
        fields = "__all__"

class ProductoType(DjangoObjectType):
    class Meta:
        model = Producto
        fields = "__all__"

class ComentarioType(DjangoObjectType):
    class Meta:
        model = Comentario
        fields = "__all__"

class ComentarioProductoType(DjangoObjectType):
    class Meta:
        model = ComentarioProducto
        fields = "__all__"

class ReferenciaType(DjangoObjectType):
    class Meta:
        model = Referencia
        fields = "__all__"

class WalletType(DjangoObjectType):
    class Meta:
        model = Wallet
        fields = "__all__"

# Query Type
class Query(graphene.ObjectType):
    all_usuarios = graphene.List(UsuarioType)
    usuario_by_id = graphene.Field(UsuarioType, id=graphene.Int(required=True))
    all_tiendas = graphene.List(TiendaType)
    tienda_by_id = graphene.Field(TiendaType, id=graphene.Int(required=True))
    all_producto_tiendas = graphene.List(ProductoTiendaType)
    producto_tienda_by_id = graphene.Field(ProductoTiendaType, id=graphene.Int(required=True))
    all_carritos = graphene.List(CarritoType)
    carrito_by_id = graphene.Field(CarritoType, id=graphene.Int(required=True))
    all_item_carritos = graphene.List(ItemCarritoType)
    item_carrito_by_id = graphene.Field(ItemCarritoType, id=graphene.Int(required=True))
    all_pedidos = graphene.List(PedidoType)
    pedido_by_id = graphene.Field(PedidoType, id=graphene.Int(required=True))
    all_categorias = graphene.List(CategoriaType)
    categoria_by_id = graphene.Field(CategoriaType, id=graphene.Int(required=True))
    all_productos = graphene.List(ProductoType)
    producto_by_id = graphene.Field(ProductoType, id=graphene.Int(required=True))
    all_comentarios = graphene.List(ComentarioType)
    comentario_by_id = graphene.Field(ComentarioType, id=graphene.Int(required=True))
    all_comentario_productos = graphene.List(ComentarioProductoType)
    comentario_producto_by_id = graphene.Field(ComentarioProductoType, id=graphene.Int(required=True))
    all_referencias = graphene.List(ReferenciaType)
    referencia_by_id = graphene.Field(ReferenciaType, id=graphene.Int(required=True))
    all_wallets = graphene.List(WalletType)
    wallet_by_id = graphene.Field(WalletType, id=graphene.Int(required=True))
    me = graphene.Field(UsuarioType)

    def resolve_all_usuarios(root, info):
        return Usuario.objects.all()
    def resolve_usuario_by_id(root, info, id):
        try: return Usuario.objects.get(pk=id)
        except Usuario.DoesNotExist: return None
    def resolve_all_tiendas(root, info):
        return Tienda.objects.all()
    def resolve_tienda_by_id(root, info, id):
        try: return Tienda.objects.get(pk=id)
        except Tienda.DoesNotExist: return None
    def resolve_all_producto_tiendas(root, info):
        return ProductoTienda.objects.all()
    def resolve_producto_tienda_by_id(root, info, id):
        try: return ProductoTienda.objects.get(pk=id)
        except ProductoTienda.DoesNotExist: return None
    def resolve_all_carritos(root, info):
        return Carrito.objects.all()
    def resolve_carrito_by_id(root, info, id):
        try: return Carrito.objects.get(pk=id)
        except Carrito.DoesNotExist: return None
    def resolve_all_item_carritos(root, info):
        return ItemCarrito.objects.all()
    def resolve_item_carrito_by_id(root, info, id):
        try: return ItemCarrito.objects.get(pk=id)
        except ItemCarrito.DoesNotExist: return None
    def resolve_all_pedidos(root, info):
        return Pedido.objects.all()
    def resolve_pedido_by_id(root, info, id):
        try: return Pedido.objects.get(pk=id)
        except Pedido.DoesNotExist: return None
    def resolve_all_categorias(root, info):
        return Categoria.objects.all()
    def resolve_categoria_by_id(root, info, id):
        try: return Categoria.objects.get(pk=id)
        except Categoria.DoesNotExist: return None
    def resolve_all_productos(root, info):
        return Producto.objects.all()
    def resolve_producto_by_id(root, info, id):
        try: return Producto.objects.get(pk=id)
        except Producto.DoesNotExist: return None
    def resolve_all_comentarios(root, info):
        return Comentario.objects.all()
    def resolve_comentario_by_id(root, info, id):
        try: return Comentario.objects.get(pk=id)
        except Comentario.DoesNotExist: return None
    def resolve_all_comentario_productos(root, info):
        return ComentarioProducto.objects.all()
    def resolve_comentario_producto_by_id(root, info, id):
        try: return ComentarioProducto.objects.get(pk=id)
        except ComentarioProducto.DoesNotExist: return None
    def resolve_all_referencias(root, info):
        return Referencia.objects.all()
    def resolve_referencia_by_id(root, info, id):
        try: return Referencia.objects.get(pk=id)
        except Referencia.DoesNotExist: return None
    def resolve_all_wallets(root, info):
        return Wallet.objects.all()
    def resolve_wallet_by_id(root, info, id):
        try: return Wallet.objects.get(pk=id)
        except Wallet.DoesNotExist: return None

    def resolve_me(root, info):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required!")
        return user

# Input Object Types for Mutations
class UsuarioInput(graphene.InputObjectType):
    email = graphene.String(required=True)
    username = graphene.String(required=True)
    password = graphene.String(required=True)
    rol = graphene.String(default_value=Usuario.ES_CLIENTE)
    # Optional fields
    first_name = graphene.String()
    last_name = graphene.String()
    edad = graphene.Int()
    genero = graphene.String() # Consider using an Enum for choices
    telefono = graphene.String()
    cedula_pasaporte = graphene.String()
    # foto_identificacion: Handled separately if using file uploads
    ingresos_minimos_mensuales = graphene.Decimal()

class TiendaInput(graphene.InputObjectType):
    usuario_id = graphene.Int(required=True)
    nombre = graphene.String(required=True)
    direccion = graphene.String()
    telefono = graphene.String()
    # logo: Handled separately if using file uploads
    informacion_fiscal = graphene.String()

# Mutations
class CreateUsuarioMutation(graphene.Mutation):
    class Arguments:
        input = UsuarioInput(required=True)

    usuario = graphene.Field(UsuarioType)

    @classmethod
    def mutate(cls, root, info, input):
        user = Usuario(
            email=input.email,
            username=input.username,
            rol=input.rol,
            first_name=input.first_name if input.first_name else '',
            last_name=input.last_name if input.last_name else '',
            edad=input.edad,
            genero=input.genero,
            telefono=input.telefono,
            cedula_pasaporte=input.cedula_pasaporte,
            ingresos_minimos_mensuales=input.ingresos_minimos_mensuales
        )
        user.set_password(input.password)
        user.save()
        return CreateUsuarioMutation(usuario=user)

class CreateTiendaMutation(graphene.Mutation):
    class Arguments:
        input = TiendaInput(required=True)

    tienda = graphene.Field(TiendaType)

    @classmethod
    def mutate(cls, root, info, input):
        try:
            usuario = Usuario.objects.get(pk=input.usuario_id, rol=Usuario.ES_TIENDA)
        except Usuario.DoesNotExist:
            # Or raise an error: raise Exception("Usuario tienda no encontrado o rol incorrecto.")
            return None

        tienda = Tienda(
            usuario=usuario,
            nombre=input.nombre,
            direccion=input.direccion,
            telefono=input.telefono,
            informacion_fiscal=input.informacion_fiscal
        )
        tienda.save()
        return CreateTiendaMutation(tienda=tienda)

class Mutation(graphene.ObjectType):
    create_usuario = CreateUsuarioMutation.Field()
    create_tienda = CreateTiendaMutation.Field()
    # update_usuario = UpdateUsuarioMutation.Field() # Placeholder for future
    # update_tienda = UpdateTiendaMutation.Field() # Placeholder for future

# Schema
# The main schema will be defined in the project-level schema.py
# For now, this file defines the types, query, and mutations for the 'store' app.
