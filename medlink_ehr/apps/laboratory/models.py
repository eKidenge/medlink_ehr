from django.db import models
from django.utils import timezone
from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.accounts.models import User


class LabTestCategory(models.Model):
    """Laboratory test categories"""
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Lab Test Categories"
    
    def __str__(self):
        return self.name


class LabTest(models.Model):
    """Laboratory test definitions"""
    
    SPECIMEN_TYPES = (
        ('blood', 'Blood'),
        ('urine', 'Urine'),
        ('stool', 'Stool'),
        ('sputum', 'Sputum'),
        ('swab', 'Swab'),
        ('tissue', 'Tissue'),
        ('cerebrospinal', 'Cerebrospinal Fluid'),
        ('pleural', 'Pleural Fluid'),
        ('ascitic', 'Ascitic Fluid'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(LabTestCategory, on_delete=models.CASCADE, related_name='tests')
    specimen_type = models.CharField(max_length=20, choices=SPECIMEN_TYPES)
    
    # Test details
    normal_range = models.CharField(max_length=200, blank=True, help_text="Normal reference range")
    unit = models.CharField(max_length=50, blank=True)
    turnaround_time = models.IntegerField(default=24, help_text="Turnaround time in hours")
    
    # Cost
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    requires_fasting = models.BooleanField(default=False)
    fasting_hours = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class LabRequest(models.Model):
    """Laboratory test request"""
    
    PRIORITY_CHOICES = (
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT - Immediate'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Collection'),
        ('collected', 'Specimen Collected'),
        ('processing', 'Processing'),
        ('verified', 'Verified'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    )
    
    # Basic Information
    request_number = models.CharField(max_length=50, unique=True, db_index=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_requests')
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='lab_requests')
    requesting_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lab_requests')
    
    # Test Information
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name='requests')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='routine')
    
    # Clinical Information
    clinical_notes = models.TextField(blank=True, help_text="Relevant clinical information")
    diagnosis = models.TextField(blank=True)
    
    # Specimen Information
    specimen_type = models.CharField(max_length=50)
    specimen_collected_at = models.DateTimeField(null=True, blank=True)
    specimen_collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='collected_specimens')
    specimen_quality = models.CharField(max_length=100, blank=True)
    
    # Processing Information
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tests')
    started_processing_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    result_value = models.TextField(blank=True)
    result_numeric = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    result_unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=200, blank=True)
    interpretation = models.TextField(blank=True)
    is_abnormal = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Verification
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_tests')
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Rejection
    rejection_reason = models.TextField(blank=True)
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_tests')
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.request_number} - {self.patient.full_name} - {self.test.name}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            prefix = "LAB"
            year = timezone.now().year
            month = timezone.now().month
            last_req = LabRequest.objects.filter(request_number__startswith=f"{prefix}{year}{month:02d}").order_by('-id').first()
            if last_req:
                last_num = int(last_req.request_number[-6:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.request_number = f"{prefix}{year}{month:02d}{new_num:06d}"
        
        super().save(*args, **kwargs)
    
    def collect_specimen(self, collected_by):
        """Mark specimen as collected"""
        self.specimen_collected_at = timezone.now()
        self.specimen_collected_by = collected_by
        self.status = 'collected'
        self.save()
    
    def start_processing(self, technician):
        """Start processing the test"""
        self.assigned_to = technician
        self.started_processing_at = timezone.now()
        self.status = 'processing'
        self.save()
    
    def complete_test(self, result_value, verified_by):
        """Complete the test with results"""
        self.result_value = result_value
        self.completed_at = timezone.now()
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.status = 'verified'
        self.save()
    
    def reject_test(self, reason, rejected_by):
        """Reject the test request"""
        self.rejection_reason = reason
        self.rejected_by = rejected_by
        self.status = 'rejected'
        self.save()


class LabResult(models.Model):
    """Detailed laboratory results for tests with multiple components"""
    
    lab_request = models.ForeignKey(LabRequest, on_delete=models.CASCADE, related_name='detailed_results')
    component_name = models.CharField(max_length=200)
    result_value = models.CharField(max_length=200)
    unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=200, blank=True)
    is_abnormal = models.BooleanField(default=False)
    flag = models.CharField(max_length=10, blank=True, help_text="H=High, L=Low, A=Abnormal")
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['component_name']
    
    def __str__(self):
        return f"{self.lab_request.request_number} - {self.component_name}: {self.result_value}"