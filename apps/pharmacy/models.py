from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.accounts.models import User


class Medication(models.Model):
    """Medication/Drug master database"""
    
    DRUG_CATEGORIES = (
        ('antibiotic', 'Antibiotic'),
        ('analgesic', 'Analgesic'),
        ('antihypertensive', 'Antihypertensive'),
        ('antidiabetic', 'Antidiabetic'),
        ('antimalarial', 'Antimalarial'),
        ('antiretroviral', 'Antiretroviral'),
        ('vaccine', 'Vaccine'),
        ('vitamin', 'Vitamin/Supplement'),
        ('cns', 'CNS Drug'),
        ('respiratory', 'Respiratory Drug'),
        ('gi', 'Gastrointestinal Drug'),
        ('other', 'Other'),
    )
    
    DRUG_FORMS = (
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('ointment', 'Ointment/Cream'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('suppository', 'Suppository'),
        ('suspension', 'Suspension'),
    )
    
    generic_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)
    drug_code = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=20, choices=DRUG_CATEGORIES)
    drug_form = models.CharField(max_length=20, choices=DRUG_FORMS)
    strength = models.CharField(max_length=100, help_text="e.g., 500mg, 10mg/ml")
    
    # Pharmacy details
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=100)
    reorder_quantity = models.IntegerField(default=500)
    
    # Prescription details
    requires_prescription = models.BooleanField(default=True)
    is_controlled = models.BooleanField(default=False, help_text="Controlled substance")
    
    # Safety
    common_allergies = models.TextField(blank=True)
    contraindications = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    precautions = models.TextField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['generic_name']
    
    def __str__(self):
        return f"{self.generic_name} {self.strength} ({self.get_drug_form_display()})"
    
    def update_stock(self, quantity, transaction_type):
        """Update stock level"""
        if transaction_type == 'issue':
            self.current_stock -= quantity
        elif transaction_type == 'receive':
            self.current_stock += quantity
        
        self.save()
        
        # Create stock transaction record
        StockTransaction.objects.create(
            medication=self,
            quantity=quantity,
            transaction_type=transaction_type,
            stock_after=self.current_stock
        )
    
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level


class Prescription(models.Model):
    """Patient prescription record"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('partial', 'Partially Dispensed'),
        ('dispensed', 'Fully Dispensed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    
    ROUTE_CHOICES = (
        ('oral', 'Oral'),
        ('iv', 'Intravenous'),
        ('im', 'Intramuscular'),
        ('sc', 'Subcutaneous'),
        ('topical', 'Topical'),
        ('inhalation', 'Inhalation'),
        ('rectal', 'Rectal'),
    )
    
    prescription_number = models.CharField(max_length=50, unique=True, db_index=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='prescriptions')
    prescribing_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    
    # Medication details
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='prescriptions')
    dosage = models.CharField(max_length=100, help_text="e.g., 1 tablet")
    frequency = models.CharField(max_length=100, help_text="e.g., Twice daily")
    duration = models.CharField(max_length=100, help_text="e.g., 7 days")
    quantity = models.IntegerField()
    route = models.CharField(max_length=20, choices=ROUTE_CHOICES, default='oral')
    
    # Instructions
    special_instructions = models.TextField(blank=True)
    food_instructions = models.CharField(max_length=200, blank=True, help_text="Take with/without food")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    dispensed_quantity = models.IntegerField(default=0)
    
    # Refills
    refills_allowed = models.IntegerField(default=0)
    refills_remaining = models.IntegerField(default=0)
    
    # Timestamps
    prescribed_at = models.DateTimeField(auto_now_add=True)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensed_prescriptions')
    
    # Notes
    clinical_notes = models.TextField(blank=True)
    cancelled_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-prescribed_at']
        indexes = [
            models.Index(fields=['prescription_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['prescribed_at']),
        ]
    
    def __str__(self):
        return f"{self.prescription_number} - {self.patient.full_name} - {self.medication.generic_name}"
    
    def save(self, *args, **kwargs):
        if not self.prescription_number:
            prefix = "RX"
            year = timezone.now().year
            month = timezone.now().month
            last_rx = Prescription.objects.filter(prescription_number__startswith=f"{prefix}{year}{month:02d}").order_by('-id').first()
            if last_rx:
                last_num = int(last_rx.prescription_number[-6:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.prescription_number = f"{prefix}{year}{month:02d}{new_num:06d}"
        
        self.refills_remaining = self.refills_allowed
        
        # Check for drug interactions and allergies
        self.check_safety_alerts()
        
        super().save(*args, **kwargs)
    
    def check_safety_alerts(self):
        """Check for drug allergies and interactions"""
        alerts = []
        
        # Check patient allergies
        patient_allergies = self.patient.allergies.filter(severity__in=['severe', 'life_threatening'])
        for allergy in patient_allergies:
            if allergy.allergen.lower() in self.medication.generic_name.lower():
                alerts.append({
                    'type': 'allergy',
                    'severity': allergy.severity,
                    'message': f"Patient has {allergy.severity} allergy to {allergy.allergen}"
                })
        
        # Check for duplicate medications from other prescriptions
        duplicate_prescriptions = Prescription.objects.filter(
            patient=self.patient,
            medication=self.medication,
            status__in=['pending', 'partial']
        ).exclude(id=self.id)
        
        if duplicate_prescriptions.exists():
            alerts.append({
                'type': 'duplicate',
                'severity': 'warning',
                'message': f"Patient already has an active prescription for {self.medication.generic_name}"
            })
        
        return alerts
    
    def dispense(self, quantity, dispensed_by):
        """Dispense medication"""
        self.dispensed_quantity += quantity
        if self.dispensed_quantity >= self.quantity:
            self.status = 'dispensed'
        else:
            self.status = 'partial'
        
        self.dispensed_at = timezone.now()
        self.dispensed_by = dispensed_by
        self.save()
        
        # Update stock
        self.medication.update_stock(quantity, 'issue')


class StockTransaction(models.Model):
    """Pharmacy stock transaction log"""
    
    TRANSACTION_TYPES = (
        ('receive', 'Stock Received'),
        ('issue', 'Stock Issued'),
        ('adjustment', 'Stock Adjustment'),
        ('return', 'Stock Return'),
        ('expiry', 'Expired Stock'),
    )
    
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='transactions')
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    stock_before = models.IntegerField()
    stock_after = models.IntegerField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.medication.generic_name} - {self.transaction_type} - {self.quantity} units"