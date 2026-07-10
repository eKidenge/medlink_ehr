from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.visits.models import Visit
from apps.accounts.models import User


class Triage(models.Model):
    """Comprehensive Triage Assessment Model"""
    
    PRIORITY_CHOICES = (
        ('resuscitation', 'Resuscitation - Immediate life-threatening'),
        ('emergency', 'Emergency - Very urgent'),
        ('urgent', 'Urgent - Urgent'),
        ('less_urgent', 'Less Urgent - Standard'),
        ('non_urgent', 'Non Urgent - Can wait'),
    )
    
    COLOUR_CODES = {
        'resuscitation': 'Red',
        'emergency': 'Orange',
        'urgent': 'Yellow',
        'less_urgent': 'Green',
        'non_urgent': 'Blue',
    }
    
    AVPU_CHOICES = (
        ('A', 'Alert'),
        ('V', 'Responds to Voice'),
        ('P', 'Responds to Pain'),
        ('U', 'Unresponsive'),
    )
    
    # Basic Information
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='triage_assessment')
    triage_officer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triage_assessments')
    
    # Vital Signs (simplified for triage)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(300)])
    respiratory_rate = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    systolic_bp = models.IntegerField(null=True, blank=True)
    diastolic_bp = models.IntegerField(null=True, blank=True)
    oxygen_saturation = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    blood_glucose = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Triage Scoring
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    colour_code = models.CharField(max_length=10, editable=False)
    triage_score = models.IntegerField(default=0, help_text="Calculated triage score 0-10")
    
    # Chief Complaint Categories
    complaint_category = models.CharField(max_length=100, blank=True)
    mechanism_of_injury = models.TextField(blank=True)
    
    # Neurological Assessment
    avpu_score = models.CharField(max_length=1, choices=AVPU_CHOICES, default='A')
    glasgow_coma_score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(3), MaxValueValidator(15)])
    pupil_response = models.CharField(max_length=100, blank=True)
    
    # Pain Assessment
    pain_score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(10)])
    pain_location = models.CharField(max_length=200, blank=True)
    
    # Respiratory Assessment
    breathing_difficulty = models.BooleanField(default=False)
    breath_sounds = models.CharField(max_length=200, blank=True)
    use_accessory_muscles = models.BooleanField(default=False)
    
    # Cardiovascular Assessment
    capillary_refill = models.IntegerField(null=True, blank=True, help_text="Seconds")
    peripheral_pulses = models.CharField(max_length=100, blank=True)
    skin_turgor = models.CharField(max_length=100, blank=True)
    
    # Disability/Neurological
    limb_movement = models.CharField(max_length=200, blank=True)
    speech = models.CharField(max_length=200, blank=True)
    
    # Exposure
    rash = models.BooleanField(default=False)
    rash_description = models.TextField(blank=True)
    bruises = models.BooleanField(default=False)
    swelling = models.BooleanField(default=False)
    swelling_location = models.CharField(max_length=200, blank=True)
    
    # Risk Factors
    is_pregnant = models.BooleanField(default=False)
    pregnancy_weeks = models.IntegerField(null=True, blank=True)
    is_diabetic = models.BooleanField(default=False)
    is_hypertensive = models.BooleanField(default=False)
    is_asthmatic = models.BooleanField(default=False)
    is_immunocompromised = models.BooleanField(default=False)
    
    # Special Circumstances
    is_elderly = models.BooleanField(default=False, help_text="Age > 65")
    is_child = models.BooleanField(default=False, help_text="Age < 5")
    is_trauma_patient = models.BooleanField(default=False)
    
    # Interventions during triage
    oxygen_given = models.BooleanField(default=False)
    oxygen_flow_rate = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    iv_line_placed = models.BooleanField(default=False)
    medications_given = models.TextField(blank=True)
    
    # Disposition
    disposition = models.CharField(max_length=100, blank=True)
    referred_to = models.CharField(max_length=200, blank=True)
    
    # Assessment Notes
    triage_notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Timestamps
    triage_start = models.DateTimeField(auto_now_add=True)
    triage_completed = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_triages')
    
    class Meta:
        verbose_name_plural = "Triage Assessments"
        indexes = [
            models.Index(fields=['visit']),
            models.Index(fields=['priority']),
            models.Index(fields=['triage_start']),
        ]
    
    def __str__(self):
        return f"Triage for {self.visit.visit_number} - {self.get_priority_display()}"
    
    def save(self, *args, **kwargs):
        # Set colour code based on priority
        self.colour_code = self.COLOUR_CODES.get(self.priority, 'White')
        
        # Calculate triage score
        self.triage_score = self.calculate_triage_score()
        
        # Update visit priority based on triage
        if self.priority == 'resuscitation':
            self.visit.priority = 'critical'
        elif self.priority == 'emergency':
            self.visit.priority = 'emergency'
        elif self.priority == 'urgent':
            self.visit.priority = 'urgent'
        else:
            self.visit.priority = 'routine'
        
        self.visit.status = 'waiting'
        self.visit.nurse = self.triage_officer
        self.visit.triage_time = self.triage_start
        self.visit.save()
        
        super().save(*args, **kwargs)
    
    def calculate_triage_score(self):
        """Calculate triage score based on multiple factors"""
        score = 0
        
        # Vital signs scoring
        if self.heart_rate:
            if self.heart_rate < 40 or self.heart_rate > 140:
                score += 3
            elif self.heart_rate < 50 or self.heart_rate > 120:
                score += 2
            elif self.heart_rate < 60 or self.heart_rate > 100:
                score += 1
        
        if self.systolic_bp:
            if self.systolic_bp < 90:
                score += 3
            elif self.systolic_bp < 100:
                score += 2
        
        if self.respiratory_rate:
            if self.respiratory_rate < 8 or self.respiratory_rate > 30:
                score += 3
            elif self.respiratory_rate < 10 or self.respiratory_rate > 24:
                score += 2
        
        if self.oxygen_saturation:
            if self.oxygen_saturation < 90:
                score += 3
            elif self.oxygen_saturation < 94:
                score += 2
        
        # Consciousness scoring
        if self.avpu_score != 'A':
            score += 3
        if self.glasgow_coma_score and self.glasgow_coma_score < 13:
            score += 3
        
        # Pain scoring
        if self.pain_score and self.pain_score >= 7:
            score += 2
        elif self.pain_score and self.pain_score >= 4:
            score += 1
        
        # Risk factors
        if self.is_elderly or self.is_child:
            score += 1
        if self.is_pregnant:
            score += 1
        if self.is_trauma_patient:
            score += 1
        
        # Determine priority based on score
        if score >= 8:
            self.priority = 'resuscitation'
        elif score >= 6:
            self.priority = 'emergency'
        elif score >= 4:
            self.priority = 'urgent'
        elif score >= 2:
            self.priority = 'less_urgent'
        else:
            self.priority = 'non_urgent'
        
        return min(score, 10)
    
    def complete_triage(self, user):
        """Mark triage as completed"""
        self.triage_completed = timezone.now()
        self.completed_by = user
        self.save()


class TriageQueue(models.Model):
    """Triage queue management"""
    
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='triage_queue')
    position = models.IntegerField()
    estimated_wait_time = models.IntegerField(default=0, help_text="Minutes")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='triage_assignments')
    called_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"Queue position {self.position} - {self.visit.visit_number}"