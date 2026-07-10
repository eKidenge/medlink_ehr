from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from datetime import timedelta
from .models import Medication, Prescription, StockTransaction
from .serializers import (
    MedicationSerializer, PrescriptionSerializer, PrescriptionListSerializer,
    PrescriptionCreateSerializer, DispenseSerializer, StockTransactionSerializer
)
from .filters import PrescriptionFilter
from apps.accounts.permissions import IsDoctorOrPharmacist, IsPharmacist, IsAdminOrSuperAdmin


class MedicationViewSet(viewsets.ModelViewSet):
    """Medication management ViewSet"""
    
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['generic_name', 'brand_name', 'drug_code']
    filterset_fields = ['category', 'drug_form', 'is_active']
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get medications with low stock"""
        low_stock_meds = Medication.objects.filter(
            current_stock__lte=F('reorder_level'),
            is_active=True
        )
        
        serializer = self.get_serializer(low_stock_meds, many=True)
        return Response({
            'count': low_stock_meds.count(),
            'medications': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """Update medication stock"""
        medication = self.get_object()
        quantity = request.data.get('quantity')
        transaction_type = request.data.get('transaction_type')
        notes = request.data.get('notes', '')
        
        if not quantity or not transaction_type:
            return Response({'error': 'Quantity and transaction type required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if transaction_type not in ['receive', 'issue', 'adjustment', 'return']:
            return Response({'error': 'Invalid transaction type'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Record stock before
        stock_before = medication.current_stock
        
        # Update stock
        if transaction_type == 'receive':
            medication.current_stock += quantity
        elif transaction_type == 'issue':
            if medication.current_stock < quantity:
                return Response({'error': 'Insufficient stock'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            medication.current_stock -= quantity
        elif transaction_type == 'adjustment':
            medication.current_stock = quantity
        
        medication.save()
        
        # Create transaction record
        transaction = StockTransaction.objects.create(
            medication=medication,
            transaction_type=transaction_type,
            quantity=quantity,
            stock_before=stock_before,
            stock_after=medication.current_stock,
            notes=notes,
            created_by=request.user
        )
        
        return Response({
            'message': f'Stock updated successfully',
            'current_stock': medication.current_stock,
            'transaction': StockTransactionSerializer(transaction).data
        })
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get medications expiring soon (within 30 days)"""
        thirty_days = timezone.now().date() + timedelta(days=30)
        expiring = Medication.objects.filter(
            expiry_date__lte=thirty_days,
            expiry_date__gte=timezone.now().date(),
            is_active=True
        )
        
        serializer = self.get_serializer(expiring, many=True)
        return Response({
            'count': expiring.count(),
            'medications': serializer.data
        })


class PrescriptionViewSet(viewsets.ModelViewSet):
    """Comprehensive Prescription ViewSet"""
    
    queryset = Prescription.objects.select_related(
        'patient', 'visit', 'medication', 'prescribing_doctor', 'dispensed_by'
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PrescriptionFilter
    search_fields = ['prescription_number', 'patient__first_name', 'patient__last_name']
    ordering_fields = ['prescribed_at', 'dispensed_at', 'status']
    ordering = ['-prescribed_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PrescriptionListSerializer
        elif self.action == 'create':
            return PrescriptionCreateSerializer
        elif self.action == 'dispense':
            return DispenseSerializer
        return PrescriptionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pending prescriptions
        pending = self.request.query_params.get('pending')
        if pending and pending.lower() == 'true':
            queryset = queryset.filter(status='pending')
        
        # Date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(prescribed_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(prescribed_at__date__lte=date_to)
        
        # Patient
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def dispense(self, request, pk=None):
        """Dispense medication"""
        prescription = self.get_object()
        
        if prescription.status == 'dispensed':
            return Response({'error': 'Prescription already fully dispensed'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        serializer = DispenseSerializer(data=request.data)
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']
            
            # Check stock availability
            if prescription.medication.current_stock < quantity:
                return Response({
                    'error': f'Insufficient stock. Available: {prescription.medication.current_stock}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            prescription.dispense(quantity, request.user)
            
            return Response({
                'message': f'Dispensed {quantity} units',
                'prescription': PrescriptionSerializer(prescription).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel_prescription(self, request, pk=None):
        """Cancel prescription"""
        prescription = self.get_object()
        
        if prescription.status != 'pending':
            return Response({'error': 'Only pending prescriptions can be cancelled'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', 'Cancelled by pharmacist')
        prescription.status = 'cancelled'
        prescription.save()
        
        return Response({
            'message': 'Prescription cancelled',
            'reason': reason
        })
    
    @action(detail=False, methods=['get'])
    def safety_alerts(self, request):
        """Get prescriptions with safety alerts"""
        patient_id = request.query_params.get('patient')
        if not patient_id:
            return Response({'error': 'Patient ID required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        prescriptions = Prescription.objects.filter(
            patient_id=patient_id,
            status='pending'
        ).select_related('medication')
        
        alerts = []
        for prescription in prescriptions:
            alerts.extend(prescription.check_safety_alerts())
        
        return Response({
            'patient_id': patient_id,
            'alerts': alerts
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Prescription statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'overall': {
                'total_prescriptions': Prescription.objects.count(),
                'total_dispensed': Prescription.objects.filter(status='dispensed').count(),
                'total_medications': Prescription.objects.aggregate(total=Sum('quantity'))['total'] or 0,
                'most_prescribed': Prescription.objects.values('medication__generic_name').annotate(
                    count=Count('id')
                ).order_by('-count')[:10]
            },
            'today': {
                'prescribed': Prescription.objects.filter(prescribed_at__date=today).count(),
                'dispensed': Prescription.objects.filter(dispensed_at__date=today).count(),
                'pending': Prescription.objects.filter(prescribed_at__date=today, status='pending').count()
            },
            'this_week': {
                'prescribed': Prescription.objects.filter(prescribed_at__date__gte=week_ago).count(),
                'by_route': Prescription.objects.filter(prescribed_at__date__gte=week_ago).values('route').annotate(count=Count('id'))
            },
            'this_month': {
                'prescribed': Prescription.objects.filter(prescribed_at__date__gte=month_ago).count(),
                'by_department': Prescription.objects.filter(prescribed_at__date__gte=month_ago).values(
                    'prescribing_doctor__department__name'
                ).annotate(count=Count('id'))
            },
            'inventory_status': {
                'total_medications': Medication.objects.filter(is_active=True).count(),
                'low_stock_items': Medication.objects.filter(current_stock__lte=F('reorder_level')).count(),
                'out_of_stock': Medication.objects.filter(current_stock=0).count(),
                'total_value': Medication.objects.aggregate(
                    total=Sum(F('current_stock') * F('unit_price'))
                )['total'] or 0
            }
        }
        
        return Response(stats)


class StockTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing stock transactions"""
    
    queryset = StockTransaction.objects.select_related('medication', 'created_by')
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated, IsPharmacist]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        medication_id = self.request.query_params.get('medication')
        if medication_id:
            queryset = queryset.filter(medication_id=medication_id)
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset