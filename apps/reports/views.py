from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail
from datetime import datetime, timedelta
import json
import csv
import io
import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from .models import ReportTemplate, ReportJob, AuditReport
from .serializers import (
    ReportTemplateSerializer, ReportJobSerializer, AuditReportSerializer
)
from apps.accounts.permissions import IsAdminOrSuperAdmin, CanExportData


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """Report template management"""
    
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate report from template"""
        template = self.get_object()
        
        # Create report job
        job = ReportJob.objects.create(
            template=template,
            requested_by=request.user,
            parameters=request.data.get('parameters', {}),
            output_format=request.data.get('format', template.default_format)
        )
        
        # Process report (in production, use Celery)
        self._process_report(job)
        
        return Response({
            'job_id': job.id,
            'status': job.status,
            'message': 'Report generation started'
        })
    
    def _process_report(self, job):
        """Process report generation"""
        try:
            job.status = 'processing'
            job.save()
            
            # Generate report based on template
            data = self._fetch_report_data(job.template, job.parameters)
            
            # Create output file
            if job.output_format == 'excel':
                file_path = self._create_excel_report(data, job.template)
            elif job.output_format == 'csv':
                file_path = self._create_csv_report(data, job.template)
            elif job.output_format == 'pdf':
                file_path = self._create_pdf_report(data, job.template)
            else:
                file_path = self._create_json_report(data, job.template)
            
            job.output_file = file_path
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save()
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
    
    def _fetch_report_data(self, template, parameters):
        """Fetch data for report based on template"""
        report_type = template.report_type
        
        if report_type == 'clinical':
            return self._get_clinical_data(parameters)
        elif report_type == 'financial':
            return self._get_financial_data(parameters)
        elif report_type == 'operational':
            return self._get_operational_data(parameters)
        elif report_type == 'public_health':
            return self._get_public_health_data(parameters)
        else:
            return self._get_administrative_data(parameters)
    
    def _get_clinical_data(self, params):
        """Get clinical report data"""
        from apps.visits.models import Visit
        from apps.admissions.models import Admission
        
        start_date = params.get('start_date', (timezone.now() - timedelta(days=30)).date())
        end_date = params.get('end_date', timezone.now().date())
        
        visits = Visit.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        
        data = {
            'report_type': 'Clinical Report',
            'date_range': f"{start_date} to {end_date}",
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {
                'total_visits': visits.count(),
                'by_type': list(visits.values('visit_type').annotate(count=Count('id'))),
                'by_diagnosis': list(visits.exclude(final_diagnosis='').values('final_diagnosis').annotate(count=Count('id')).order_by('-count')[:20]),
                'admissions': Admission.objects.filter(admission_date__date__gte=start_date).count(),
                'average_length_of_stay': Admission.objects.filter(admission_date__date__gte=start_date).aggregate(avg=Avg('discharge_date') - Avg('admission_date'))['avg']
            }
        }
        
        return data
    
    def _get_financial_data(self, params):
        """Get financial report data"""
        from apps.visits.models import Visit
        from apps.admissions.models import Admission
        
        start_date = params.get('start_date', (timezone.now() - timedelta(days=30)).date())
        end_date = params.get('end_date', timezone.now().date())
        
        visits = Visit.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        
        data = {
            'report_type': 'Financial Report',
            'date_range': f"{start_date} to {end_date}",
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {
                'total_revenue': visits.aggregate(total=Sum('total_amount'))['total'] or 0,
                'collected_amount': visits.aggregate(collected=Sum('amount_paid'))['collected'] or 0,
                'outstanding': visits.aggregate(total=Sum('total_amount'))['total'] - visits.aggregate(collected=Sum('amount_paid'))['collected'] or 0,
                'by_payment_status': list(visits.values('payment_status').annotate(count=Count('id'), total=Sum('total_amount'))),
                'insurance_claims': visits.exclude(insurance_claim_number='').count()
            }
        }
        
        return data
    
    def _get_operational_data(self, params):
        """Get operational report data"""
        from apps.visits.models import Visit
        from apps.triage.models import Triage
        
        start_date = params.get('start_date', (timezone.now() - timedelta(days=30)).date())
        end_date = params.get('end_date', timezone.now().date())
        
        visits = Visit.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        
        data = {
            'report_type': 'Operational Report',
            'date_range': f"{start_date} to {end_date}",
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {
                'total_visits': visits.count(),
                'average_waiting_time': visits.aggregate(avg=Avg('total_waiting_time'))['avg'] or 0,
                'by_status': list(visits.values('status').annotate(count=Count('id'))),
                'triage_statistics': {
                    'total_triages': Triage.objects.filter(triage_start__date__gte=start_date).count(),
                    'by_priority': list(Triage.objects.filter(triage_start__date__gte=start_date).values('priority').annotate(count=Count('id'))),
                    'average_score': Triage.objects.filter(triage_start__date__gte=start_date).aggregate(avg=Avg('triage_score'))['avg'] or 0
                },
                'peak_hours': list(visits.extra({'hour': "EXTRACT(hour FROM created_at)"}).values('hour').annotate(count=Count('id')).order_by('-count')[:5])
            }
        }
        
        return data
    
    def _get_public_health_data(self, params):
        """Get public health report data"""
        from apps.visits.models import Visit
        from apps.patients.models import Patient
        
        start_date = params.get('start_date', (timezone.now() - timedelta(days=30)).date())
        end_date = params.get('end_date', timezone.now().date())
        
        data = {
            'report_type': 'Public Health Report',
            'date_range': f"{start_date} to {end_date}",
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {
                'top_diseases': list(Visit.objects.filter(created_at__date__gte=start_date).exclude(final_diagnosis='').values('final_diagnosis').annotate(count=Count('id')).order_by('-count')[:20]),
                'demographics': {
                    'by_age_group': self._get_age_group_distribution(start_date),
                    'by_gender': list(Patient.objects.filter(created_at__date__gte=start_date).values('gender').annotate(count=Count('id'))),
                    'by_county': list(Patient.objects.exclude(county='').values('county').annotate(count=Count('id')).order_by('-count')[:10])
                }
            }
        }
        
        return data
    
    def _get_administrative_data(self, params):
        """Get administrative report data"""
        from apps.accounts.models import User, AuditLog
        
        start_date = params.get('start_date', (timezone.now() - timedelta(days=30)).date())
        end_date = params.get('end_date', timezone.now().date())
        
        data = {
            'report_type': 'Administrative Report',
            'date_range': f"{start_date} to {end_date}",
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {
                'staff_statistics': {
                    'total_staff': User.objects.filter(is_active=True).count(),
                    'by_role': list(User.objects.filter(is_active=True).values('role').annotate(count=Count('id'))),
                    'by_department': list(User.objects.filter(is_active=True).values('department__name').annotate(count=Count('id')))
                },
                'system_usage': {
                    'total_logins': AuditLog.objects.filter(action='login', timestamp__date__gte=start_date).count(),
                    'active_users': User.objects.filter(is_online=True).count(),
                    'api_calls': AuditLog.objects.filter(timestamp__date__gte=start_date).count()
                }
            }
        }
        
        return data
    
    def _get_age_group_distribution(self, start_date):
        """Get age group distribution"""
        from apps.patients.models import Patient
        
        age_groups = {
            '0-5': Patient.objects.filter(age__lte=5, created_at__date__gte=start_date).count(),
            '6-12': Patient.objects.filter(age__gte=6, age__lte=12, created_at__date__gte=start_date).count(),
            '13-18': Patient.objects.filter(age__gte=13, age__lte=18, created_at__date__gte=start_date).count(),
            '19-35': Patient.objects.filter(age__gte=19, age__lte=35, created_at__date__gte=start_date).count(),
            '36-50': Patient.objects.filter(age__gte=36, age__lte=50, created_at__date__gte=start_date).count(),
            '51-65': Patient.objects.filter(age__gte=51, age__lte=65, created_at__date__gte=start_date).count(),
            '65+': Patient.objects.filter(age__gte=65, created_at__date__gte=start_date).count()
        }
        
        return age_groups
    
    def _create_excel_report(self, data, template):
        """Create Excel report file"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Add formats
        title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#4CAF50', 'color': 'white'})
        
        # Create worksheet
        worksheet = workbook.add_worksheet(template.name)
        
        # Title
        worksheet.merge_range('A1:D1', data['report_type'], title_format)
        worksheet.write(2, 0, f"Date Range: {data['date_range']}")
        worksheet.write(3, 0, f"Generated: {data['generated_at']}")
        
        # Write data sections
        row = 5
        for section, section_data in data['data'].items():
            worksheet.write(row, 0, section.replace('_', ' ').title(), header_format)
            row += 1
            
            if isinstance(section_data, list) and len(section_data) > 0:
                # Write headers
                headers = list(section_data[0].keys())
                for col, header in enumerate(headers):
                    worksheet.write(row, col, header, header_format)
                row += 1
                
                # Write data
                for item in section_data:
                    for col, header in enumerate(headers):
                        worksheet.write(row, col, str(item.get(header, '')))
                    row += 1
                row += 1
            elif isinstance(section_data, dict):
                for key, value in section_data.items():
                    worksheet.write(row, 0, key.replace('_', ' ').title())
                    worksheet.write(row, 1, str(value))
                    row += 1
                row += 1
            else:
                worksheet.write(row, 0, str(section_data))
                row += 1
        
        workbook.close()
        output.seek(0)
        
        # Save file
        filename = f"reports/{template.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        from django.core.files.base import ContentFile
        from django.core.files import File
        
        job.template.save(filename, ContentFile(output.getvalue()))
        return filename
    
    def _create_csv_report(self, data, template):
        """Create CSV report file"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([data['report_type']])
        writer.writerow([f"Date Range: {data['date_range']}"])
        writer.writerow([f"Generated: {data['generated_at']}"])
        writer.writerow([])
        
        for section, section_data in data['data'].items():
            writer.writerow([section.replace('_', ' ').title()])
            
            if isinstance(section_data, list) and len(section_data) > 0:
                headers = list(section_data[0].keys())
                writer.writerow(headers)
                for item in section_data:
                    writer.writerow([str(item.get(h, '')) for h in headers])
            elif isinstance(section_data, dict):
                for key, value in section_data.items():
                    writer.writerow([key.replace('_', ' ').title(), value])
            else:
                writer.writerow([str(section_data)])
            writer.writerow([])
        
        output.seek(0)
        
        filename = f"reports/{template.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        from django.core.files.base import ContentFile
        
        job.template.save(filename, ContentFile(output.getvalue().encode()))
        return filename
    
    def _create_pdf_report(self, data, template):
        """Create PDF report file"""
        response = HttpResponse(content_type='application/pdf')
        
        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=18, alignment=1)
        elements.append(Paragraph(data['report_type'], title_style))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Date Range: {data['date_range']}", styles['Normal']))
        elements.append(Paragraph(f"Generated: {data['generated_at']}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Data sections
        for section, section_data in data['data'].items():
            elements.append(Paragraph(section.replace('_', ' ').title(), styles['Heading2']))
            elements.append(Spacer(1, 6))
            
            if isinstance(section_data, list) and len(section_data) > 0:
                # Create table
                headers = list(section_data[0].keys())
                table_data = [headers]
                for item in section_data:
                    row = [str(item.get(h, '')) for h in headers]
                    table_data.append(row)
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(table)
            elif isinstance(section_data, dict):
                for key, value in section_data.items():
                    elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", styles['Normal']))
            else:
                elements.append(Paragraph(str(section_data), styles['Normal']))
            
            elements.append(Spacer(1, 12))
        
        doc.build(elements)
        
        filename = f"reports/{template.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        from django.core.files.base import ContentFile
        
        job.template.save(filename, ContentFile(response.content))
        return filename
    
    def _create_json_report(self, data, template):
        """Create JSON report file"""
        import json
        
        output = json.dumps(data, indent=2, default=str)
        
        filename = f"reports/{template.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        from django.core.files.base import ContentFile
        
        job.template.save(filename, ContentFile(output.encode()))
        return filename


class ReportJobViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing report jobs"""
    
    queryset = ReportJob.objects.select_related('template', 'requested_by')
    serializer_class = ReportJobSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Users can only see their own reports unless admin
        if not self.request.user.role in ['super_admin', 'admin']:
            queryset = queryset.filter(requested_by=self.request.user)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download generated report"""
        job = self.get_object()
        
        if job.status != 'completed' or not job.output_file:
            return Response({'error': 'Report not ready for download'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        response = HttpResponse(job.output_file.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{job.output_file.name.split("/")[-1]}"'
        
        return response


class AuditReportViewSet(viewsets.ModelViewSet):
    """ViewSet for audit reports"""
    
    queryset = AuditReport.objects.select_related('generated_by')
    serializer_class = AuditReportSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate audit report"""
        from apps.accounts.models import AuditLog
        
        action_type = request.data.get('action_type')
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')
        
        if not all([action_type, date_from, date_to]):
            return Response({'error': 'action_type, date_from, and date_to required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch audit logs
        logs = AuditLog.objects.filter(
            action=action_type,
            timestamp__date__gte=date_from,
            timestamp__date__lte=date_to
        ).select_related('user')
        
        # Generate report data
        report_data = {
            'action_type': action_type,
            'date_range': f"{date_from} to {date_to}",
            'total_events': logs.count(),
            'events': list(logs.values('timestamp', 'user__username', 'model_name', 'object_repr', 'ip_address')),
            'summary': {
                'by_user': list(logs.values('user__username').annotate(count=Count('id'))),
                'by_model': list(logs.values('model_name').annotate(count=Count('id')))
            }
        }
        
        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Audit Report')
        
        header_format = workbook.add_format({'bold': True, 'bg_color': '#4CAF50', 'color': 'white'})
        
        # Write headers
        headers = ['Timestamp', 'User', 'Action', 'Model', 'Object', 'IP Address']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        for row, log in enumerate(logs, 1):
            worksheet.write(row, 0, log.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
            worksheet.write(row, 1, log.user.username if log.user else 'System')
            worksheet.write(row, 2, log.action)
            worksheet.write(row, 3, log.model_name)
            worksheet.write(row, 4, log.object_repr[:50])
            worksheet.write(row, 5, log.ip_address)
        
        workbook.close()
        output.seek(0)
        
        # Save report
        report = AuditReport.objects.create(
            report_number=f"AUD{timezone.now().strftime('%Y%m%d%H%M%S')}",
            action_type=action_type,
            date_from=date_from,
            date_to=date_to,
            total_events=logs.count(),
            report_data=report_data,
            generated_by=request.user
        )
        
        filename = f"audit_reports/audit_{report.report_number}.xlsx"
        from django.core.files.base import ContentFile
        report.report_file.save(filename, ContentFile(output.getvalue()))
        
        return Response({
            'message': 'Audit report generated',
            'report': AuditReportSerializer(report).data
        })