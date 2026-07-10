from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import json
from .models import (
    Patient, PatientAllergy, PatientChronicDisease, 
    PatientVaccination, PatientMedicalHistory, PatientSurgicalHistory
)
from .serializers import (
    PatientSerializer, PatientListSerializer, PatientCreateSerializer,
    PatientAllergySerializer, PatientChronicDiseaseSerializer,
    PatientVaccinationSerializer, PatientMedicalHistorySerializer,
    PatientSurgicalHistorySerializer, PatientMergeSerializer
)
from .filters import PatientFilter
from .utils import export_to_excel, export_to_csv
from apps.accounts.permissions import IsAdminOrSuperAdmin, CanViewPatient, CanEditPatient


class PatientViewSet(viewsets.ModelViewSet):
    """Comprehensive Patient ViewSet"""
    
    queryset = Patient.objects.filter(is_active=True, is_merged=False)
    permission_classes = [IsAuthenticated, CanViewPatient]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PatientFilter
    search_fields = ['patient_number', 'mrn_number', 'first_name', 'last_name', 
                     'phone_primary', 'identification_number', 'nhif_number']
    ordering_fields = ['created_at', 'last_name', 'first_name', 'age']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        elif self.action == 'create':
            return PatientCreateSerializer
        elif self.action == 'merge':
            return PatientMergeSerializer
        return PatientSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by search parameter
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(patient_number__icontains=search) |
                Q(mrn_number__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone_primary__icontains=search) |
                Q(identification_number__icontains=search)
            )
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.select_related('created_by')
    
    @action(detail=True, methods=['get'])
    def generate_qr(self, request, pk=None):
        """Generate QR code for patient"""
        patient = self.get_object()
        patient.generate_qr_code()
        return Response({'qr_code_url': patient.qr_code.url if patient.qr_code else None})
    
    @action(detail=True, methods=['get'])
    def allergies(self, request, pk=None):
        """Get patient allergies"""
        patient = self.get_object()
        allergies = patient.allergies.all()
        serializer = PatientAllergySerializer(allergies, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_allergy(self, request, pk=None):
        """Add allergy to patient"""
        patient = self.get_object()
        serializer = PatientAllergySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient, confirmed_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def chronic_diseases(self, request, pk=None):
        """Get patient chronic diseases"""
        patient = self.get_object()
        diseases = patient.chronic_diseases.all()
        serializer = PatientChronicDiseaseSerializer(diseases, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_chronic_disease(self, request, pk=None):
        """Add chronic disease to patient"""
        patient = self.get_object()
        serializer = PatientChronicDiseaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient, diagnosed_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def medical_history(self, request, pk=None):
        """Get patient medical history"""
        patient = self.get_object()
        history = patient.medical_history.all()
        serializer = PatientMedicalHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def vaccinations(self, request, pk=None):
        """Get patient vaccinations"""
        patient = self.get_object()
        vaccinations = patient.vaccinations.all()
        serializer = PatientVaccinationSerializer(vaccinations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def surgeries(self, request, pk=None):
        """Get patient surgical history"""
        patient = self.get_object()
        surgeries = patient.surgeries.all()
        serializer = PatientSurgicalHistorySerializer(surgeries, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get patient complete medical summary"""
        patient = self.get_object()
        
        summary = {
            'patient': PatientSerializer(patient).data,
            'allergies': PatientAllergySerializer(patient.allergies.all(), many=True).data,
            'chronic_diseases': PatientChronicDiseaseSerializer(patient.chronic_diseases.all(), many=True).data,
            'medical_history': PatientMedicalHistorySerializer(patient.medical_history.all(), many=True).data,
            'vaccinations': PatientVaccinationSerializer(patient.vaccinations.all(), many=True).data,
            'surgeries': PatientSurgicalHistorySerializer(patient.surgeries.all(), many=True).data,
            'visit_count': patient.visits.count(),
            'admission_count': patient.admissions.count(),
            'last_visit': patient.visits.order_by('-created_at').first().created_at if patient.visits.exists() else None,
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """Export patient data as PDF"""
        patient = self.get_object()
        
        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="patient_{patient.patient_number}.pdf"'
        
        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        title = Paragraph(f"Patient Medical Record - {patient.full_name}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Patient Information Table
        data = [
            ['Field', 'Value'],
            ['Patient Number', patient.patient_number],
            ['MRN', patient.mrn_number],
            ['Name', patient.full_name],
            ['Date of Birth', patient.date_of_birth],
            ['Age', patient.age],
            ['Gender', patient.get_gender_display()],
            ['Phone', patient.phone_primary],
            ['Email', patient.email or 'N/A'],
            ['NHIF Number', patient.nhif_number or 'N/A'],
            ['County', patient.county or 'N/A'],
        ]
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        return response
    
    @action(detail=False, methods=['post'])
    def export_excel(self, request):
        """Export filtered patients to Excel"""
        queryset = self.filter_queryset(self.get_queryset())
        export_format = request.data.get('format', 'excel')
        
        if export_format == 'csv':
            return export_to_csv(queryset)
        else:
            return export_to_excel(queryset)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrSuperAdmin])
    def merge(self, request):
        """Merge two patient records"""
        serializer = PatientMergeSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': 'Patients merged successfully',
                'target_patient': PatientSerializer(result).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def duplicates(self, request, pk=None):
        """Find duplicate patients based on similar information"""
        patient = self.get_object()
        
        # Find potential duplicates
        duplicates = Patient.objects.filter(
            Q(first_name__icontains=patient.first_name) &
            Q(last_name__icontains=patient.last_name) |
            Q(phone_primary=patient.phone_primary) |
            Q(identification_number=patient.identification_number)
        ).exclude(id=patient.id).filter(is_active=True)[:10]
        
        serializer = PatientListSerializer(duplicates, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get patient statistics"""
        total_patients = Patient.objects.count()
        active_patients = Patient.objects.filter(is_active=True).count()
        
        stats = {
            'total_patients': total_patients,
            'active_patients': active_patients,
            'inactive_patients': total_patients - active_patients,
            'patients_by_gender': Patient.objects.values('gender').annotate(count=Count('id')),
            'patients_by_county': Patient.objects.exclude(county='').values('county').annotate(count=Count('id')).order_by('-count')[:10],
            'new_patients_today': Patient.objects.filter(created_at__date=timezone.now().date()).count(),
            'new_patients_this_month': Patient.objects.filter(created_at__month=timezone.now().month).count(),
        }
        
        return Response(stats)