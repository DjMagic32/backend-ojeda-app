from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from .models import Producto, Categoria, Carrito, ItemCarrito, Pedido, Tienda, ProductoTienda, Comentario, ComentarioProducto, Referencia, Wallet, Usuario
from .serializers import (
    ProductoSerializer, CategoriaSerializer, CarritoSerializer, ItemCarritoSerializer,
    PedidoSerializer, TiendaSerializer, ProductoTiendaSerializer, ComentarioSerializer,
    ComentarioProductoSerializer, ReferenciaSerializer, WalletSerializer, UsuarioSerializer,
    WalletActionSerializer
)
from .permissions import EsTienda

class CreateUserView(APIView):
    permission_classes = [permissions.AllowAny]  # Permitir acceso sin token

    def post(self, request, *args, **kwargs):
        serializer = UsuarioSerializer(data=request.data)
        if serializer.is_valid():
            # The email uniqueness check is now handled by the serializer if 'email' has UniqueValidator
            # or if the model field 'email' unique=True is respected by ModelSerializer.
            # The manual check can be removed:
            # email = data.get('email', '').strip().lower()
            # if Usuario.objects.filter(email=email).exists():
            #     return Response({'error': 'El correo ya está en uso.'}, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save() # The serializer's create method handles password hashing and username

            # Logic for Tienda creation
            if user.rol == Usuario.ES_TIENDA:
                tienda_data = {
                    'usuario': user.id, # Use user.id from the saved instance
                    'nombre': request.data.get('nombre_tienda', ''),
                    'direccion': request.data.get('direccion', ''),
                    'telefono': request.data.get('telefono_tienda', ''),
                    'informacion_fiscal': request.data.get('informacion_fiscal', ''),
                }
                tienda_serializer = TiendaSerializer(data=tienda_data)
                if tienda_serializer.is_valid():
                    tienda_serializer.save()
                    # Return the user serializer data (which now excludes password)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    user.delete()  # Clean up created user if tienda creation fails
                    return Response(tienda_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Producto.objects.select_related('categoria').all()
    serializer_class = ProductoSerializer

class CarritoView(APIView):
    '''Handles operations related to the user's shopping cart.'''
    permission_classes = [IsAuthenticated]
    def get(self, request):
        carrito, _ = Carrito.objects.prefetch_related('items__producto').get_or_create(usuario=request.user)
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

    def post(self, request):
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto = Producto.objects.get(id=request.data['producto_id'])
        item, created = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
        if not created:
            item.cantidad += request.data.get('cantidad', 1)
            item.save()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        producto = Producto.objects.get(id=request.data['producto_id'])
        item = ItemCarrito.objects.get(carrito=carrito, producto=producto)
        item.delete()
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

class PedidoView(APIView):
    '''Manages creating new orders from the cart and listing user's orders.'''
    permission_classes = [IsAuthenticated]
    def post(self, request):
        carrito = Carrito.objects.get(usuario=request.user)
        items = carrito.items.all()
        if not items:
            return Response({'error': 'El carrito está vacío.'}, status=status.HTTP_400_BAD_REQUEST)

        total = sum(item.subtotal for item in items)
        pedido = Pedido.objects.create(usuario=request.user, total=total)
        pedido.items.set(items)
        carrito.items.all().delete()  # Vaciar el carrito
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('items__producto')
        serializer = PedidoSerializer(pedidos, many=True)
        return Response(serializer.data)

class TiendaViewSet(viewsets.ModelViewSet):
    
    permission_classes = [IsAuthenticated, EsTienda]
    queryset = Tienda.objects.select_related('usuario').all()
    serializer_class = TiendaSerializer

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class ProductoTiendaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, EsTienda]
    queryset = ProductoTienda.objects.select_related('tienda__usuario').all()
    serializer_class = ProductoTiendaSerializer

    def perform_create(self, serializer):
        # Assumes that a Tienda instance already exists for this user,
        # which should be ensured during user registration if rol is TIENDA.
        tienda = Tienda.objects.get(usuario=self.request.user)
        serializer.save(tienda=tienda)

class ComentarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Comentario.objects.select_related('tienda', 'usuario').all()
    serializer_class = ComentarioSerializer

class ComentarioProductoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ComentarioProducto.objects.select_related('usuario', 'producto__categoria').all()
    serializer_class = ComentarioProductoSerializer

class ReferenciaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Referencia.objects.select_related('usuario', 'tienda', 'producto__categoria').all()
    serializer_class = ReferenciaSerializer

class WalletViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

class WalletActionView(APIView):
    '''Allows users to perform actions on their wallet, primarily adding funds.'''
    permission_classes = [IsAuthenticated]
    def post(self, request):
        action_serializer = WalletActionSerializer(data=request.data)
        if action_serializer.is_valid():
            wallet, _ = Wallet.objects.get_or_create(usuario=request.user) # Consider get_or_create
            amount = action_serializer.validated_data['amount'] # Use validated data

            # Add logic here if you need to distinguish between deposit/withdrawal based on amount or another field
            wallet.saldo += amount
            wallet.save()

            response_serializer = WalletSerializer(wallet)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(action_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UsuarioDetalleView(APIView):
    '''Provides detailed information about the authenticated user, including Tienda details if applicable.'''
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Autenticar el usuario usando el token
        user = request.user  # Dado que estamos usando JWT, el usuario ya está autenticado

        # Serializar la información del usuario
        usuario_serializer = UsuarioSerializer(user)

        # Eliminar la contraseña de los datos serializados
        usuario_data = usuario_serializer.data
        # if 'password' in usuario_data: # This block can be removed
        #     del usuario_data['password']

        # Verificar si el usuario es una tienda
        tienda_data = None
        if user.rol == Usuario.ES_TIENDA:
            try:
                tienda = Tienda.objects.get(usuario=user)
                tienda_serializer = TiendaSerializer(tienda)
                tienda_data = tienda_serializer.data
            except Tienda.DoesNotExist:
                return Response({'error': 'Tienda no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        # Devolver los datos del usuario y, si es una tienda, también los de la tienda
        response_data = usuario_data
        if tienda_data:
            response_data['tienda'] = tienda_data

        return Response(response_data, status=status.HTTP_200_OK)

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = 'http://localhost:8000/accounts/google/login/callback/' # Update if necessary

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = self.user
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UsuarioSerializer(user).data
            })
        return response

from .models import ChatRoom, ChatMessage # Added
from .serializers import ChatRoomSerializer, ChatMessageSerializer # Added
from rest_framework.decorators import action # Added
from django.db.models import Q, Max # Added for complex queries & ordering
from rest_framework.pagination import PageNumberPagination # Added for message pagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users should only see chat rooms they are participants in
        # Order by the 'updated_at' field of the ChatRoom, which is updated by new messages
        return self.request.user.chat_rooms.annotate(
            last_message_timestamp=Max('messages__timestamp')
        ).order_by('-last_message_timestamp', '-updated_at')


    def perform_create(self, serializer):
        # Ensure the creating user is part of the participants
        # The client should send a list of 'participant_ids'
        participant_ids = self.request.data.get('participants', [])
        participants = list(Usuario.objects.filter(id__in=participant_ids))

        # Ensure the creator is in the participants list
        if self.request.user not in participants:
            participants.append(self.request.user)

        # Prevent creating a room with only one participant (the creator)
        if len(participants) < 2:
            raise serializers.ValidationError("A chat room must have at least two participants.")

        # Check if a room with these exact participants already exists to avoid duplicates
        # This check can be complex for groups. For 1-on-1, it's simpler.
        # For simplicity, we'll allow multiple rooms for same group for now, or client can check first.
        # A more robust solution would involve a unique constraint or a more complex lookup.

        chat_room = serializer.save()
        chat_room.participants.set(participants)

class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Filter messages by room_id provided in the URL (achieved via nested routing or query param)
        # And ensure the user is a participant of that room.
        room_id = self.kwargs.get('room_pk') # Assuming nested routing: /chat_rooms/{room_pk}/messages/
        if not room_id:
            # Fallback or error if room_id is not in URL (e.g. if using as a query parameter)
            room_id_query = self.request.query_params.get('room_id')
            if not room_id_query:
                 return ChatMessage.objects.none() # Or raise an error
            room_id = room_id_query


        # Check if user is part of the room
        if not ChatRoom.objects.filter(id=room_id, participants=self.request.user).exists():
            return ChatMessage.objects.none() # Or raise PermissionDenied

        return ChatMessage.objects.filter(room_id=room_id).order_by('-timestamp')

    def perform_create(self, serializer):
        # Message sending should ideally be via WebSockets for real-time.
        # This HTTP endpoint can be a fallback or for specific message types not sent via WS.
        room_id = self.request.data.get('room') # Expect room ID in request data

        try:
            room = ChatRoom.objects.get(id=room_id)
            if not room.participants.filter(id=self.request.user.id).exists():
                raise serializers.ValidationError("You are not a participant of this chat room.")
        except ChatRoom.DoesNotExist:
            raise serializers.ValidationError("ChatRoom not found.")

        # The consumer will handle broadcasting. Here we just save.
        # If using this endpoint to send, you might want to trigger a channel layer send manually:
        # from channels.layers import get_channel_layer
        # from asgiref.sync import async_to_sync
        # channel_layer = get_channel_layer()
        # async_to_sync(channel_layer.group_send)(...)

        serializer.save(sender=self.request.user, room=room)

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeCreatePaymentIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            pedido_id = request.data.get('pedido_id')
            if not pedido_id:
                return Response({'error': 'Pedido ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                pedido = Pedido.objects.get(id=pedido_id, usuario=request.user, estado_pago='PENDING')
            except Pedido.DoesNotExist:
                return Response({'error': 'Pedido no encontrado o ya procesado.'}, status=status.HTTP_404_NOT_FOUND)

            # Amount in cents
            amount = int(pedido.total * 100)

            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd', # Or your desired currency
                metadata={'pedido_id': pedido.id, 'user_id': request.user.id},
                # automatic_payment_methods={'enabled': True}, # Recommended by Stripe
            )

            pedido.payment_intent_id = intent.id
            pedido.save()

            return Response({
                'clientSecret': intent.client_secret,
                'paymentIntentId': intent.id
            }, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'An unexpected error occurred: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        pedido_id = payment_intent.metadata.get('pedido_id')
        try:
            pedido = Pedido.objects.get(id=pedido_id, payment_intent_id=payment_intent.id)
            pedido.estado_pago = 'PAID'
            # Add any other post-payment logic here (e.g., send confirmation email, update inventory)
            pedido.save()
        except Pedido.DoesNotExist:
            print(f"Webhook error: Pedido not found for payment_intent {payment_intent.id}")
            return HttpResponse(status=404) # Or log and return 200 if Stripe should not retry

    elif event.type == 'payment_intent.payment_failed':
        payment_intent = event.data.object
        pedido_id = payment_intent.metadata.get('pedido_id')
        try:
            pedido = Pedido.objects.get(id=pedido_id, payment_intent_id=payment_intent.id)
            pedido.estado_pago = 'FAILED'
            pedido.save()
        except Pedido.DoesNotExist:
            print(f"Webhook error: Pedido not found for payment_intent {payment_intent.id}")
            # Potentially log this, but return 200 so Stripe doesn't retry for a pedido that might not exist.
            return HttpResponse(status=200)

    # ... handle other event types
    else:
        print('Unhandled event type {}'.format(event.type))

    return HttpResponse(status=200)

import time
import hashlib
import hmac
import json
import requests # Ensure requests is imported if not already

class BinanceCreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def _generate_signature(self, data_string):
        return hmac.new(
            settings.BINANCE_SECRET_KEY.encode('utf-8'),
            data_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest().upper() # Binance Pay often uses SHA512, verify this

    def post(self, request, *args, **kwargs):
        pedido_id = request.data.get('pedido_id')
        if not pedido_id:
            return Response({'error': 'Pedido ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pedido = Pedido.objects.get(id=pedido_id, usuario=request.user, estado_pago='PENDING')
        except Pedido.DoesNotExist:
            return Response({'error': 'Pedido no encontrado o ya procesado.'}, status=status.HTTP_404_NOT_FOUND)

        # Construct payload for Binance Pay API - this is highly dependent on their API
        # Refer to official Binance Pay "Create Order" API documentation
        nonce = str(int(time.time() * 1000)) # Example nonce
        payload_body = {
            "env": {"terminalType": "APP"}, # Or "WEB", "WAP", "MINI_PROGRAM"
            "merchantTradeNo": f"{pedido.id}_{nonce}", # Unique order ID for merchant
            "orderAmount": str(pedido.total), # Amount as string
            "currency": "USDT", # Or BUSD, etc. - currency supported by your Binance Pay account
            "goodsDetails": [{ # Example, adjust as needed
                "goodsType": "01", # 01: Tangible, 02: Virtual
                "goodsCategory": "ECommerce",
                "referenceGoodsId": str(p.producto.id),
                "goodsName": p.producto.nombre,
                # "goodsDetail": p.producto.descripcion # Optional
            } for p in pedido.items.all()],
            # "returnUrl": "your_app_return_url_after_payment", # Optional client-side redirect
            # "notifyUrl": "your_backend_webhook_url_for_binance", # Important for server notifications
            # ... other required parameters
        }

        # Binance API request structure: timestamp, nonce, signature in headers
        # Body is JSON string. Signature is usually on (timestamp + nonce + request_body_string)
        # This is a common pattern, VERIFY with Binance Pay docs.

        timestamp = str(int(time.time() * 1000))
        request_body_string = json.dumps(payload_body)
        string_to_sign = f"{timestamp}\n{nonce}\n{request_body_string}\n"
        signature = self._generate_signature(string_to_sign)

        headers = {
            'Content-Type': 'application/json',
            'BinancePay-Timestamp': timestamp,
            'BinancePay-Nonce': nonce,
            'BinancePay-Certificate-SN': settings.BINANCE_API_KEY, # This is usually the API Key
            'BinancePay-Signature': signature.upper()
        }

        try:
            # Example endpoint, replace with actual Binance Pay Create Order API endpoint
            # It's often something like /binancepay/openapi/v2/order or similar
            api_url = f"{settings.BINANCE_PAY_BASE_URL}/binancepay/openapi/v1/order" # Verify exact endpoint

            response = requests.post(api_url, headers=headers, data=request_body_string, timeout=10)
            response.raise_for_status() # Raise an exception for HTTP errors

            binance_response_data = response.json()

            if binance_response_data.get('status') == 'SUCCESS':
                # Store relevant info, e.g., binance's order ID (prepayId is common)
                prepay_id = binance_response_data.get('data', {}).get('prepayId')
                if not prepay_id:
                     return Response({'error': 'Binance prepayId not found in response.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                pedido.binance_order_id = prepay_id
                # Optionally store merchantTradeNo if you want to query by it later
                # pedido.merchant_trade_no = payload_body["merchantTradeNo"]
                pedido.save()

                # The response to the client should include what's needed to launch Binance App/SDK
                # This might be the `checkoutUrl` or other parameters from `binance_response_data.data`
                return Response({
                    'message': 'Binance order created successfully.',
                    'binance_order_id': prepay_id,
                    'checkout_details': binance_response_data.get('data') # Send relevant part to frontend
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'Binance Pay API error.',
                    'details': binance_response_data.get('errorMessage', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            return Response({'error': f'Binance API request failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
def binance_webhook(request):
    # Binance webhook security: verify signature (HMAC-SHA512 or similar)
    # The exact mechanism depends on Binance Pay documentation.
    # It typically involves checking a signature in headers against the payload and your secret key.

    # Example: (This is a general idea, actual verification is critical and specific to Binance)
    # received_signature = request.headers.get('Binancepay-Signature') # Or similar header
    # payload_body = request.body.decode('utf-8')
    # if not verify_binance_signature(payload_body, received_signature, settings.BINANCE_SECRET_KEY):
    #     return HttpResponse('Invalid signature', status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON payload', status=400)

    # Process the notification based on `bizStatus` or similar field
    # E.g., "PAY_SUCCESS", "PAY_FAIL", "PAY_CLOSED"
    biz_status = data.get('bizStatus')
    # merchant_trade_no = data.get('merchantTradeNo') # Your unique order ID
    prepay_id = data.get('prepayId') # Binance's transaction ID

    if not prepay_id: # Or use merchant_trade_no if that's what you stored / can query by
        print("Webhook error: prepayId not found in Binance notification.")
        return HttpResponse('Missing prepayId', status=400)

    try:
        # Query using binance_order_id (prepayId)
        pedido = Pedido.objects.get(binance_order_id=prepay_id)
    except Pedido.DoesNotExist:
        print(f"Webhook error: Pedido not found for Binance prepayId {prepay_id}")
        # Return 200 to acknowledge receipt and prevent retries for non-existent orders
        return HttpResponse('Pedido not found, acknowledged.', status=200)

    if biz_status == 'PAY_SUCCESS':
        pedido.estado_pago = 'PAID'
        # Add other post-payment logic
        pedido.save()
        print(f"Pedido {pedido.id} marked as PAID via Binance webhook.")
    elif biz_status in ['PAY_FAIL', 'PAY_CLOSED']: # Or other failure statuses
        pedido.estado_pago = 'FAILED'
        pedido.save()
        print(f"Pedido {pedido.id} marked as FAILED via Binance webhook (status: {biz_status}).")
    else:
        print(f"Unhandled Binance webhook bizStatus: {biz_status} for pedido {pedido.id}")

    # Binance expects a specific response format for success, usually JSON.
    # Example: {"returnCode": "SUCCESS", "returnMessage": null}
    # Consult Binance Pay documentation for the exact required response.
    return HttpResponse(json.dumps({"returnCode": "SUCCESS", "returnMessage": None}), content_type='application/json', status=200)


from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter

class AppleLogin(SocialLoginView):
    adapter_class = AppleOAuth2Adapter
    client_class = OAuth2Client # Can reuse OAuth2Client
    callback_url = 'http://localhost:8000/accounts/apple/login/callback/' # Update if necessary

    def post(self, request, *args, **kwargs):
        # The frontend should send 'id_token' and optionally 'code' from Apple
        # dj_rest_auth SocialLoginView expects 'access_token' or 'code'
        # We might need to adjust this if Apple provides the token differently
        # For now, assuming the frontend can pass the id_token as 'access_token'
        # or we might need a custom adapter if the flow is very different.

        # If Apple sends 'id_token', we can rename it to 'access_token' for dj_rest_auth
        if 'id_token' in request.data and 'access_token' not in request.data:
            request.data['access_token'] = request.data['id_token']

        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = self.user
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UsuarioSerializer(user).data
            })
        return response
