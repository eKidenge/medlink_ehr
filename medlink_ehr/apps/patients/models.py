from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image


class Patient(models.Model):
    """Comprehensive Patient Model"""
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    MARITAL_STATUS = (
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
    )
    
    BLOOD_TYPE = (
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('unknown', 'Unknown'),
    )
    
    ID_TYPE = (
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('alien_id', 'Alien ID'),
        ('birth_cert', 'Birth Certificate'),
        ('none', 'None'),
    )
    
    # Primary Identifiers
    patient_number = models.CharField(max_length=50, unique=True, db_index=True)
    mrn_number = models.CharField(max_length=50, unique=True, db_index=True)  # Medical Record Number
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_code_data = models.TextField(blank=True)
    
    # Personal Information
    title = models.CharField(max_length=10, blank=True)
    first_name = models.CharField(max_length=100, db_index=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, db_index=True)
    maiden_name = models.CharField(max_length=100, blank=True)
    
    # Identification
    id_type = models.CharField(max_length=20, choices=ID_TYPE, default='national_id')
    identification_number = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)
    passport_number = models.CharField(max_length=20, blank=True)
    birth_certificate_number = models.CharField(max_length=50, blank=True)
    nhif_number = models.CharField(max_length=20, blank=True, db_index=True)  # National Hospital Insurance Fund
    other_id = models.CharField(max_length=100, blank=True)
    
    # Contact Information
    phone_primary = models.CharField(max_length=15, validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')], db_index=True)
    phone_secondary = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True, null=True)
    alternative_email = models.EmailField(blank=True)
    
    # Demographic Information
    date_of_birth = models.DateField()
    age = models.PositiveIntegerField(editable=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, db_index=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS, default='single')
    blood_type = models.CharField(max_length=10, choices=BLOOD_TYPE, default='unknown')
    
    # Address Information
    county = models.CharField(max_length=100, blank=True, db_index=True)
    sub_county = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=100, blank=True)
    sub_location = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    physical_address = models.TextField(blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_alternative = models.CharField(max_length=15, blank=True)
    
    # Employment Information
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=200, blank=True)
    employer_phone = models.CharField(max_length=15, blank=True)
    employer_address = models.TextField(blank=True)
    
    # Insurance Information
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_number = models.CharField(max_length=100, blank=True)
    insurance_valid_until = models.DateField(null=True, blank=True)
    
    # Next of Kin
    next_of_kin_name = models.CharField(max_length=200, blank=True)
    next_of_kin_relationship = models.CharField(max_length=100, blank=True)
    next_of_kin_phone = models.CharField(max_length=15, blank=True)
    next_of_kin_address = models.TextField(blank=True)
    
    # Medical Flags
    is_deceased = models.BooleanField(default=False)
    date_of_death = models.DateField(null=True, blank=True)
    cause_of_death = models.TextField(blank=True)
    has_allergies = models.BooleanField(default=False)
    has_chronic_diseases = models.BooleanField(default=False)
    is_pregnant = models.BooleanField(default=False)
    expected_delivery_date = models.DateField(null=True, blank=True)
    is_disabled = models.BooleanField(default=False)
    disability_type = models.CharField(max_length=200, blank=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_patients')
    merged_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='merged_patients')
    is_merged = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_number']),
            models.Index(fields=['mrn_number']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['phone_primary']),
            models.Index(fields=['identification_number']),
            models.Index(fields=['nhif_number']),
            models.Index(fields=['county']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.patient_number} - {self.full_name}"
    
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def short_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        # Calculate age
        if self.date_of_birth:
            today = timezone.now().date()
            self.age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        
        # Generate patient number if not exists
        if not self.patient_number:
            prefix = "PAT"
            year = timezone.now().year
            last_patient = Patient.objects.filter(patient_number__startswith=f"{prefix}{year}").order_by('-id').first()
            if last_patient:
                last_num = int(last_patient.patient_number[-6:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.patient_number = f"{prefix}{year}{new_num:06d}"
        
        # Generate MRN if not exists
        if not self.mrn_number:
            self.mrn_number = f"MRN{timezone.now().year}{uuid.uuid4().hex[:8].upper()}"
        
        super().save(*args, **kwargs)
        
        # Generate QR code if not exists
        if not self.qr_code:
            self.generate_qr_code()
    
    def generate_qr_code(self):
        """Generate QR code containing patient information"""
        qr_data = {
            'patient_number': self.patient_number,
            'mrn': self.mrn_number,
            'name': self.full_name,
            'phone': self.phone_primary,
            'nhif': self.nhif_number if self.nhif_number else ''
        }
        
        import json
        qr_text = json.dumps(qr_data)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"qr_{self.patient_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)
        self.qr_code_data = qr_text
        self.save(update_fields=['qr_code', 'qr_code_data'])
    
    def merge_with(self, other_patient):
        """Merge this patient with another patient record"""
        # Move all related records to this patient
        related_models = [
            ('visits', 'visits'),
            ('admissions', 'admissions'),
            ('laboratory_requests', 'laboratory_requests'),
            ('prescriptions', 'prescriptions'),
            ('referrals', 'referrals'),
        ]
        
        for model_name, related_name in related_models:
            related_objects = getattr(other_patient, related_name).all()
            for obj in related_objects:
                obj.patient = self
                obj.save()
        
        other_patient.is_merged = True
        other_patient.merged_to = self
        other_patient.is_active = False
        other_patient.save()
    
    def get_photo(self):
        """Get patient photo if exists"""
        try:
            return self.photo.url
        except:
            return None


class PatientAllergy(models.Model):
    """Patient allergies tracking"""
    
    SEVERITY_CHOICES = (
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('life_threatening', 'Life Threatening'),
    )
    
    REACTION_CHOICES = (
        ('rash', 'Rash/Hives'),
        ('swelling', 'Swelling'),
        ('difficulty_breathing', 'Difficulty Breathing'),
        ('anaphylaxis', 'Anaphylaxis'),
        ('nausea', 'Nausea/Vomiting'),
        ('diarrhea', 'Diarrhea'),
        ('headache', 'Headache'),
        ('fever', 'Fever'),
        ('other', 'Other'),
    )
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergies')
    allergen = models.CharField(max_length=200)  # e.g., Penicillin, Peanuts, Latex
    allergen_type = models.CharField(max_length=100, blank=True)  # Medication, Food, Environmental
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    reaction = models.CharField(max_length=50, choices=REACTION_CHOICES, default='other')
    reaction_details = models.TextField(blank=True)
    onset_date = models.DateField(null=True, blank=True)
    confirmed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='confirmed_allergies')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-severity', 'allergen']
        verbose_name_plural = "Patient Allergies"
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.allergen} ({self.get_severity_display()})"


class PatientChronicDisease(models.Model):
    """Patient chronic diseases tracking"""
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('controlled', 'Controlled'),
        ('remission', 'Remission'),
        ('resolved', 'Resolved'),
    )
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='chronic_diseases')
    disease_name = models.CharField(max_length=200)
    icd10_code = models.CharField(max_length=20, blank=True)
    diagnosed_date = models.DateField()
    diagnosed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='diagnosed_diseases')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-diagnosed_date']
        verbose_name = "Chronic Disease"
        verbose_name_plural = "Chronic Diseases"
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.disease_name}"


class PatientVaccination(models.Model):
    """Patient vaccination history"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_name = models.CharField(max_length=200)
    dose_number = models.PositiveIntegerField()
    date_administered = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    administered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='administered_vaccines')
    batch_number = models.CharField(max_length=50, blank=True)
    facility_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_administered']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.vaccine_name} (Dose {self.dose_number})"


class PatientMedicalHistory(models.Model):
    """Past medical history"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_history')
    condition = models.CharField(max_length=200)
    icd10_code = models.CharField(max_length=20, blank=True)
    diagnosed_date = models.DateField(null=True, blank=True)
    resolved_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-diagnosed_date']
        verbose_name_plural = "Medical History"
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.condition}"


class PatientSurgicalHistory(models.Model):
    """Surgical history"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='surgeries')
    procedure_name = models.CharField(max_length=200)
    surgery_date = models.DateField()
    hospital = models.CharField(max_length=200, blank=True)
    surgeon = models.CharField(max_length=200, blank=True)
    indication = models.TextField(blank=True)
    complications = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-surgery_date']
        verbose_name_plural = "Surgical History"
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.procedure_name} ({self.surgery_date})"