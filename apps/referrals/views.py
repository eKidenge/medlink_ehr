from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import qrcode
import json
from .models import Referral, ReferralNote
from .serializers import (
    ReferralSerializer, ReferralListSerializer, ReferralCreateSerializer,
    ReferralNoteSerializer, ReferralStatusSerializer
)
from .filters import ReferralFilter
from apps.accounts.permissions import IsDoctorOrNurse


class ReferralViewSet(viewsets.ModelViewSet):
    """Comprehensive Referral ViewSet"""
    
    queryset = Referral.objects.select_related('patient', 'visit', 'referring_doctor')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReferralFilter
    search_fields = ['referral_number', 'patient__first_name', 'patient__last_name', 'receiving_facility']
    ordering_fields = ['created_at', 'priority', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReferralListSerializer
        elif self.action == 'create':
            return ReferralCreateSerializer
        elif self.action == 'update_status':
            return ReferralStatusSerializer
        return ReferralSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by type
        referral_type = self.request.query_params.get('type')
        if referral_type:
            queryset = queryset.filter(referral_type=referral_type)
        
        # Pending referrals
        pending = self.request.query_params.get('pending')
        if pending and pending.lower() == 'true':
            queryset = queryset.filter(status='pending')
        
        # Facility
        facility = self.request.query_params.get('facility')
        if facility:
            queryset = queryset.filter(Q(referring_facility__icontains=facility) | 
                                       Q(receiving_facility__icontains=facility))
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve referral"""
        referral = self.get_object()
        
        if referral.status != 'pending':
            return Response({'error': 'Only pending referrals can be approved'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        referral.approve(request.user)
        
        # Generate QR code for secure access
        self._generate_qr_code(referral)
        
        return Response({
            'message': 'Referral approved',
            'referral': ReferralSerializer(referral).data,
            'qr_code_url': referral.qr_code.url if referral.qr_code else None
        })
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark referral as completed"""
        referral = self.get_object()
        
        if referral.status not in ['approved', 'in_progress']:
            return Response({'error': 'Referral must be approved or in progress'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        feedback = request.data.get('feedback', '')
        outcome = request.data.get('outcome', '')
        
        if feedback:
            referral.feedback_from_receiving = feedback
        if outcome:
            referral.outcome = outcome
        
        referral.complete()
        
        return Response({
            'message': 'Referral completed',
            'referral': ReferralSerializer(referral).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel referral"""
        referral = self.get_object()
        
        if referral.status == 'completed':
            return Response({'error': 'Cannot cancel completed referral'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', 'Cancelled by user')
        referral.cancel(reason, request.user)
        
        return Response({
            'message': 'Referral cancelled',
            'reason': reason
        })
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add note to referral"""
        referral = self.get_object()
        
        serializer = ReferralNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(referral=referral, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        """Get all notes for referral"""
        referral = self.get_object()
        notes = referral.notes.all()
        serializer = ReferralNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """Export referral as PDF"""
        referral = self.get_object()
        
        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="referral_{referral.referral_number}.pdf"'
        
        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center
        )
        title = Paragraph(f"MEDICAL REFERRAL FORM", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Referral Header
        header_data = [
            ['Referral Number:', referral.referral_number],
            ['Date:', referral.created_at.strftime('%Y-%m-%d %H:%M')],
            ['Priority:', referral.get_priority_display()],
            ['Status:', referral.get_status_display()],
        ]
        
        header_table = Table(header_data, colWidths=[2*inch, 4*inch])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 12))
        
        # Patient Information
        elements.append(Paragraph("PATIENT INFORMATION", styles['Heading2']))
        patient_data = [
            ['Name:', referral.patient.full_name],
            ['Date of Birth:', referral.patient.date_of_birth.strftime('%Y-%m-%d')],
            ['Gender:', referral.patient.get_gender_display()],
            ['Phone:', referral.patient.phone_primary],
            ['NHIF Number:', referral.patient.nhif_number or 'N/A'],
        ]
        
        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        elements.append(patient_table)
        elements.append(Spacer(1, 12))
        
        # Referral Details
        elements.append(Paragraph("REFERRAL DETAILS", styles['Heading2']))
        referral_data = [
            ['Referring Facility:', referral.referring_facility],
            ['Referring Doctor:', referral.referring_doctor.get_full_name()],
            ['Receiving Facility:', referral.receiving_facility],
            ['Receiving Department:', referral.receiving_department or 'N/A'],
            ['Reason for Referral:', referral.reason_for_referral],
        ]
        
        referral_table = Table(referral_data, colWidths=[2*inch, 4*inch])
        referral_table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        elements.append(referral_table)
        elements.append(Spacer(1, 12))
        
        # Clinical Information
        elements.append(Paragraph("CLINICAL INFORMATION", styles['Heading2']))
        elements.append(Paragraph(f"<b>Clinical Summary:</b> {referral.clinical_summary}", styles['Normal']))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Provisional Diagnosis:</b> {referral.provisional_diagnosis}", styles['Normal']))
        
        if referral.investigations_done:
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<b>Investigations Done:</b> {referral.investigations_done}", styles['Normal']))
        
        if referral.treatment_given:
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<b>Treatment Given:</b> {referral.treatment_given}", styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        
        return response
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def verify(self, request):
        """Verify referral using QR code token"""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)
        
        referral = get_object_or_404(Referral, access_token=token)
        
        # Check if token is expired
        if referral.token_expiry and referral.token_expiry < timezone.now():
            return Response({'error': 'Referral link has expired'}, status=status.HTTP_410_GONE)
        
        serializer = ReferralSerializer(referral)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get referral statistics"""
        today = timezone.now().date()
        
        stats = {
            'overall': {
                'total': Referral.objects.count(),
                'pending': Referral.objects.filter(status='pending').count(),
                'approved': Referral.objects.filter(status='approved').count(),
                'completed': Referral.objects.filter(status='completed').count(),
                'cancelled': Referral.objects.filter(status='cancelled').count()
            },
            'by_type': {
                'internal': Referral.objects.filter(referral_type='internal').count(),
                'external': Referral.objects.filter(referral_type='external').count(),
                'emergency': Referral.objects.filter(referral_type='emergency').count(),
                'specialist': Referral.objects.filter(referral_type='specialist').count()
            },
            'by_priority': {
                'routine': Referral.objects.filter(priority='routine').count(),
                'urgent': Referral.objects.filter(priority='urgent').count(),
                'emergency': Referral.objects.filter(priority='emergency').count()
            },
            'today': {
                'created': Referral.objects.filter(created_at__date=today).count(),
                'completed': Referral.objects.filter(completed_at__date=today).count()
            },
            'top_receiving_facilities': Referral.objects.values('receiving_facility').annotate(
                count=Count('id')
            ).order_by('-count')[:5],
            'average_completion_time': self._calculate_average_completion_time()
        }
        
        return Response(stats)
    
    def _generate_qr_code(self, referral):
        """Generate QR code for secure referral access"""
        import secrets
        import qrcode
        from io import BytesIO
        from django.core.files import File
        
        # Generate unique access token
        token = secrets.token_urlsafe(32)
        referral.access_token = token
        referral.token_expiry = timezone.now() + timedelta(days=7)  # 7 days expiry
        
        # Create QR code data
        qr_data = {
            'referral_number': referral.referral_number,
            'token': token,
            'patient_name': referral.patient.full_name,
            'receiving_facility': referral.receiving_facility
        }
        
        qr_text = json.dumps(qr_data)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"referral_qr_{referral.referral_number}.png"
        referral.qr_code.save(filename, File(buffer), save=False)
        referral.save()
    
    def _calculate_average_completion_time(self):
        """Calculate average completion time in days"""
        completed = Referral.objects.filter(
            status='completed',
            completed_at__isnull=False,
            created_at__isnull=False
        )
        
        if not completed.exists():
            return 0
        
        total_days = 0
        for ref in completed:
            days = (ref.completed_at - ref.created_at).days
            total_days += days
        
        return round(total_days / completed.count(), 1)


class ReferralNoteViewSet(viewsets.ModelViewSet):
    """Referral notes ViewSet"""
    
    queryset = ReferralNote.objects.select_related('referral', 'author')
    serializer_class = ReferralNoteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        referral_id = self.request.query_params.get('referral')
        if referral_id:
            queryset = queryset.filter(referral_id=referral_id)
        
        return queryset