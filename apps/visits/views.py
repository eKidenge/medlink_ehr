from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Visit, ClinicalNote, Vitals
from .serializers import (
    VisitSerializer, VisitListSerializer, VisitCreateSerializer,
    VisitUpdateSerializer, ClinicalNoteSerializer, VitalsSerializer,
    VisitCheckInSerializer
)
from .filters import VisitFilter
from apps.accounts.permissions import CanViewPatient, CanEditPatient


class VisitViewSet(viewsets.ModelViewSet):
    """Comprehensive Visit ViewSet"""
    
    queryset = Visit.objects.select_related('patient', 'primary_doctor', 'created_by')
    permission_classes = [IsAuthenticated, CanViewPatient]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = VisitFilter
    search_fields = ['visit_number', 'patient__first_name', 'patient__last_name', 'patient__phone_primary']
    ordering_fields = ['registration_time', 'check_in_time', 'status', 'priority']
    ordering = ['-registration_time']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return VisitListSerializer
        elif self.action == 'create':
            return VisitCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return VisitUpdateSerializer
        elif self.action == 'check_in':
            return VisitCheckInSerializer
        return VisitSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by doctor
        doctor_id = self.request.query_params.get('doctor')
        if doctor_id:
            queryset = queryset.filter(primary_doctor_id=doctor_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(registration_time__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(registration_time__date__lte=date_to)
        
        # Filter by visit type
        visit_type = self.request.query_params.get('visit_type')
        if visit_type:
            queryset = queryset.filter(visit_type=visit_type)
        
        # Today's visits
        today = self.request.query_params.get('today')
        if today and today.lower() == 'true':
            queryset = queryset.filter(registration_time__date=timezone.now().date())
        
        # Waiting patients
        waiting = self.request.query_params.get('waiting')
        if waiting and waiting.lower() == 'true':
            queryset = queryset.filter(status__in=['waiting', 'triage'])
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def check_in(self, request):
        """Patient check-in - create or update visit"""
        serializer = VisitCheckInSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            if data.get('visit_id'):
                visit = Visit.objects.get(id=data['visit_id'])
                visit.status = 'check_in'
                visit.check_in_time = timezone.now()
                visit.save()
            else:
                # Create new visit
                visit = Visit.objects.create(
                    patient_id=data['patient_id'],
                    visit_type=data.get('visit_type', 'outpatient'),
                    chief_complaint=data.get('chief_complaint', ''),
                    status='check_in',
                    check_in_time=timezone.now(),
                    created_by=request.user
                )
            
            return Response({
                'message': 'Patient checked in successfully',
                'visit': VisitSerializer(visit).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get visit timeline with all events"""
        visit = self.get_object()
        
        timeline = []
        
        # Registration
        timeline.append({
            'event': 'Registration',
            'time': visit.registration_time,
            'user': visit.created_by.get_full_name() if visit.created_by else None
        })
        
        # Check-in
        if visit.check_in_time:
            timeline.append({
                'event': 'Check-in',
                'time': visit.check_in_time,
                'user': None
            })
        
        # Triage
        if visit.triage_time:
            timeline.append({
                'event': 'Triage',
                'time': visit.triage_time,
                'user': visit.nurse.get_full_name() if visit.nurse else None
            })
        
        # Consultation
        if visit.consultation_start:
            timeline.append({
                'event': 'Consultation Started',
                'time': visit.consultation_start,
                'user': visit.primary_doctor.get_full_name() if visit.primary_doctor else None
            })
        
        if visit.consultation_end:
            timeline.append({
                'event': 'Consultation Ended',
                'time': visit.consultation_end,
                'user': visit.primary_doctor.get_full_name() if visit.primary_doctor else None
            })
        
        # Completion
        if visit.completion_time:
            timeline.append({
                'event': 'Visit Completed',
                'time': visit.completion_time,
                'user': None
            })
        
        return Response(timeline)
    
    @action(detail=True, methods=['post'])
    def add_vitals(self, request, pk=None):
        """Add or update vitals for visit"""
        visit = self.get_object()
        
        # Check if vitals already exist
        vitals, created = Vitals.objects.get_or_create(visit=visit)
        
        serializer = VitalsSerializer(vitals, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(recorded_by=request.user)
            
            # Update visit status if needed
            if visit.status == 'check_in':
                visit.status = 'triage'
                visit.triage_time = timezone.now()
                visit.save()
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_clinical_note(self, request, pk=None):
        """Add clinical note to visit"""
        visit = self.get_object()
        
        serializer = ClinicalNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(visit=visit, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def clinical_notes(self, request, pk=None):
        """Get all clinical notes for visit"""
        visit = self.get_object()
        notes = visit.clinical_notes_detail.all()
        serializer = ClinicalNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_consultation(self, request, pk=None):
        """Start consultation for visit"""
        visit = self.get_object()
        
        if visit.status not in ['triage', 'waiting']:
            return Response({'error': 'Visit must be in triage or waiting status'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        visit.status = 'consultation'
        visit.consultation_start = timezone.now()
        visit.primary_doctor = request.user
        visit.save()
        
        # Calculate waiting times
        visit.calculate_waiting_times()
        
        return Response({'message': 'Consultation started', 'visit': VisitSerializer(visit).data})
    
    @action(detail=True, methods=['post'])
    def end_consultation(self, request, pk=None):
        """End consultation for visit"""
        visit = self.get_object()
        
        if visit.status != 'consultation':
            return Response({'error': 'Visit must be in consultation status'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        visit.consultation_end = timezone.now()
        
        # Check if admission or referral needed
        if request.data.get('requires_admission'):
            visit.requires_admission = True
            visit.status = 'admitted'
        elif request.data.get('requires_referral'):
            visit.requires_referral = True
            visit.status = 'completed'
        else:
            visit.status = 'completed'
            visit.completion_time = timezone.now()
        
        # Update clinical information
        if request.data.get('final_diagnosis'):
            visit.final_diagnosis = request.data['final_diagnosis']
        if request.data.get('treatment_plan'):
            visit.treatment_plan = request.data['treatment_plan']
        if request.data.get('discharge_instructions'):
            visit.discharge_instructions = request.data['discharge_instructions']
        
        visit.save()
        
        return Response({'message': 'Consultation ended', 'visit': VisitSerializer(visit).data})
    
    @action(detail=False, methods=['get'])
    def queue(self, request):
        """Get current queue for different departments"""
        department = request.query_params.get('department', 'outpatient')
        
        # Base queryset for waiting patients
        waiting_patients = Visit.objects.filter(
            status__in=['registered', 'check_in', 'triage', 'waiting'],
            visit_type=department
        ).exclude(status='completed').select_related('patient', 'primary_doctor')
        
        # Order by priority and time
        priority_order = {'critical': 1, 'emergency': 2, 'urgent': 3, 'routine': 4}
        waiting_list = []
        
        for visit in waiting_patients:
            waiting_list.append({
                'position': len(waiting_list) + 1,
                'visit_number': visit.visit_number,
                'patient_name': visit.patient.full_name,
                'priority': visit.priority,
                'status': visit.status,
                'waiting_time': visit.total_waiting_time,
                'arrival_time': visit.check_in_time or visit.registration_time
            })
        
        # Sort by priority
        waiting_list.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        return Response({
            'department': department,
            'queue_length': len(waiting_list),
            'queue': waiting_list
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get visit statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'today': {
                'total': Visit.objects.filter(registration_time__date=today).count(),
                'completed': Visit.objects.filter(completion_time__date=today).count(),
                'waiting': Visit.objects.filter(registration_time__date=today, status__in=['waiting', 'triage']).count(),
                'by_type': Visit.objects.filter(registration_time__date=today).values('visit_type').annotate(count=Count('id')),
                'average_waiting_time': Visit.objects.filter(registration_time__date=today, total_waiting_time__gt=0).aggregate(Avg('total_waiting_time'))['total_waiting_time__avg'] or 0
            },
            'this_week': {
                'total': Visit.objects.filter(registration_time__date__gte=week_ago).count(),
                'by_status': Visit.objects.filter(registration_time__date__gte=week_ago).values('status').annotate(count=Count('id'))
            },
            'this_month': {
                'total': Visit.objects.filter(registration_time__date__gte=month_ago).count(),
                'by_priority': Visit.objects.filter(registration_time__date__gte=month_ago).values('priority').annotate(count=Count('id'))
            },
            'overall': {
                'total_visits': Visit.objects.count(),
                'average_waiting_time': Visit.objects.filter(total_waiting_time__gt=0).aggregate(Avg('total_waiting_time'))['total_waiting_time__avg'] or 0,
                'peak_hours': Visit.objects.extra({'hour': "EXTRACT(hour FROM registration_time)"}).values('hour').annotate(count=Count('id')).order_by('-count')[:5]
            }
        }
        
        return Response(stats)