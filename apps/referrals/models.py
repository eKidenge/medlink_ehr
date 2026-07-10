from django.db import models
from django.utils import timezone
from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.accounts.models import User


class Referral(models.Model):
    """Patient referral management"""
    
    REFERRAL_TYPE = (
        ('internal', 'Internal - Same Facility'),
        ('external', 'External - Different Facility'),
        ('emergency', 'Emergency Transfer'),
        ('specialist', 'Specialist Consultation'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    PRIORITY_CHOICES = (
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    )
    
    referral_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Patient Information
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='referrals_outgoing')
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='referrals')
    
    # Referral Details
    referral_type = models.CharField(max_length=20, choices=REFERRAL_TYPE)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='routine')
    
    # From
    referring_facility = models.CharField(max_length=200)
    referring_department = models.CharField(max_length=200, blank=True)
    referring_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    
    # To
    receiving_facility = models.CharField(max_length=200)
    receiving_department = models.CharField(max_length=200, blank=True)
    receiving_doctor = models.CharField(max_length=200, blank=True)
    receiving_contact = models.CharField(max_length=20, blank=True)
    
    # Clinical Information
    reason_for_referral = models.TextField()
    clinical_summary = models.TextField()
    provisional_diagnosis = models.TextField()
    investigations_done = models.TextField(blank=True)
    treatment_given = models.TextField(blank=True)
    
    # Documents
    referral_letter = models.FileField(upload_to='referrals/', null=True, blank=True)
    attachments = models.FileField(upload_to='referrals/attachments/', null=True, blank=True)
    
    # QR Code for secure access
    qr_code = models.ImageField(upload_to='referrals/qr/', null=True, blank=True)
    access_token = models.CharField(max_length=100, unique=True, null=True, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Feedback
    feedback_from_receiving = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_referrals')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_referrals')
    cancelled_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['referral_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['referring_facility', 'receiving_facility']),
        ]
    
    def __str__(self):
        return f"{self.referral_number} - {self.patient.full_name} to {self.receiving_facility}"
    
    def save(self, *args, **kwargs):
        if not self.referral_number:
            prefix = "REF"
            year = timezone.now().year
            month = timezone.now().month
            last_ref = Referral.objects.filter(referral_number__startswith=f"{prefix}{year}{month:02d}").order_by('-id').first()
            if last_ref:
                last_num = int(last_ref.referral_number[-6:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.referral_number = f"{prefix}{year}{month:02d}{new_num:06d}"
        
        super().save(*args, **kwargs)
    
    def approve(self, approved_by):
        """Approve referral"""
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = approved_by
        self.save()
    
    def complete(self):
        """Mark referral as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def cancel(self, reason, cancelled_by):
        """Cancel referral"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_reason = reason
        self.save()


class ReferralNote(models.Model):
    """Additional notes for referrals"""
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_notes')
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.referral.referral_number} by {self.author.get_full_name()}"