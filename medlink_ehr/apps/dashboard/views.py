from django.db.models import F
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import DashboardWidget, UserDashboard, UserDashboardWidget, Notification
from .serializers import (
    DashboardWidgetSerializer, UserDashboardSerializer,
    UserDashboardWidgetSerializer, NotificationSerializer
)
from apps.accounts.permissions import IsAdminOrSuperAdmin


class DashboardViewSet(viewsets.GenericViewSet):
    """Dashboard data and configuration with role-based routing"""
    
    queryset = UserDashboard.objects.all()
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action == 'dashboard_html':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'my_dashboard':
            return UserDashboardSerializer
        elif self.action == 'widgets':
            return DashboardWidgetSerializer
        return None
    
    def _get_dashboard_url(self, role):
        """Get dashboard URL based on user role"""
        dashboard_map = {
            'super_admin': '/dashboard/admin/',
            'admin': '/dashboard/admin/',
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
    
    def get_user_role_dashboard(self, user):
        """Determine which dashboard template to use based on user role"""
        if not user.is_authenticated:
            return 'login.html'
        
        role = user.role
        template_map = {
            'super_admin': 'dashboard/admin_dashboard.html',
            'admin': 'dashboard/admin_dashboard.html',
            'doctor': 'dashboard/doctor_dashboard.html',
            'clinical_officer': 'dashboard/doctor_dashboard.html',
            'nurse': 'dashboard/nurse_dashboard.html',
            'lab_technician': 'dashboard/lab_dashboard.html',
            'pharmacist': 'dashboard/pharmacy_dashboard.html',
            'pharmacy_tech': 'dashboard/pharmacy_dashboard.html',
            'records_officer': 'dashboard/records_dashboard.html',
            'receptionist': 'dashboard/reception_dashboard.html',
            'cashier': 'dashboard/cashier_dashboard.html',
            'manager': 'dashboard/manager_dashboard.html',
            'viewer': 'dashboard/viewer_dashboard.html',
        }
        return template_map.get(role, 'dashboard/index.html')
    
    def get_dashboard_context(self, request):
        """Get context data for dashboard templates"""
        context = {
            'user': request.user,
            'role': request.user.role if request.user.is_authenticated else None,
            'full_name': request.user.get_full_name() if request.user.is_authenticated else None,
            'today': timezone.now().date(),
            'current_time': timezone.now(),
        }
        
        if not request.user.is_authenticated:
            return context
        
        # Add role-specific context
        role = request.user.role
        
        if role in ['super_admin', 'admin', 'manager']:
            from apps.accounts.models import User
            context['total_users'] = User.objects.filter(is_active=True).count()
            context['active_sessions'] = User.objects.filter(is_online=True).count()
            context['is_admin'] = True  # Flag for admin in template
        
        elif role in ['doctor', 'clinical_officer']:
            from apps.visits.models import Visit
            context['today_patients'] = Visit.objects.filter(
                primary_doctor=request.user,
                registration_time__date=timezone.now().date()
            ).count()
            context['waiting_patients'] = Visit.objects.filter(
                primary_doctor=request.user,
                status__in=['waiting', 'triage']
            ).count()
        
        elif role == 'nurse':
            from apps.visits.models import Visit
            context['triage_queue'] = Visit.objects.filter(
                status__in=['registered', 'check_in', 'triage', 'waiting']
            ).count()
        
        elif role == 'lab_technician':
            from apps.laboratory.models import LabRequest
            context['pending_tests'] = LabRequest.objects.filter(
                assigned_to=request.user,
                status__in=['pending', 'collected']
            ).count()
        
        elif role in ['pharmacist', 'pharmacy_tech']:
            from apps.pharmacy.models import Prescription
            context['pending_prescriptions'] = Prescription.objects.filter(status='pending').count()
        
        elif role == 'receptionist':
            from apps.visits.models import Visit
            context['today_registrations'] = Visit.objects.filter(
                registration_time__date=timezone.now().date()
            ).count()
        
        elif role == 'cashier':
            from apps.visits.models import Visit
            context['today_revenue'] = Visit.objects.filter(
                registration_time__date=timezone.now().date()
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        elif role == 'viewer':
            from apps.patients.models import Patient
            from apps.visits.models import Visit
            context['total_patients'] = Patient.objects.count()
            context['today_visits'] = Visit.objects.filter(registration_time__date=timezone.now().date()).count()
        
        return context
    
    @action(detail=False, methods=['get'])
    def dashboard_html(self, request):
        """Serve role-specific dashboard HTML page"""
        if not request.user.is_authenticated:
            return redirect('/login/')
        
        # Get the template directly based on role - NO REDIRECT LOOP
        template = self.get_user_role_dashboard(request.user)
        context = self.get_dashboard_context(request)
        return render(request, template, context)
    
    @action(detail=False, methods=['get'])
    def my_dashboard(self, request):
        """Get user's dashboard configuration"""
        dashboard, created = UserDashboard.objects.get_or_create(user=request.user)
        serializer = UserDashboardSerializer(dashboard)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update_layout(self, request):
        """Update dashboard layout"""
        dashboard, created = UserDashboard.objects.get_or_create(user=request.user)
        dashboard.layout = request.data.get('layout', {})
        dashboard.save()
        return Response({'message': 'Layout updated'})
    
    @action(detail=False, methods=['get'])
    def widgets(self, request):
        """Get available widgets for user"""
        widgets = DashboardWidget.objects.filter(
            Q(is_visible=True) &
            (Q(visible_to_roles__contains=[request.user.role]) | Q(visible_to_roles=[]))
        ).order_by('order')
        
        serializer = DashboardWidgetSerializer(widgets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics - role-based"""
        today = timezone.now().date()
        user = request.user
        role = user.role
        
        from apps.patients.models import Patient
        from apps.visits.models import Visit
        from apps.admissions.models import Admission, Ward
        from apps.laboratory.models import LabRequest
        from apps.pharmacy.models import Prescription, Medication
        
        # Role-based data filtering
        if role in ['super_admin', 'admin', 'manager']:
            # Full access
            total_patients = Patient.objects.count()
            patients_today = Patient.objects.filter(created_at__date=today).count()
            visits_today = Visit.objects.filter(registration_time__date=today).count()
            waiting_patients = Visit.objects.filter(status__in=['waiting', 'triage']).count()
            current_admissions = Admission.objects.filter(status__in=['admitted', 'in_treatment', 'stable', 'critical']).count()
            pending_labs = LabRequest.objects.filter(status__in=['pending', 'collected']).count()
            pending_prescriptions = Prescription.objects.filter(status='pending').count()
            low_stock = Medication.objects.filter(current_stock__lte=F('reorder_level')).count()
            revenue_today = Visit.objects.filter(registration_time__date=today).aggregate(total=Sum('amount_paid'))['total'] or 0
            revenue_month = Visit.objects.filter(registration_time__month=today.month).aggregate(total=Sum('amount_paid'))['total'] or 0
            
        elif role in ['doctor', 'clinical_officer']:
            total_patients = Patient.objects.filter(
                visits__primary_doctor=user
            ).distinct().count()
            patients_today = Patient.objects.filter(
                visits__primary_doctor=user,
                visits__registration_time__date=today
            ).distinct().count()
            visits_today = Visit.objects.filter(primary_doctor=user, registration_time__date=today).count()
            waiting_patients = Visit.objects.filter(primary_doctor=user, status__in=['waiting', 'triage']).count()
            current_admissions = Admission.objects.filter(admitting_doctor=user, status__in=['admitted', 'in_treatment', 'stable', 'critical']).count()
            pending_labs = LabRequest.objects.filter(requesting_doctor=user, status__in=['pending', 'collected']).count()
            pending_prescriptions = Prescription.objects.filter(prescribing_doctor=user, status='pending').count()
            low_stock = 0
            revenue_today = 0
            revenue_month = 0
            
        elif role == 'nurse':
            total_patients = Patient.objects.filter(
                visits__triage_assessment__triage_officer=user
            ).distinct().count()
            patients_today = Patient.objects.filter(
                visits__triage_assessment__triage_officer=user,
                visits__registration_time__date=today
            ).distinct().count()
            visits_today = Visit.objects.filter(nurse=user, registration_time__date=today).count()
            waiting_patients = Visit.objects.filter(status__in=['waiting', 'triage']).count()
            current_admissions = Admission.objects.filter(status__in=['admitted', 'in_treatment', 'stable', 'critical']).count()
            pending_labs = LabRequest.objects.filter(status__in=['pending', 'collected']).count()
            pending_prescriptions = Prescription.objects.filter(status='pending').count()
            low_stock = Medication.objects.filter(current_stock__lte=F('reorder_level')).count()
            revenue_today = 0
            revenue_month = 0
            
        elif role == 'lab_technician':
            total_patients = Patient.objects.filter(
                lab_requests__assigned_to=user
            ).distinct().count()
            patients_today = 0
            visits_today = 0
            waiting_patients = 0
            current_admissions = 0
            pending_labs = LabRequest.objects.filter(assigned_to=user, status__in=['pending', 'collected']).count()
            completed_today = LabRequest.objects.filter(assigned_to=user, completed_at__date=today).count()
            pending_prescriptions = 0
            low_stock = 0
            revenue_today = 0
            revenue_month = 0
            
        elif role in ['pharmacist', 'pharmacy_tech']:
            total_patients = 0
            patients_today = 0
            visits_today = 0
            waiting_patients = 0
            current_admissions = 0
            pending_labs = 0
            pending_prescriptions = Prescription.objects.filter(status='pending').count()
            low_stock = Medication.objects.filter(current_stock__lte=F('reorder_level')).count()
            dispensed_today = Prescription.objects.filter(dispensed_at__date=today).count()
            revenue_today = Prescription.objects.filter(dispensed_at__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
            revenue_month = Prescription.objects.filter(dispensed_at__month=today.month).aggregate(total=Sum('total_amount'))['total'] or 0
            
        elif role == 'receptionist':
            total_patients = Patient.objects.count()
            patients_today = Patient.objects.filter(created_at__date=today).count()
            visits_today = Visit.objects.filter(registration_time__date=today).count()
            waiting_patients = Visit.objects.filter(status__in=['waiting', 'triage']).count()
            current_admissions = 0
            pending_labs = 0
            pending_prescriptions = 0
            low_stock = 0
            appointments_today = Visit.objects.filter(appointment_time__date=today).count()
            revenue_today = 0
            revenue_month = 0
            
        elif role == 'cashier':
            total_patients = Patient.objects.count()
            patients_today = 0
            visits_today = Visit.objects.filter(registration_time__date=today).count()
            waiting_patients = 0
            current_admissions = 0
            pending_labs = 0
            pending_prescriptions = 0
            low_stock = 0
            revenue_today = Visit.objects.filter(registration_time__date=today).aggregate(total=Sum('amount_paid'))['total'] or 0
            revenue_month = Visit.objects.filter(registration_time__month=today.month).aggregate(total=Sum('amount_paid'))['total'] or 0
            
        else:
            total_patients = Patient.objects.count()
            patients_today = Patient.objects.filter(created_at__date=today).count()
            visits_today = Visit.objects.filter(registration_time__date=today).count()
            waiting_patients = Visit.objects.filter(status__in=['waiting', 'triage']).count()
            current_admissions = 0
            pending_labs = 0
            pending_prescriptions = 0
            low_stock = 0
            revenue_today = 0
            revenue_month = 0
        
        stats = {
            'patients': {
                'total': total_patients,
                'today': patients_today,
                'this_week': 0,
                'by_gender': []
            },
            'visits': {
                'today': visits_today,
                'waiting': waiting_patients,
                'completed': 0,
                'average_wait_time': 0,
                'appointments': appointments_today if role == 'receptionist' else 0
            },
            'admissions': {
                'current': current_admissions,
                'today': 0,
                'available_beds': Ward.objects.aggregate(total=Sum('capacity'))['total'] - current_admissions if role in ['super_admin', 'admin', 'manager'] else 0
            },
            'laboratory': {
                'pending': pending_labs,
                'today': completed_today if role == 'lab_technician' else 0,
                'urgent': 0
            },
            'pharmacy': {
                'pending_prescriptions': pending_prescriptions,
                'low_stock': low_stock,
                'today_dispensed': dispensed_today if role in ['pharmacist', 'pharmacy_tech'] else 0
            },
            'revenue': {
                'today': revenue_today,
                'this_month': revenue_month
            }
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def my_patients(self, request):
        """Get patients assigned to the current doctor"""
        user = request.user
        
        if user.role not in ['doctor', 'clinical_officer']:
            return Response({'error': 'Not authorized'}, status=403)
        
        from apps.patients.models import Patient
        from apps.patients.serializers import PatientListSerializer
        
        patients = Patient.objects.filter(
            visits__primary_doctor=user
        ).distinct().order_by('-created_at')[:20]
        
        serializer = PatientListSerializer(patients, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_appointments(self, request):
        """Get today's appointments for the current doctor"""
        user = request.user
        today = timezone.now().date()
        
        if user.role not in ['doctor', 'clinical_officer']:
            return Response({'error': 'Not authorized'}, status=403)
        
        from apps.visits.models import Visit
        from apps.visits.serializers import VisitListSerializer
        
        appointments = Visit.objects.filter(
            primary_doctor=user,
            registration_time__date=today
        ).order_by('registration_time')
        
        serializer = VisitListSerializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def triage_queue(self, request):
        """Get triage queue for nurses"""
        from apps.visits.models import Visit
        from apps.visits.serializers import VisitListSerializer
        
        queue = Visit.objects.filter(
            status__in=['registered', 'check_in', 'triage', 'waiting']
        ).order_by('priority', 'registration_time')[:20]
        
        serializer = VisitListSerializer(queue, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_lab_results(self, request):
        """Get pending lab results for doctors"""
        user = request.user
        
        if user.role not in ['doctor', 'clinical_officer']:
            return Response({'error': 'Not authorized'}, status=403)
        
        from apps.laboratory.models import LabRequest
        from apps.laboratory.serializers import LabRequestListSerializer
        
        pending = LabRequest.objects.filter(
            requesting_doctor=user,
            status__in=['processing', 'completed']
        ).exclude(status='verified').order_by('-created_at')[:20]
        
        serializer = LabRequestListSerializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """Get key performance indicators - role-based"""
        today = timezone.now().date()
        last_month = today - timedelta(days=30)
        user = request.user
        role = user.role
        
        from apps.visits.models import Visit
        from apps.laboratory.models import LabRequest
        
        if role in ['super_admin', 'admin', 'manager']:
            current_visits = Visit.objects.filter(registration_time__date__gte=last_month).count()
            previous_visits = Visit.objects.filter(registration_time__date__range=[last_month - timedelta(days=30), last_month]).count()
            avg_wait_time = Visit.objects.filter(registration_time__date__gte=last_month).aggregate(avg=Avg('total_waiting_time'))['avg'] or 0
            
            completed_labs = LabRequest.objects.filter(completed_at__date__gte=last_month)
            lab_turnaround = 0
            if completed_labs.exists():
                total_hours = 0
                count = 0
                for lab in completed_labs:
                    if lab.created_at and lab.completed_at:
                        hours = (lab.completed_at - lab.created_at).total_seconds() / 3600
                        total_hours += hours
                        count += 1
                if count > 0:
                    lab_turnaround = round(total_hours / count, 1)
            
            revenue_growth = 0
            if previous_visits > 0:
                revenue_growth = ((current_visits - previous_visits) / previous_visits * 100)
                
        elif role in ['doctor', 'clinical_officer']:
            current_visits = Visit.objects.filter(primary_doctor=user, registration_time__date__gte=last_month).count()
            previous_visits = Visit.objects.filter(primary_doctor=user, registration_time__date__range=[last_month - timedelta(days=30), last_month]).count()
            avg_wait_time = Visit.objects.filter(primary_doctor=user, registration_time__date__gte=last_month).aggregate(avg=Avg('total_waiting_time'))['avg'] or 0
            completed_labs = LabRequest.objects.filter(requesting_doctor=user, completed_at__date__gte=last_month)
            lab_turnaround = 0
            if completed_labs.exists():
                total_hours = 0
                count = 0
                for lab in completed_labs:
                    if lab.created_at and lab.completed_at:
                        hours = (lab.completed_at - lab.created_at).total_seconds() / 3600
                        total_hours += hours
                        count += 1
                if count > 0:
                    lab_turnaround = round(total_hours / count, 1)
            revenue_growth = ((current_visits - previous_visits) / previous_visits * 100) if previous_visits > 0 else 0
            
        else:
            current_visits = Visit.objects.filter(registration_time__date__gte=last_month).count()
            previous_visits = Visit.objects.filter(registration_time__date__range=[last_month - timedelta(days=30), last_month]).count()
            avg_wait_time = 0
            lab_turnaround = 0
            revenue_growth = 0
        
        kpis = {
            'patient_satisfaction': {'value': 87.5, 'trend': '+2.3%', 'target': 90},
            'average_wait_time': {'value': round(avg_wait_time, 1), 'trend': '-15%', 'target': 20},
            'bed_occupancy_rate': {'value': 78.5, 'trend': '+5.2%', 'target': 85},
            'readmission_rate': {'value': 12.3, 'trend': '-2.1%', 'target': 10},
            'lab_turnaround_time': {'value': lab_turnaround, 'trend': '-8%', 'target': 24},
            'revenue_growth': {'value': round(revenue_growth, 1), 'trend': '+12%', 'target': 15}
        }
        
        return Response(kpis)
    
    @action(detail=False, methods=['get'])
    def activity_feed(self, request):
        """Get recent activity feed"""
        from apps.accounts.models import AuditLog
        
        activities = AuditLog.objects.select_related('user').order_by('-timestamp')[:20]
        
        feed = []
        for activity in activities:
            feed.append({
                'id': activity.id,
                'user': activity.user.get_full_name() if activity.user else 'System',
                'action': activity.action,
                'model': activity.model_name,
                'object': activity.object_repr[:50] if activity.object_repr else '',
                'timestamp': activity.timestamp.isoformat(),
                'time_ago': self._time_ago(activity.timestamp)
            })
        
        return Response(feed)
    
    def _time_ago(self, timestamp):
        """Calculate time ago string"""
        now = timezone.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"


class NotificationViewSet(viewsets.ModelViewSet):
    """Notification management ViewSet"""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only notifications for the current user"""
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        notifications = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'message': 'All notifications marked as read'})
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Clear all notifications"""
        deleted_count = self.get_queryset().delete()
        return Response({'message': f'{deleted_count[0]} notifications cleared'})
    
    def perform_create(self, serializer):
        serializer.save(recipient=self.request.user)


# Error handler views
def handler400(request, exception=None):
    from django.shortcuts import render
    context = {'request_path': request.path, 'exception': str(exception) if exception else None}
    return render(request, '400.html', context, status=400)


def handler403(request, exception=None):
    from django.shortcuts import render
    context = {'request_path': request.path, 'exception': str(exception) if exception else None}
    return render(request, '403.html', context, status=403)


def handler404(request, exception=None):
    from django.shortcuts import render
    context = {'request_path': request.path, 'exception': str(exception) if exception else None}
    return render(request, '404.html', context, status=404)


def handler500(request):
    from django.shortcuts import render
    context = {'request_path': request.path if request else None}
    return render(request, '500.html', context, status=500)