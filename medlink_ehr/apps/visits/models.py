from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from apps.patients.models import Patient
from apps.accounts.models import User


class Visit(models.Model):
    """Comprehensive Visit/Encounter Model"""
    
    VISIT_TYPE = (
        ('outpatient', 'Outpatient'),
        ('inpatient', 'Inpatient'),
        ('emergency', 'Emergency'),
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('antenatal', 'Antenatal Care'),
        ('postnatal', 'Postnatal Care'),
        ('wellness', 'Wellness Check'),
        ('telemedicine', 'Telemedicine'),
        ('home_visit', 'Home Visit'),
    )
    
    STATUS_CHOICES = (
        ('registered', 'Registered'),
        ('check_in', 'Checked In'),
        ('triage', 'In Triage'),
        ('waiting', 'Waiting'),
        ('consultation', 'In Consultation'),
        ('investigation', 'Under Investigation'),
        ('treatment', 'Under Treatment'),
        ('observation', 'Under Observation'),
        ('admitted', 'Admitted'),
        ('discharged', 'Discharged'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )
    
    PRIORITY_CHOICES = (
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
        ('critical', 'Critical'),
    )
    
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('insurance', 'Insurance'),
        ('waived', 'Waived'),
        ('bad_debt', 'Bad Debt'),
    )
    
    # Basic Information
    visit_number = models.CharField(max_length=50, unique=True, db_index=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE, default='outpatient')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='routine')
    
    # Clinical Team
    primary_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_visits')
    referring_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_visits')
    nurse = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='nurse_visits')
    clinical_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='co_visits')
    
    # Timestamps
    registration_time = models.DateTimeField(auto_now_add=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    triage_time = models.DateTimeField(null=True, blank=True)
    consultation_start = models.DateTimeField(null=True, blank=True)
    consultation_end = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)
    
    # Waiting Times (for analytics)
    waiting_time_triage = models.IntegerField(default=0, help_text="Minutes waited for triage")
    waiting_time_consultation = models.IntegerField(default=0, help_text="Minutes waited for consultation")
    total_waiting_time = models.IntegerField(default=0, help_text="Total waiting time in minutes")
    
    # Clinical Information
    chief_complaint = models.TextField()
    history_of_present_illness = models.TextField(blank=True)
    review_of_systems = models.JSONField(default=dict, blank=True)
    past_medical_history = models.TextField(blank=True)
    family_history = models.TextField(blank=True)
    social_history = models.TextField(blank=True)
    
    # Diagnosis
    provisional_diagnosis = models.TextField(blank=True)
    final_diagnosis = models.TextField(blank=True)
    icd10_codes = models.JSONField(default=list, blank=True)  # List of ICD-10 codes
    differential_diagnosis = models.TextField(blank=True)
    
    # Treatment
    treatment_plan = models.TextField(blank=True)
    procedures_performed = models.JSONField(default=list, blank=True)
    outcome = models.TextField(blank=True)
    discharge_instructions = models.TextField(blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='followup_visits')
    
    # Payment
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    insurance_claim_number = models.CharField(max_length=100, blank=True)
    
    # Flags
    is_emergency = models.BooleanField(default=False)
    requires_admission = models.BooleanField(default=False)
    requires_referral = models.BooleanField(default=False)
    is_telemedicine = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    
    # Referral Information
    referred_from = models.CharField(max_length=200, blank=True)
    referred_to = models.CharField(max_length=200, blank=True)
    referral_reason = models.TextField(blank=True)
    
    # Clinical Notes (for multiple entries)
    clinical_notes = models.JSONField(default=list, blank=True)
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_visits')
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_visits')
    
    class Meta:
        ordering = ['-registration_time']
        indexes = [
            models.Index(fields=['visit_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['registration_time']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['primary_doctor', 'status']),
        ]
    
    def __str__(self):
        return f"{self.visit_number} - {self.patient.full_name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.visit_number:
            prefix = "VIS"
            year = timezone.now().year
            month = timezone.now().month
            last_visit = Visit.objects.filter(visit_number__startswith=f"{prefix}{year}{month:02d}").order_by('-id').first()
            if last_visit:
                last_num = int(last_visit.visit_number[-6:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.visit_number = f"{prefix}{year}{month:02d}{new_num:06d}"
        
        # Calculate total waiting time if consultation started
        if self.consultation_start and self.check_in_time:
            self.total_waiting_time = int((self.consultation_start - self.check_in_time).total_seconds() / 60)
        
        super().save(*args, **kwargs)
    
    def calculate_waiting_times(self):
        """Calculate all waiting time metrics"""
        if self.check_in_time and self.triage_time:
            self.waiting_time_triage = int((self.triage_time - self.check_in_time).total_seconds() / 60)
        if self.triage_time and self.consultation_start:
            self.waiting_time_consultation = int((self.consultation_start - self.triage_time).total_seconds() / 60)
        self.save()
    
    def complete_visit(self):
        """Mark visit as completed"""
        self.status = 'completed'
        self.completion_time = timezone.now()
        self.save()
    
    def cancel_visit(self, reason, cancelled_by):
        """Cancel the visit"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.cancelled_by = cancelled_by
        self.save()
    
    @property
    def duration_minutes(self):
        """Calculate total visit duration"""
        if self.completion_time and self.registration_time:
            return int((self.completion_time - self.registration_time).total_seconds() / 60)
        return 0


class ClinicalNote(models.Model):
    """Detailed clinical notes for each visit"""
    
    NOTE_TYPE = (
        ('progress', 'Progress Note'),
        ('doctor', 'Doctor\'s Note'),
        ('nurse', 'Nurse\'s Note'),
        ('discharge', 'Discharge Summary'),
        ('referral', 'Referral Note'),
        ('consultation', 'Consultation Note'),
    )
    
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='clinical_notes_detail')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clinical_notes')
    
    # SOAP Format
    subjective = models.TextField(help_text="Patient's symptoms and complaints")
    objective = models.TextField(help_text="Physical exam findings and test results")
    assessment = models.TextField(help_text="Diagnosis and assessment")
    plan = models.TextField(help_text="Treatment plan and next steps")
    
    # Additional sections
    review_of_systems = models.JSONField(default=dict, blank=True)
    physical_examination = models.JSONField(default=dict, blank=True)
    investigations = models.JSONField(default=list, blank=True)
    medications_prescribed = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_shared = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.visit.visit_number} - {self.get_note_type_display()} by {self.author.get_full_name()}"


class Vitals(models.Model):
    """Patient vitals recording"""
    
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='vitals')
    recorded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recorded_vitals')
    
    # Basic Vitals
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="°C")
    pulse_rate = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(300)], help_text="beats/min")
    respiratory_rate = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="breaths/min")
    systolic_bp = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(300)], help_text="mmHg")
    diastolic_bp = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(200)], help_text="mmHg")
    
    # Advanced Vitals
    oxygen_saturation = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="%")
    blood_glucose = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="mmol/L")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="kg")
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="cm")
    bmi = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    # Pain Assessment
    pain_score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(10)], help_text="0-10 scale")
    pain_location = models.CharField(max_length=200, blank=True)
    
    # Mental Status
    glasgow_coma_score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(3), MaxValueValidator(15)])
    avpu_score = models.CharField(max_length=1, blank=True, help_text="A=Alert, V=Verbal, P=Pain, U=Unresponsive")
    
    # Maternal (if applicable)
    fundal_height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="cm")
    fetal_heart_rate = models.IntegerField(null=True, blank=True)
    contractions = models.CharField(max_length=100, blank=True)
    
    # Pediatric
    head_circumference = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="cm")
    
    # Nutritional
    muac = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Mid-Upper Arm Circumference (cm)")
    
    # Notes
    vitals_notes = models.TextField(blank=True)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Vitals"
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['recorded_at']),
        ]
    
    def __str__(self):
        return f"Vitals for {self.visit.visit_number} at {self.recorded_at}"
    
    def save(self, *args, **kwargs):
        # Calculate BMI
        if self.weight and self.height:
            height_m = self.height / 100
            self.bmi = self.weight / (height_m * height_m)
        super().save(*args, **kwargs)
    
    @property
    def blood_pressure_display(self):
        if self.systolic_bp and self.diastolic_bp:
            return f"{self.systolic_bp}/{self.diastolic_bp}"
        return "Not recorded"
    
    @property
    def is_critical(self):
        """Check if any vitals are in critical range"""
        if self.temperature and (self.temperature < 35 or self.temperature > 39):
            return True
        if self.systolic_bp and self.systolic_bp < 90:
            return True
        if self.oxygen_saturation and self.oxygen_saturation < 90:
            return True
        if self.pulse_rate and (self.pulse_rate < 50 or self.pulse_rate > 120):
            return True
        if self.glasgow_coma_score and self.glasgow_coma_score < 13:
            return True
        return False