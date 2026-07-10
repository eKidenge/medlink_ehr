from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Ward, Bed, Admission, DailyRound
from .serializers import (
    WardSerializer, BedSerializer, AdmissionSerializer, 
    AdmissionListSerializer, AdmissionCreateSerializer,
    DailyRoundSerializer, DischargeSerializer
)
from .filters import AdmissionFilter
from apps.accounts.permissions import IsDoctorOrNurse, IsAdminOrSuperAdmin


class WardViewSet(viewsets.ModelViewSet):
    """Ward management ViewSet"""
    
    queryset = Ward.objects.all()
    serializer_class = WardSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code', 'ward_type']
    filterset_fields = ['ward_type', 'is_active']
    
    @action(detail=True, methods=['get'])
    def beds(self, request, pk=None):
        """Get all beds in ward"""
        ward = self.get_object()
        beds = ward.beds.all()
        serializer = BedSerializer(beds, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def current_patients(self, request, pk=None):
        """Get currently admitted patients in ward"""
        ward = self.get_object()
        admissions = Admission.objects.filter(
            ward=ward, 
            status__in=['admitted', 'in_treatment', 'stable', 'critical']
        ).select_related('patient', 'bed')
        
        data = []
        for admission in admissions:
            data.append({
                'admission_id': admission.id,
                'admission_number': admission.admission_number,
                'patient_name': admission.patient.full_name,
                'bed_number': admission.bed.bed_number if admission.bed else None,
                'admission_date': admission.admission_date,
                'status': admission.get_status_display(),
                'primary_diagnosis': admission.primary_diagnosis[:100]
            })
        
        return Response({
            'ward': ward.name,
            'occupied_beds': ward.occupied_beds,
            'available_beds': ward.available_beds,
            'patients': data
        })
    
    @action(detail=True, methods=['post'])
    def update_bed_count(self, request, pk=None):
        """Update ward bed counts"""
        ward = self.get_object()
        ward.update_bed_counts()
        return Response({
            'total_beds': ward.total_beds,
            'occupied_beds': ward.occupied_beds,
            'available_beds': ward.available_beds
        })


class BedViewSet(viewsets.ModelViewSet):
    """Bed management ViewSet"""
    
    queryset = Bed.objects.select_related('ward')
    serializer_class = BedSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['bed_number']
    filterset_fields = ['ward', 'is_occupied', 'is_available', 'bed_type']
    
    @action(detail=True, methods=['post'])
    def occupy(self, request, pk=None):
        """Occupy a bed"""
        bed = self.get_object()
        admission_id = request.data.get('admission_id')
        
        if bed.is_occupied:
            return Response({'error': 'Bed is already occupied'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        admission = Admission.objects.filter(id=admission_id).first()
        if not admission:
            return Response({'error': 'Admission not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        bed.occupy(admission)
        
        return Response({
            'message': f'Bed {bed.bed_number} occupied by {admission.patient.full_name}',
            'bed': BedSerializer(bed).data
        })
    
    @action(detail=True, methods=['post'])
    def vacate(self, request, pk=None):
        """Vacate a bed"""
        bed = self.get_object()
        
        if not bed.is_occupied:
            return Response({'error': 'Bed is not occupied'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        bed.vacate()
        
        return Response({
            'message': f'Bed {bed.bed_number} is now available',
            'bed': BedSerializer(bed).data
        })
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all available beds"""
        ward_id = request.query_params.get('ward')
        bed_type = request.query_params.get('bed_type')
        
        queryset = Bed.objects.filter(is_available=True, is_occupied=False)
        
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        if bed_type:
            queryset = queryset.filter(bed_type=bed_type)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total_available': queryset.count(),
            'beds': serializer.data
        })


class AdmissionViewSet(viewsets.ModelViewSet):
    """Comprehensive Admission ViewSet"""
    
    queryset = Admission.objects.select_related(
        'patient', 'visit', 'ward', 'bed', 'admitting_doctor', 'created_by'
    )
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AdmissionFilter
    search_fields = ['admission_number', 'patient__first_name', 'patient__last_name', 'patient__phone_primary']
    ordering_fields = ['admission_date', 'discharge_date', 'status']
    ordering = ['-admission_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AdmissionListSerializer
        elif self.action == 'create':
            return AdmissionCreateSerializer
        elif self.action == 'discharge':
            return DischargeSerializer
        return AdmissionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by ward
        ward_id = self.request.query_params.get('ward')
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        
        # Currently admitted (not discharged)
        current = self.request.query_params.get('current')
        if current and current.lower() == 'true':
            queryset = queryset.filter(status__in=['admitted', 'in_treatment', 'stable', 'critical'])
        
        # Date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(admission_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(admission_date__date__lte=date_to)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def discharge(self, request, pk=None):
        """Discharge a patient"""
        admission = self.get_object()
        
        if admission.status == 'discharged':
            return Response({'error': 'Patient already discharged'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        serializer = DischargeSerializer(data=request.data)
        if serializer.is_valid():
            admission.discharge(
                discharge_status=serializer.validated_data['discharge_status'],
                discharge_summary=serializer.validated_data['discharge_summary'],
                discharged_by=request.user
            )
            
            return Response({
                'message': f'Patient {admission.patient.full_name} discharged successfully',
                'admission': AdmissionSerializer(admission).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_round(self, request, pk=None):
        """Add daily round note"""
        admission = self.get_object()
        
        serializer = DailyRoundSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(admission=admission, doctor=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def rounds(self, request, pk=None):
        """Get all rounds for admission"""
        admission = self.get_object()
        rounds = admission.rounds.all()
        serializer = DailyRoundSerializer(rounds, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def census(self, request):
        """Get hospital census"""
        today = timezone.now().date()
        
        census = {
            'summary': {
                'total_beds': Ward.objects.aggregate(total=Sum('total_beds'))['total'] or 0,
                'occupied_beds': Bed.objects.filter(is_occupied=True).count(),
                'available_beds': Bed.objects.filter(is_available=True, is_occupied=False).count(),
                'occupancy_rate': 0
            },
            'by_ward': [],
            'by_type': {
                'emergency': Admission.objects.filter(admission_type='emergency', status__in=['admitted', 'in_treatment']).count(),
                'elective': Admission.objects.filter(admission_type='elective', status__in=['admitted', 'in_treatment']).count(),
                'transfer': Admission.objects.filter(admission_type='transfer', status__in=['admitted', 'in_treatment']).count(),
            },
            'today': {
                'admissions': Admission.objects.filter(admission_date__date=today).count(),
                'discharges': Admission.objects.filter(discharge_date__date=today).count(),
                'current_patients': Admission.objects.filter(status__in=['admitted', 'in_treatment', 'stable', 'critical']).count()
            }
        }
        
        # Calculate occupancy rate
        if census['summary']['total_beds'] > 0:
            census['summary']['occupancy_rate'] = round(
                (census['summary']['occupied_beds'] / census['summary']['total_beds']) * 100, 1
            )
        
        # By ward
        for ward in Ward.objects.filter(is_active=True):
            ward_data = {
                'ward_name': ward.name,
                'total_beds': ward.total_beds,
                'occupied': ward.occupied_beds,
                'available': ward.available_beds,
                'occupancy_rate': round((ward.occupied_beds / ward.total_beds) * 100, 1) if ward.total_beds > 0 else 0
            }
            census['by_ward'].append(ward_data)
        
        return Response(census)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get admission statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'overall': {
                'total_admissions': Admission.objects.count(),
                'average_length_of_stay': Admission.objects.filter(discharge_date__isnull=False).aggregate(
                    avg_days=Avg('discharge_date') - Avg('admission_date')
                )['avg_days'].days if Admission.objects.filter(discharge_date__isnull=False).exists() else 0,
                'readmission_rate': self._calculate_readmission_rate()
            },
            'today': {
                'admissions': Admission.objects.filter(admission_date__date=today).count(),
                'discharges': Admission.objects.filter(discharge_date__date=today).count(),
                'current': Admission.objects.filter(status__in=['admitted', 'in_treatment', 'stable', 'critical']).count()
            },
            'this_week': {
                'admissions': Admission.objects.filter(admission_date__date__gte=week_ago).count(),
                'by_type': Admission.objects.filter(admission_date__date__gte=week_ago).values('admission_type').annotate(count=Count('id'))
            },
            'this_month': {
                'admissions': Admission.objects.filter(admission_date__date__gte=month_ago).count(),
                'by_diagnosis': Admission.objects.values('primary_diagnosis').annotate(count=Count('id')).order_by('-count')[:10]
            },
            'discharge_outcomes': {
                'home': Admission.objects.filter(discharge_status='home').count(),
                'transfer': Admission.objects.filter(discharge_status='transfer').count(),
                'ama': Admission.objects.filter(discharge_status='ama').count(),
                'deceased': Admission.objects.filter(discharge_status='deceased').count(),
                'absconded': Admission.objects.filter(discharge_status='absconded').count()
            }
        }
        
        return Response(stats)
    
    def _calculate_readmission_rate(self):
        """Calculate readmission rate within 30 days"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        readmissions = 0
        total_discharged = Admission.objects.filter(discharge_date__isnull=False).count()
        
        # Simplified calculation - counts patients with multiple admissions within 30 days
        patients_with_multiple = Admission.objects.values('patient').annotate(
            admission_count=Count('id')
        ).filter(admission_count__gt=1).count()
        
        if total_discharged > 0:
            return round((patients_with_multiple / total_discharged) * 100, 1)
        return 0


class DailyRoundViewSet(viewsets.ModelViewSet):
    """Daily round notes ViewSet"""
    
    queryset = DailyRound.objects.select_related('admission', 'admission__patient', 'doctor')
    serializer_class = DailyRoundSerializer
    permission_classes = [IsAuthenticated, IsDoctorOrNurse]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        admission_id = self.request.query_params.get('admission')
        if admission_id:
            queryset = queryset.filter(admission_id=admission_id)
        
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(round_date__date=date)
        
        return queryset