from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import LabTestCategory, LabTest, LabRequest, LabResult
from .serializers import (
    LabTestCategorySerializer, LabTestSerializer, LabRequestSerializer,
    LabRequestListSerializer, LabRequestCreateSerializer, LabResultSerializer
)
from .filters import LabRequestFilter
from apps.accounts.permissions import IsDoctorOrLabTech, IsLabTechnician, IsAdminOrSuperAdmin


class LabTestCategoryViewSet(viewsets.ModelViewSet):
    """Lab test categories ViewSet"""
    
    queryset = LabTestCategory.objects.all()
    serializer_class = LabTestCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    search_fields = ['name', 'code']
    
    @action(detail=True, methods=['get'])
    def tests(self, request, pk=None):
        """Get all tests in category"""
        category = self.get_object()
        tests = category.tests.filter(is_active=True)
        serializer = LabTestSerializer(tests, many=True)
        return Response(serializer.data)


class LabTestViewSet(viewsets.ModelViewSet):
    """Lab test definitions ViewSet"""
    
    queryset = LabTest.objects.select_related('category')
    serializer_class = LabTestSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['category', 'is_active', 'specimen_type']


class LabRequestViewSet(viewsets.ModelViewSet):
    """Comprehensive Lab Request ViewSet"""
    
    queryset = LabRequest.objects.select_related(
        'patient', 'visit', 'requesting_doctor', 'test', 'assigned_to'
    )
    permission_classes = [IsAuthenticated, IsDoctorOrLabTech]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LabRequestFilter
    search_fields = ['request_number', 'patient__first_name', 'patient__last_name', 'patient__phone_primary']
    ordering_fields = ['created_at', 'priority', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LabRequestListSerializer
        elif self.action == 'create':
            return LabRequestCreateSerializer
        return LabRequestSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Pending requests (for lab dashboard)
        pending = self.request.query_params.get('pending')
        if pending and pending.lower() == 'true':
            queryset = queryset.filter(status__in=['pending', 'collected'])
        
        # Date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Assigned to current user
        my_tasks = self.request.query_params.get('my_tasks')
        if my_tasks and my_tasks.lower() == 'true':
            queryset = queryset.filter(assigned_to=self.request.user)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def collect_specimen(self, request, pk=None):
        """Mark specimen as collected"""
        lab_request = self.get_object()
        
        if lab_request.status != 'pending':
            return Response({'error': 'Specimen cannot be collected at this stage'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        lab_request.collect_specimen(request.user)
        
        return Response({
            'message': 'Specimen collected successfully',
            'collected_at': lab_request.specimen_collected_at,
            'status': lab_request.status
        })
    
    @action(detail=True, methods=['post'])
    def start_processing(self, request, pk=None):
        """Start processing the test"""
        lab_request = self.get_object()
        
        if lab_request.status != 'collected':
            return Response({'error': 'Specimen must be collected before processing'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        lab_request.start_processing(request.user)
        
        return Response({
            'message': 'Test processing started',
            'started_at': lab_request.started_processing_at,
            'assigned_to': lab_request.assigned_to.get_full_name()
        })
    
    @action(detail=True, methods=['post'])
    def submit_result(self, request, pk=None):
        """Submit test results"""
        lab_request = self.get_object()
        
        if lab_request.status != 'processing':
            return Response({'error': 'Test must be in processing stage'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        result_value = request.data.get('result_value')
        if not result_value:
            return Response({'error': 'Result value is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if result is abnormal
        is_abnormal = False
        if lab_request.test.normal_range:
            # Simple parsing of normal range (e.g., "4-11")
            try:
                if '-' in lab_request.test.normal_range:
                    min_val, max_val = lab_request.test.normal_range.split('-')
                    numeric_result = float(result_value)
                    if numeric_result < float(min_val) or numeric_result > float(max_val):
                        is_abnormal = True
            except:
                pass
        
        lab_request.result_value = result_value
        lab_request.is_abnormal = is_abnormal
        lab_request.interpretation = request.data.get('interpretation', '')
        
        # Handle detailed results
        detailed_results = request.data.get('detailed_results', [])
        for detail in detailed_results:
            LabResult.objects.create(
                lab_request=lab_request,
                component_name=detail['component_name'],
                result_value=detail['result_value'],
                unit=detail.get('unit', ''),
                reference_range=detail.get('reference_range', ''),
                is_abnormal=detail.get('is_abnormal', False),
                notes=detail.get('notes', '')
            )
        
        lab_request.complete_test(result_value, request.user)
        
        return Response({
            'message': 'Results submitted successfully',
            'result': LabRequestSerializer(lab_request).data
        })
    
    @action(detail=True, methods=['post'])
    def reject_test(self, request, pk=None):
        """Reject a test request"""
        lab_request = self.get_object()
        
        reason = request.data.get('reason')
        if not reason:
            return Response({'error': 'Rejection reason is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        lab_request.reject_test(reason, request.user)
        
        return Response({
            'message': 'Test request rejected',
            'reason': reason
        })
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Lab dashboard statistics"""
        today = timezone.now().date()
        
        stats = {
            'pending_tests': LabRequest.objects.filter(status='pending').count(),
            'collected_tests': LabRequest.objects.filter(status='collected').count(),
            'processing_tests': LabRequest.objects.filter(status='processing').count(),
            'completed_today': LabRequest.objects.filter(completed_at__date=today).count(),
            'urgent_pending': LabRequest.objects.filter(priority='stat', status__in=['pending', 'collected']).count(),
            'abnormal_results': LabRequest.objects.filter(is_abnormal=True, created_at__date=today).count(),
            'rejected_today': LabRequest.objects.filter(status='rejected', created_at__date=today).count(),
            'by_category': LabRequest.objects.filter(created_at__date=today).values(
                'test__category__name'
            ).annotate(count=Count('id')),
            'recent_requests': LabRequestListSerializer(
                LabRequest.objects.filter(created_at__date=today)[:10], 
                many=True
            ).data
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Comprehensive lab statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'overall': {
                'total_requests': LabRequest.objects.count(),
                'total_completed': LabRequest.objects.filter(status='completed').count(),
                'average_turnaround': self._calculate_average_turnaround(),
                'most_requested_tests': LabRequest.objects.values('test__name').annotate(
                    count=Count('id')
                ).order_by('-count')[:10]
            },
            'today': {
                'requests': LabRequest.objects.filter(created_at__date=today).count(),
                'completed': LabRequest.objects.filter(completed_at__date=today).count(),
                'pending': LabRequest.objects.filter(created_at__date=today, status__in=['pending', 'collected']).count(),
                'abnormal_rate': self._calculate_abnormal_rate(today)
            },
            'this_week': {
                'requests': LabRequest.objects.filter(created_at__date__gte=week_ago).count(),
                'by_priority': LabRequest.objects.filter(created_at__date__gte=week_ago).values('priority').annotate(count=Count('id'))
            },
            'this_month': {
                'requests': LabRequest.objects.filter(created_at__date__gte=month_ago).count(),
                'by_department': LabRequest.objects.filter(created_at__date__gte=month_ago).values(
                    'requesting_doctor__department__name'
                ).annotate(count=Count('id'))
            }
        }
        
        return Response(stats)
    
    def _calculate_average_turnaround(self):
        """Calculate average turnaround time in hours"""
        completed = LabRequest.objects.filter(
            status='completed', 
            completed_at__isnull=False,
            created_at__isnull=False
        )
        
        if not completed.exists():
            return 0
        
        total_hours = 0
        for req in completed:
            hours = (req.completed_at - req.created_at).total_seconds() / 3600
            total_hours += hours
        
        return round(total_hours / completed.count(), 1)
    
    def _calculate_abnormal_rate(self, date):
        """Calculate abnormal results rate for a given date"""
        completed = LabRequest.objects.filter(completed_at__date=date)
        if not completed.exists():
            return 0
        
        abnormal = completed.filter(is_abnormal=True).count()
        return round((abnormal / completed.count()) * 100, 1)


class LabResultViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing lab results"""
    
    queryset = LabResult.objects.select_related('lab_request', 'lab_request__patient')
    serializer_class = LabResultSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        lab_request_id = self.request.query_params.get('lab_request')
        if lab_request_id:
            queryset = queryset.filter(lab_request_id=lab_request_id)
        
        return queryset