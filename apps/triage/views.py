from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Triage, TriageQueue
from .serializers import (
    TriageSerializer, TriageListSerializer, TriageCreateSerializer,
    TriageQueueSerializer, TriageCompleteSerializer
)
from .filters import TriageFilter
from apps.accounts.permissions import IsDoctorOrNurse, IsAdminOrSuperAdmin
from apps.visits.models import Visit


class TriageViewSet(viewsets.ModelViewSet):
    """Comprehensive Triage ViewSet"""
    
    queryset = Triage.objects.select_related('visit', 'visit__patient', 'triage_officer')
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TriageFilter
    search_fields = ['visit__visit_number', 'visit__patient__first_name', 'visit__patient__last_name']
    ordering_fields = ['triage_start', 'priority', 'triage_score']
    ordering = ['-triage_start']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TriageListSerializer
        elif self.action == 'create':
            return TriageCreateSerializer
        elif self.action == 'complete_triage':
            return TriageCompleteSerializer
        return TriageSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(triage_start__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(triage_start__date__lte=date_to)
        
        # Today's triage
        today = self.request.query_params.get('today')
        if today and today.lower() == 'true':
            queryset = queryset.filter(triage_start__date=timezone.now().date())
        
        # Incomplete triage
        incomplete = self.request.query_params.get('incomplete')
        if incomplete and incomplete.lower() == 'true':
            queryset = queryset.filter(triage_completed__isnull=True)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def waiting_list(self, request):
        """Get patients waiting for triage"""
        waiting_visits = Visit.objects.filter(
            status__in=['check_in', 'registered'],
            triage_assessment__isnull=True
        ).select_related('patient').order_by('priority', 'check_in_time')
        
        waiting_list = []
        for idx, visit in enumerate(waiting_visits, 1):
            waiting_list.append({
                'position': idx,
                'visit_id': visit.id,
                'visit_number': visit.visit_number,
                'patient_name': visit.patient.full_name,
                'patient_age': visit.patient.age,
                'patient_gender': visit.patient.get_gender_display(),
                'priority': visit.priority,
                'arrival_time': visit.check_in_time or visit.registration_time,
                'waiting_minutes': int((timezone.now() - (visit.check_in_time or visit.registration_time)).total_seconds() / 60),
                'chief_complaint': visit.chief_complaint[:100] if visit.chief_complaint else ''
            })
        
        return Response({
            'total_waiting': len(waiting_list),
            'patients': waiting_list
        })
    
    @action(detail=True, methods=['post'])
    def start_triage(self, request, pk=None):
        """Start triage for a visit"""
        visit = Visit.objects.filter(id=pk).first()
        if not visit:
            return Response({'error': 'Visit not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if triage already exists
        if hasattr(visit, 'triage_assessment'):
            return Response({'error': 'Triage already started for this visit'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Create triage record
        triage = Triage.objects.create(
            visit=visit,
            triage_officer=request.user,
            triage_start=timezone.now()
        )
        
        # Update visit status
        visit.status = 'triage'
        visit.triage_time = timezone.now()
        visit.nurse = request.user
        visit.save()
        
        serializer = TriageSerializer(triage)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def complete_triage(self, request, pk=None):
        """Complete triage assessment"""
        triage = self.get_object()
        
        if triage.triage_completed:
            return Response({'error': 'Triage already completed'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        serializer = TriageCompleteSerializer(triage, data=request.data, partial=True)
        if serializer.is_valid():
            # Update triage with assessment data
            for field, value in serializer.validated_data.items():
                setattr(triage, field, value)
            
            # Calculate score and set priority
            triage.triage_score = triage.calculate_triage_score()
            triage.triage_completed = timezone.now()
            triage.completed_by = request.user
            triage.save()
            
            # Update visit priority based on triage
            if triage.priority == 'resuscitation':
                visit_priority = 'critical'
            elif triage.priority == 'emergency':
                visit_priority = 'emergency'
            elif triage.priority == 'urgent':
                visit_priority = 'urgent'
            else:
                visit_priority = 'routine'
            
            visit = triage.visit
            visit.priority = visit_priority
            visit.status = 'waiting'
            visit.save()
            
            return Response({
                'message': 'Triage completed successfully',
                'triage': TriageSerializer(triage).data,
                'priority': triage.get_priority_display(),
                'colour_code': triage.colour_code,
                'triage_score': triage.triage_score
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get triage statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        stats = {
            'today': {
                'total': Triage.objects.filter(triage_start__date=today).count(),
                'completed': Triage.objects.filter(triage_completed__date=today).count(),
                'by_priority': Triage.objects.filter(triage_start__date=today).values('priority').annotate(count=Count('id')),
                'average_score': Triage.objects.filter(triage_start__date=today).aggregate(Avg('triage_score'))['triage_score__avg'] or 0
            },
            'this_week': {
                'total': Triage.objects.filter(triage_start__date__gte=week_ago).count(),
                'by_priority': Triage.objects.filter(triage_start__date__gte=week_ago).values('priority').annotate(count=Count('id'))
            },
            'priority_distribution': {
                'resuscitation': Triage.objects.filter(priority='resuscitation').count(),
                'emergency': Triage.objects.filter(priority='emergency').count(),
                'urgent': Triage.objects.filter(priority='urgent').count(),
                'less_urgent': Triage.objects.filter(priority='less_urgent').count(),
                'non_urgent': Triage.objects.filter(priority='non_urgent').count()
            },
            'average_triage_time': Triage.objects.exclude(triage_completed__isnull=True).aggregate(
                avg_time=Avg('triage_completed') - Avg('triage_start')
            )['avg_time']
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def vitals_summary(self, request, pk=None):
        """Get vitals summary for triage"""
        triage = self.get_object()
        
        vitals = {
            'temperature': float(triage.temperature) if triage.temperature else None,
            'heart_rate': triage.heart_rate,
            'respiratory_rate': triage.respiratory_rate,
            'blood_pressure': f"{triage.systolic_bp}/{triage.diastolic_bp}" if triage.systolic_bp and triage.diastolic_bp else None,
            'oxygen_saturation': triage.oxygen_saturation,
            'blood_glucose': float(triage.blood_glucose) if triage.blood_glucose else None,
            'pain_score': triage.pain_score,
            'avpu_score': triage.get_avpu_score_display(),
            'glasgow_coma_score': triage.glasgow_coma_score
        }
        
        return Response(vitals)
    
    @action(detail=True, methods=['post'])
    def add_to_queue(self, request, pk=None):
        """Add patient to department queue after triage"""
        triage = self.get_object()
        department = request.data.get('department', 'consultation')
        
        # Create queue entry
        queue_position = TriageQueue.objects.filter(
            visit__status='waiting',
            completed_at__isnull=True
        ).count() + 1
        
        queue = TriageQueue.objects.create(
            visit=triage.visit,
            position=queue_position,
            estimated_wait_time=queue_position * 15  # 15 minutes per patient
        )
        
        return Response({
            'message': f'Patient added to {department} queue',
            'position': queue_position,
            'estimated_wait_time': queue.estimated_wait_time
        })


class TriageQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing triage queue"""
    
    queryset = TriageQueue.objects.select_related('visit', 'visit__patient')
    serializer_class = TriageQueueSerializer
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]
    
    @action(detail=True, methods=['post'])
    def call_patient(self, request, pk=None):
        """Call patient for triage"""
        queue_entry = self.get_object()
        queue_entry.called_at = timezone.now()
        queue_entry.save()
        
        return Response({
            'message': f'Patient {queue_entry.visit.patient.full_name} called for triage',
            'called_at': queue_entry.called_at
        })
    
    @action(detail=True, methods=['post'])
    def start_triage(self, request, pk=None):
        """Start triage for queue entry"""
        queue_entry = self.get_object()
        queue_entry.started_at = timezone.now()
        queue_entry.save()
        
        return Response({
            'message': 'Triage started',
            'started_at': queue_entry.started_at
        })
    
    @action(detail=True, methods=['post'])
    def complete_queue(self, request, pk=None):
        """Complete queue entry"""
        queue_entry = self.get_object()
        queue_entry.completed_at = timezone.now()
        queue_entry.save()
        
        # Reorder remaining queue
        remaining = TriageQueue.objects.filter(
            position__gt=queue_entry.position,
            completed_at__isnull=True
        )
        for item in remaining:
            item.position -= 1
            item.save()
        
        return Response({'message': 'Queue entry completed'})