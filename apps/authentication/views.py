from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user).data,
            "message": "User and Tenant created successfully."
        }, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from shared.utils.email_service import get_email_service
from .models import User
from .serializers import UserInviteSerializer, UserRoleUpdateSerializer
from django.contrib.auth.tokens import default_token_generator
from .tasks import send_invite_email_task
import uuid

class IsOrgAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        is_auth = super().has_permission(request, view)
        return is_auth and request.user.role in ['SUPER_ADMIN', 'ORG_ADMIN']

class OrgUsersListView(generics.ListAPIView):
    """Listar todos los usuarios del Tenant actual."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(tenant=self.request.user.tenant)

class UserInviteView(APIView):
    """Invitar a un usuario a la organización."""
    permission_classes = [IsOrgAdmin]

    def post(self, request):
        serializer = UserInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        role = serializer.validated_data['role']

        if User.objects.filter(email=email).exists():
            return Response({'error': 'El usuario ya existe en el sistema.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create user with unusable password
        username = f"{email.split('@')[0]}_{uuid.uuid4().hex[:8]}"
        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
            tenant=request.user.tenant,
            role=role
        )

        # Generate token for "Set Your Password" flow
        token = default_token_generator.make_token(user)
        reset_link = f"{request.scheme}://{request.get_host()}/set-password/?token={token}&email={email}"
        
        subject = f"Invitación a Fleet SaaS - {request.user.tenant.name}"
        message = f"Hola, has sido invitado a Fleet SaaS con el rol de {role}.\n\nPor favor, ingresa al siguiente enlace para configurar tu contraseña y activar tu cuenta:\n\n{reset_link}"
        
        # Dispatch email asynchronously using Celery
        send_invite_email_task.delay(email, subject, message)

        return Response({'status': 'Invitación enviada', 'email': email, 'role': role}, status=status.HTTP_201_CREATED)

class UserRoleUpdateView(generics.UpdateAPIView):
    """Actualizar el rol de un usuario dentro del Tenant."""
    serializer_class = UserRoleUpdateSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        return User.objects.filter(tenant=self.request.user.tenant)
