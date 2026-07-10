from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as django_login
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Q, Count, Avg
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
import uuid
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Department, UserSession, AuditLog
from .serializers import (
    UserSerializer, 
    UserCreateSerializer, 
    UserUpdateSerializer,
    DepartmentSerializer, 
    UserSessionSerializer, 
    AuditLogSerializer,
    ChangePasswordSerializer, 
    LoginSerializer,
    UserRegistrationSerializer
)
from .permissions import (
    IsAdminOrSuperAdmin, 
    IsOwnerOrAdmin, 
    IsAuthenticatedAndActive,
    IsDoctorOrNurse,
    IsLabTechnician,
    IsPharmacist,
    CanViewPatient,
    CanEditPatient
)
from .utils import (
    generate_otp, 
    send_otp_email, 
    send_otp_sms, 
    get_client_ip, 
    log_user_activity
)


class UserViewSet(viewsets.ModelViewSet):
    """Comprehensive User management viewset"""
    
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__id=department)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(employee_number__icontains=search)
            )
        
        return queryset.select_related('department').prefetch_related('groups')
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAuthenticatedAndActive])
    def me(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated, IsAuthenticatedAndActive])
    def update_me(self, request):
        """Update current user profile"""
        serializer = UserUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def reset_password(self, request, pk=None):
        """Reset user password (admin only)"""
        user = self.get_object()
        new_password = request.data.get('new_password')
        if not new_password:
            return Response(
                {'error': 'New password required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.save()
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='update',
            model_name='User',
            object_id=str(user.id),
            object_repr=str(user),
            changes={'password': 'reset'},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        return Response({'message': 'Password reset successfully'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def toggle_active(self, request, pk=None):
        """Activate or deactivate user"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        return Response({'status': 'active' if user.is_active else 'inactive'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def unlock_account(self, request, pk=None):
        """Unlock a locked account"""
        user = self.get_object()
        user.reset_login_attempts()
        return Response({'message': 'Account unlocked successfully'})
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def sessions(self, request, pk=None):
        """Get user sessions"""
        user = self.get_object()
        sessions = UserSession.objects.filter(user=user, is_active=True)
        serializer = UserSessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def terminate_sessions(self, request, pk=None):
        """Terminate all user sessions except current"""
        user = self.get_object()
        UserSession.objects.filter(user=user, is_active=True).exclude(
            session_key=request.session.session_key
        ).update(is_active=False, logout_time=timezone.now())
        return Response({'message': 'All other sessions terminated'})


class DepartmentViewSet(viewsets.ModelViewSet):
    """Department management viewset"""
    
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(type=type_filter)
        
        return queryset.prefetch_related('users')
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def users(self, request, pk=None):
        """Get all users in a department"""
        department = self.get_object()
        users = department.users.all()
        serializer = UserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def statistics(self, request, pk=None):
        """Get department statistics"""
        department = self.get_object()
        stats = {
            'total_users': department.users.count(),
            'active_users': department.users.filter(is_active=True).count(),
            'online_users': department.users.filter(is_online=True).count(),
            'users_by_role': department.users.values('role').annotate(count=Count('id')),
        }
        return Response(stats)


class AuthViewSet(viewsets.GenericViewSet):
    """Authentication endpoints with role-based dashboard redirection"""
    
    permission_classes = [AllowAny]
    serializer_class = None
    
    def _get_dashboard_url(self, role):
        """Get dashboard URL based on user role"""
        dashboard_map = {
            'super_admin': '/dashboard/',
            'admin': '/dashboard/',
            'doctor': '/dashboard/doctor/',
            'clinical_officer': '/dashboard/doctor/',
            'nurse': '/dashboard/nurse/',
            'lab_technician': '/dashboard/lab/',
            'pharmacist': '/dashboard/pharmacy/',
            'pharmacy_tech': '/dashboard/pharmacy/',
            'records_officer': '/dashboard/records/',
            'receptionist': '/dashboard/reception/',
            'cashier': '/dashboard/cashier/',
            'manager': '/dashboard/manager/',
            'viewer': '/dashboard/viewer/',
        }
        return dashboard_map.get(role, '/dashboard/')
    
    def _create_user_session(self, request, user):
        """Helper method to create user session with duplicate handling"""
        session_key = None
        if hasattr(request, 'session') and request.session.session_key:
            session_key = request.session.session_key
        else:
            session_key = str(uuid.uuid4())
        
        # Try to create session, handle duplicate key
        try:
            return UserSession.objects.create(
                user=user,
                session_key=session_key,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
        except IntegrityError:
            # Session key exists, generate new one
            new_session_key = str(uuid.uuid4())
            return UserSession.objects.create(
                user=user,
                session_key=new_session_key,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user (admin/super_admin cannot register)"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Auto-login after registration
            django_login(request, user)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Create session record
            self._create_user_session(request, user)
            
            # Log the action
            AuditLog.objects.create(
                user=user,
                action='register',
                model_name='User',
                object_id=str(user.id),
                object_repr=str(user),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Get dashboard URL based on role
            dashboard_url = self._get_dashboard_url(user.role)
            
            # Return response with JWT tokens and dashboard redirect info
            return Response({
                'success': True,
                'message': 'Registration successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user, context={'request': request}).data,
                'dashboard_url': dashboard_url,
                'role': user.role
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login with 2FA support and JWT tokens"""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            
            if user is None:
                return Response(
                    {'error': 'Invalid credentials'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if user.account_locked:
                return Response(
                    {'error': 'Account is locked. Contact administrator.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not user.is_active:
                return Response(
                    {'error': 'Account is disabled'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check for 2FA
            if user.two_factor_enabled:
                otp = generate_otp()
                cache.set(f'2fa_{user.id}', otp, timeout=300)
                
                # Send OTP via email/SMS based on user preference
                if user.receive_sms_notifications and user.phone_number:
                    send_otp_sms(user.phone_number, otp)
                else:
                    send_otp_email(user.email, otp)
                
                request.session['2fa_user_id'] = user.id
                return Response({
                    'requires_2fa': True, 
                    'message': 'OTP sent to your registered contact',
                    'user_id': user.id
                })
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Login successful
            user.reset_login_attempts()
            user.update_last_activity()
            
            # Create Django session login
            django_login(request, user)
            
            # Create session record using helper method
            session = self._create_user_session(request, user)
            
            # Log the action
            AuditLog.objects.create(
                user=user,
                action='login',
                model_name='User',
                object_id=str(user.id),
                object_repr=str(user),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Get dashboard URL based on role
            dashboard_url = self._get_dashboard_url(user.role)
            
            # Return response with JWT tokens and dashboard redirect info
            return Response({
                'message': 'Login successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user, context={'request': request}).data,
                'session_id': session.session_key,
                'dashboard_url': dashboard_url,
                'role': user.role,
                'redirect': True
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_2fa(self, request):
        """Verify 2FA code and return JWT tokens with role-based redirect"""
        otp = request.data.get('otp')
        user_id = request.session.get('2fa_user_id')
        
        if not user_id:
            return Response(
                {'error': 'Session expired'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = get_object_or_404(User, id=user_id)
        cached_otp = cache.get(f'2fa_{user.id}')
        
        if cached_otp and cached_otp == otp:
            cache.delete(f'2fa_{user.id}')
            del request.session['2fa_user_id']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Complete login process
            user.reset_login_attempts()
            user.update_last_activity()
            
            # Create Django session login
            django_login(request, user)
            
            # Create session record using helper method
            self._create_user_session(request, user)
            
            # Get dashboard URL based on role
            dashboard_url = self._get_dashboard_url(user.role)
            
            # Return response with JWT tokens
            return Response({
                'message': '2FA verification successful',
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user, context={'request': request}).data,
                'dashboard_url': dashboard_url,
                'role': user.role,
                'redirect': True
            })
        
        user.increment_login_attempts()
        return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAuthenticatedAndActive])
    def logout(self, request):
        """User logout"""
        session_key = request.session.session_key
        if session_key:
            UserSession.objects.filter(session_key=session_key).update(
                is_active=False, 
                logout_time=timezone.now()
            )
        
        AuditLog.objects.create(
            user=request.user,
            action='logout',
            model_name='User',
            object_id=str(request.user.id),
            object_repr=str(request.user),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        logout(request)
        return Response({'message': 'Logged out successfully'})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAuthenticatedAndActive])
    def change_password(self, request):
        """Change user password"""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.password_changed_at = timezone.now()
            user.save()
            
            # Terminate all sessions
            UserSession.objects.filter(user=user).update(is_active=False)
            
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAuthenticatedAndActive])
    def enable_2fa(self, request):
        """Enable two-factor authentication"""
        user = request.user
        secret = generate_otp()
        user.two_factor_secret = secret
        user.two_factor_enabled = True
        user.save()
        
        return Response({'secret': secret, 'message': '2FA enabled successfully'})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAuthenticatedAndActive])
    def disable_2fa(self, request):
        """Disable two-factor authentication"""
        request.user.two_factor_enabled = False
        request.user.two_factor_secret = ''
        request.user.save()
        
        return Response({'message': '2FA disabled successfully'})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def get_dashboard_url(self, request):
        """Get dashboard URL for current user"""
        dashboard_url = self._get_dashboard_url(request.user.role)
        return Response({
            'dashboard_url': dashboard_url,
            'role': request.user.role,
            'redirect_url': dashboard_url
        })


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for viewing audit logs"""
    
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin, IsAuthenticatedAndActive]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user__id=user_id)
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by model
        model = self.request.query_params.get('model')
        if model:
            queryset = queryset.filter(model_name=model)
        
        # Date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset.select_related('user')