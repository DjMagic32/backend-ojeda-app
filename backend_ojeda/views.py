from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
import logging

# Configura el logger
logger = logging.getLogger(__name__)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return response
        except AuthenticationFailed as e:
            logger.error(f"Authentication failed: {str(e)}")
            return Response({"detail": str(e)}, status=401)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response({"detail": "An unexpected error occurred."}, status=400)
