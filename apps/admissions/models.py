from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.accounts.models import User


class Ward(models.Model):
    """Hospital ward management"""
    
    WARD_TYPES = (
        ('general', 'General Ward'),
        ('private', 'Private Ward'),
        ('vip', 'VIP Suite'),
        ('icu', 'Intensive Care Unit'),
        ('hdu', 'High Dependency Unit'),
        ('pediatric', 'Pediatric Ward'),
        ('maternity', 'Maternity Ward'),
        ('isolation', 'Isolation Ward'),
        ('psychiatric', 'Psychiatric Ward'),
        ('rehabilitation', 'Rehabilitation'),
    )
    
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=20, choices=WARD_TYPES)
    floor = models.CharField(max_length=50, blank=True)
    building = models.CharField(max_length=100, blank=True)
    
    # Capacity
    total_beds = models.IntegerField()
    available_beds = models.IntegerField()
    occupied_beds = models.IntegerField(default=0)
    
    # Staff
    ward_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_wards')
    in_charge_nurse = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incharge_wards')
    
    # Services
    has_oxygen = models.BooleanField(default=True)
    has_suction = models.BooleanField(default=True)
    has_monitoring = models.BooleanField(default=False)
    has_private_bathroom = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_under_maintenance = models.BooleanField(default=False)
    
    # Daily rates
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.available_beds}/{self.total_beds} beds available)"
    
    def update_bed_counts(self):
        """Update available and occupied bed counts"""
        self.occupied_beds = Bed.objects.filter(ward=self, is_occupied=True).count()
        self.available_beds = self.total_beds - self.occupied_beds
        self.save(update_fields=['available_beds', 'occupied_beds'])
    
    def has_available_beds(self):
        return self.available_beds > 0


class Bed(models.Model):
    """Individual bed management"""
    
    BED_TYPES = (
        ('standard', 'Standard'),
        ('icu', 'ICU Bed'),
        ('pediatric', 'Pediatric Bed'),
        ('maternity', 'Maternity Bed'),
        ('isolation', 'Isolation Bed'),
        ('bariatric', 'Bariatric Bed'),
    )
    
    bed_number = models.CharField(max_length=20)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    bed_type = models.CharField(max_length=20, choices=BED_TYPES, default='standard')
    
    # Status
    is_occupied = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    is_under_maintenance = models.BooleanField(default=False)
    
    # Features
    has_oxygen_outlet = models.BooleanField(default=False)
    has_suction_outlet = models.BooleanField(default=False)
    has_call_bell = models.BooleanField(default=True)
    has_side_rails = models.BooleanField(default=True)
    has_overbed_table = models.BooleanField(default=True)
    
    # Current patient (if occupied)
    current_patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_bed')
    current_admission = models.ForeignKey('Admission', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bed')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['ward', 'bed_number']
        ordering = ['ward', 'bed_number']
    
    def __str__(self):
        return f"{self.ward.code} - Bed {self.bed_number}"
    
    def occupy(self, admission):
        """Occupy the bed"""
        self.is_occupied = True
        self.is_available = False
        self.current_admission = admission
        self.current_patient = admission.patient
        self.save()
        self.ward.update_bed_counts()
    
    def vacate(self):
        """Vacate the bed"""
        self.is_occupied = False
        self.is_available = True
        self.current_admission = None
        self.current_patient = None
        self.save()
        self.ward.update_bed_counts()


class Admission(models.Model):
    """Patient admission record"""
    
    ADMISSION_TYPE = (
        ('emergency', 'Emergency Admission'),
        ('elective', 'Elective Admission'),
        ('transfer', 'Transfer from another facility'),
        ('postnatal', 'Postnatal Admission'),
        ('antenatal', 'Antenatal Admission'),
    )
    
    STATUS_CHOICES = (
        ('admitted', 'Admitted'),
        ('in_treatment', 'In Treatment'),
        ('stable', 'Stable'),
        ('critical', 'Critical'),
        ('discharged', 'Discharged'),
        ('transferred', 'Transferred'),
        ('expired', 'Expired'),
        ('absconded', 'Absconded'),
    )
    
    DISCHARGE_STATUS = (
        ('home', 'Discharged Home'),
        ('transfer', 'Transferred to Another Facility'),
        ('ama', 'Discharged Against Medical Advice'),
        ('deceased', 'Deceased'),
        ('absconded', 'Absconded'),
    )
    
    # Basic Information
    admission_number = models.CharField(max_length=50, unique=True, db_index=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='admissions')
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='admissions')
    admission_type = models.CharField(max_length=20, choices=ADMISSION_TYPE)
    
    # Ward and Bed
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='admissions')
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='admissions')
    
    # Clinical Information
    admitting_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admissions_made')
    primary_diagnosis = models.TextField()
    secondary_diagnosis = models.TextField(blank=True)
    admitting_notes = models.TextField()
    
    # Condition
    condition_on_admission = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='admitted')
    
    # Timestamps
    admission_date = models.DateTimeField(auto_now_add=True)
    expected_discharge_date = models.DateField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    
    # Discharge Information
    discharge_status = models.CharField(max_length=20, choices=DISCHARGE_STATUS, blank=True)
    discharge_summary = models.TextField(blank=True)
    discharge_instructions = models.TextField(blank=True)
    discharged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='discharges')
    
    # Financial
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Transfer Information
    transferred_from = models.CharField(max_length=200, blank=True)
    transferred_to = models.CharField(max_length=200, blank=True)
    transfer_reason = models.TextField(blank=True)
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_admissions')
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-admission_date']
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['admission_date']),
            models.Index(fields=['ward', 'status']),
        ]
    
    def __str__(self):
        return f"{self.admission_number} - {self.patient.full_name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.admission_number:
            prefix = "ADM"
            year = timezone.now().year
            month = timezone.now().month
            last_adm = Admission.objects.filter(admission_number__startswith=f"{prefix}{year}{month:02d}").order_by('-id').first()
            if last_adm:
                last_num = int(last_adm.admission_number[-6:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.admission_number = f"{prefix}{year}{month:02d}{new_num:06d}"
        
        super().save(*args, **kwargs)
    
    def discharge(self, discharge_status, discharge_summary, discharged_by):
        """Discharge patient"""
        self.discharge_date = timezone.now()
        self.discharge_status = discharge_status
        self.discharge_summary = discharge_summary
        self.discharged_by = discharged_by
        self.status = 'discharged'
        self.save()
        
        # Vacate bed
        if self.bed:
            self.bed.vacate()
        
        # Update visit
        self.visit.complete_visit()
    
    @property
    def length_of_stay_days(self):
        """Calculate length of stay in days"""
        end_date = self.discharge_date or timezone.now()
        return (end_date - self.admission_date).days
    
    @property
    def length_of_stay_hours(self):
        """Calculate length of stay in hours"""
        end_date = self.discharge_date or timezone.now()
        return int((end_date - self.admission_date).total_seconds() / 3600)


class DailyRound(models.Model):
    """Daily clinical rounds for admitted patients"""
    
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='rounds')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rounds')
    
    # Clinical Findings
    subjective = models.TextField(help_text="Patient's complaints today")
    objective = models.TextField(help_text="Physical examination findings")
    assessment = models.TextField(help_text="Current assessment")
    plan = models.TextField(help_text="Today's treatment plan")
    
    # Vitals (can be linked to vitals model)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    oxygen_saturation = models.IntegerField(null=True, blank=True)
    
    # Orders
    medication_changes = models.TextField(blank=True)
    investigations_ordered = models.TextField(blank=True)
    diet_ordered = models.CharField(max_length=200, blank=True)
    
    round_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-round_date']
    
    def __str__(self):
        return f"Round for {self.admission.patient.full_name} on {self.round_date.date()}"