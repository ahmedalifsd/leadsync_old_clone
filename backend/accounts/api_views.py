from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import UserProfile
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserUpdateSerializer,
    UserProfileUpdateSerializer, PasswordChangeSerializer, UserProfileSerializer
)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Registration successful. Please log in.'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """Login user"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user)
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    
    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Logout user"""
    logout(request)
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """Get current user information"""
    return Response(UserSerializer(request.user).data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    user = request.user
    
    # Update user fields
    user_serializer = UserUpdateSerializer(user, data=request.data, partial=True)
    if user_serializer.is_valid():
        user_serializer.save()
    
    # Update profile fields
    profile = user.profile
    profile_data = {
        'phone_number': request.data.get('phone_number', profile.phone_number),
        'company_name': request.data.get('company_name', profile.company_name),
    }
    profile_serializer = UserProfileUpdateSerializer(profile, data=profile_data, partial=True)
    if profile_serializer.is_valid():
        profile_serializer.save()
    
    return Response(UserSerializer(user).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """Change user password"""
    serializer = PasswordChangeSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def check_username(request):
    """Check if username is available"""
    username = request.query_params.get('username', '')
    
    if not username:
        return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    available = not User.objects.filter(username=username).exists()
    return Response({'available': available})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def check_email(request):
    """Check if email is available"""
    email = request.query_params.get('email', '')
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    available = not User.objects.filter(email=email).exists()
    return Response({'available': available})


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing users (read-only for security)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see other users in the system (not full details)
        return User.objects.all()
