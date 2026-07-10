"""
Custom permission classes for MedLink EHR system
Handles role-based access control (RBAC) for all apps
"""
from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAuthenticatedAndActive(BasePermission):
    """
    Allows access only to authenticated and active users (not locked).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_active and not request.user.account_locked


class IsAdminOrSuperAdmin(BasePermission):
    """
    Allows access only to admin or super admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'super_admin']
        )


class IsSuperAdmin(BasePermission):
    """
    Allows access only to super admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'super_admin'
        )


class IsDoctor(BasePermission):
    """
    Allows access only to doctors and clinical officers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['doctor', 'clinical_officer']
        )


class IsNurse(BasePermission):
    """
    Allows access only to nurses.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'nurse'
        )


class IsDoctorOrNurse(BasePermission):
    """
    Allows access only to doctors or nurses.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['doctor', 'clinical_officer', 'nurse']
        )


class IsLabTechnician(BasePermission):
    """
    Allows access only to laboratory technicians.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'lab_technician'
        )


class IsDoctorOrLabTech(BasePermission):
    """
    Allows access only to doctors or lab technicians.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['doctor', 'clinical_officer', 'lab_technician']
        )


class IsPharmacist(BasePermission):
    """
    Allows access only to pharmacists and pharmacy technicians.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['pharmacist', 'pharmacy_tech']
        )


class IsDoctorOrPharmacist(BasePermission):
    """
    Allows access only to doctors or pharmacists.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['doctor', 'clinical_officer', 'pharmacist']
        )


class IsRecordsOfficer(BasePermission):
    """
    Allows access only to medical records officers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'records_officer'
        )


class IsReceptionist(BasePermission):
    """
    Allows access only to receptionists.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['receptionist', 'cashier']
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Allows access to object owner or admin users.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin can access anything
        if request.user.role in ['admin', 'super_admin']:
            return True
        
        # Check if user is the owner of the object
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        if obj == request.user:
            return True
        
        return False


class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Write permissions are only allowed to the owner or admin
        if request.user.role in ['super_admin', 'admin']:
            return True
        
        # Check if user is the owner
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        return False


class IsOwnerOrStaff(BasePermission):
    """
    Allows access to object owners or staff members.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin staff can access anything
        if request.user.role in ['super_admin', 'admin']:
            return True
        
        # Check if user is the owner
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Check patient ownership for medical records
        if hasattr(obj, 'patient') and obj.patient:
            from apps.visits.models import Visit
            if request.user.role in ['doctor', 'clinical_officer']:
                return Visit.objects.filter(
                    patient=obj.patient,
                    primary_doctor=request.user
                ).exists()
        
        return False


class CanViewPatient(BasePermission):
    """
    Allows users to view patient records based on their role.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin and doctors can view all patients
        if request.user.role in ['super_admin', 'admin', 'doctor', 'clinical_officer', 'nurse']:
            return True
        
        # Lab techs can view patients with lab requests
        if request.user.role == 'lab_technician':
            return True
        
        # Pharmacists can view patients with prescriptions
        if request.user.role in ['pharmacist', 'pharmacy_tech']:
            return True
        
        # Records officers can view all patients
        if request.user.role == 'records_officer':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin can access any patient
        if request.user.role in ['super_admin', 'admin']:
            return True
        
        # Doctors can access patients they have seen
        if request.user.role in ['doctor', 'clinical_officer']:
            from apps.visits.models import Visit
            return Visit.objects.filter(
                patient=obj, 
                primary_doctor=request.user
            ).exists()
        
        # Nurses can access patients they have triaged
        if request.user.role == 'nurse':
            from apps.triage.models import Triage
            return Triage.objects.filter(
                visit__patient=obj, 
                triage_officer=request.user
            ).exists()
        
        # Lab techs can access patients with their lab requests
        if request.user.role == 'lab_technician':
            from apps.laboratory.models import LabRequest
            return LabRequest.objects.filter(
                patient=obj, 
                assigned_to=request.user
            ).exists()
        
        return False


class CanEditPatient(BasePermission):
    """
    Allows users to edit patient records.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['super_admin', 'admin', 'doctor', 'clinical_officer', 'records_officer']
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin can edit any patient
        if request.user.role in ['super_admin', 'admin', 'records_officer']:
            return True
        
        # Doctors can edit patients they have seen
        if request.user.role in ['doctor', 'clinical_officer']:
            from apps.visits.models import Visit
            return Visit.objects.filter(
                patient=obj, 
                primary_doctor=request.user
            ).exists()
        
        return False


class CanManageVisits(BasePermission):
    """
    Allows users to manage visits (check-in, triage, consultation).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in [
            'super_admin', 'admin', 'doctor', 'clinical_officer', 
            'nurse', 'receptionist'
        ]


class CanManageTriage(BasePermission):
    """
    Allows users to perform triage assessments.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['super_admin', 'admin', 'nurse', 'doctor', 'clinical_officer']


class CanManageAdmissions(BasePermission):
    """
    Allows users to manage patient admissions.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in [
            'super_admin', 'admin', 'doctor', 'clinical_officer', 'nurse'
        ]


class CanManageLaboratory(BasePermission):
    """
    Allows users to manage laboratory requests and results.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in [
            'super_admin', 'admin', 'doctor', 'clinical_officer', 'lab_technician'
        ]


class CanManagePharmacy(BasePermission):
    """
    Allows users to manage prescriptions and pharmacy inventory.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in [
            'super_admin', 'admin', 'doctor', 'clinical_officer', 'pharmacist', 'pharmacy_tech'
        ]


class CanManageReferrals(BasePermission):
    """
    Allows users to create and manage referrals.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in [
            'super_admin', 'admin', 'doctor', 'clinical_officer', 'nurse'
        ]


class CanViewReports(BasePermission):
    """
    Allows users to view and generate reports.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in [
            'super_admin', 'admin', 'doctor', 'clinical_officer', 
            'manager', 'records_officer'
        ]


class CanExportData(BasePermission):
    """
    Allows users to export data from the system.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['super_admin', 'admin', 'manager']


class CanManageUsers(BasePermission):
    """
    Allows users to manage system users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['super_admin', 'admin']


class CanViewAuditLogs(BasePermission):
    """
    Allows users to view audit logs.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['super_admin', 'admin']


class CanManageSystem(BasePermission):
    """
    Allows users to manage system settings.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['super_admin', 'admin']


class CanAccessDashboard(BasePermission):
    """
    Determines if user can access the dashboard.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # All authenticated users can access dashboard
        return True


class CanViewOwnProfile(BasePermission):
    """
    Allows users to view only their own profile.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Users can view and edit their own profile
        if obj == request.user:
            return True
        
        # Admins can view all profiles
        if request.user.role in ['super_admin', 'admin']:
            return True
        
        return False


class CanAccessFinancialData(BasePermission):
    """
    Allows access to financial data (billing, payments, insurance).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in ['super_admin', 'admin', 'cashier', 'manager']


class CanAccessClinicalData(BasePermission):
    """
    Allows access to clinical data (diagnosis, treatment, notes).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.role in [
            'super_admin', 'admin', 'doctor', 'clinical_officer', 
            'nurse', 'pharmacist', 'lab_technician'
        ]


class ReadOnlyForViewers(BasePermission):
    """
    Read-only access for viewers.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Viewers only have read access
        if request.user.role == 'viewer':
            return request.method in SAFE_METHODS
        
        return True
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.role == 'viewer':
            return request.method in SAFE_METHODS
        
        return True


# Role-based permission mapping for easy reference
ROLE_PERMISSIONS = {
    'super_admin': [
        'can_view_all', 'can_edit_all', 'can_delete_all', 'can_manage_users',
        'can_view_audit_logs', 'can_manage_system', 'can_export_data',
        'can_access_financial_data', 'can_access_clinical_data'
    ],
    'admin': [
        'can_view_all', 'can_edit_all', 'can_manage_users',
        'can_view_audit_logs', 'can_export_data',
        'can_access_financial_data', 'can_access_clinical_data'
    ],
    'doctor': [
        'can_view_patients', 'can_edit_patients', 'can_manage_visits',
        'can_manage_triage', 'can_manage_admissions', 'can_manage_laboratory',
        'can_manage_pharmacy', 'can_manage_referrals', 'can_view_reports',
        'can_access_clinical_data'
    ],
    'clinical_officer': [
        'can_view_patients', 'can_edit_patients', 'can_manage_visits',
        'can_manage_triage', 'can_manage_admissions', 'can_manage_laboratory',
        'can_manage_pharmacy', 'can_manage_referrals', 'can_view_reports',
        'can_access_clinical_data'
    ],
    'nurse': [
        'can_view_patients', 'can_manage_visits', 'can_manage_triage',
        'can_manage_admissions', 'can_access_clinical_data'
    ],
    'lab_technician': [
        'can_view_patients', 'can_manage_laboratory'
    ],
    'pharmacist': [
        'can_view_patients', 'can_manage_pharmacy'
    ],
    'pharmacy_tech': [
        'can_view_patients', 'can_manage_pharmacy'
    ],
    'records_officer': [
        'can_view_patients', 'can_edit_patients', 'can_view_reports'
    ],
    'receptionist': [
        'can_manage_visits'
    ],
    'cashier': [
        'can_access_financial_data'
    ],
    'manager': [
        'can_view_reports', 'can_export_data', 'can_access_financial_data'
    ],
    'viewer': [
        'read_only'
    ]
}


def has_permission(user, permission_name):
    """
    Helper function to check if a user has a specific permission.
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin has all permissions
    if user.role == 'super_admin':
        return True
    
    # Check if user has the specific permission
    if permission_name in ROLE_PERMISSIONS.get(user.role, []):
        return True
    
    return False


def get_user_permissions(user):
    """
    Returns a list of all permissions for a given user.
    """
    if not user or not user.is_authenticated:
        return []
    
    if user.role == 'super_admin':
        # Return all permissions for super admin
        all_permissions = []
        for role_perms in ROLE_PERMISSIONS.values():
            all_permissions.extend(role_perms)
        return list(set(all_permissions))
    
    return ROLE_PERMISSIONS.get(user.role, [])