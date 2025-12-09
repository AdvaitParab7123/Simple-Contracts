"""
Django Admin configuration for Contract Management module.
"""

from django.contrib import admin
from .models import (
    Department, ContractType, Tag, Contract, ContractFile,
    ContractVersion, ContractTag, ContractShare, AdditionalApproval,
    Clause, ClausePlaybookEntry, Deviation, RiskItem,
    SignatureRecord, AuditLog
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(ContractType)
class ContractTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'active', 'created_at']
    list_filter = ['active']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'active', 'created_at']
    list_filter = ['active']
    search_fields = ['name', 'description']
    ordering = ['name']


class ContractFileInline(admin.TabularInline):
    model = ContractFile
    extra = 0
    fields = ['file', 'original_filename', 'is_primary', 'uploaded_by', 'uploaded_at']
    readonly_fields = ['uploaded_at']


class ContractVersionInline(admin.TabularInline):
    model = ContractVersion
    extra = 0
    fields = ['version_number', 'label', 'file', 'created_by', 'created_at']
    readonly_fields = ['created_at']


class AdditionalApprovalInline(admin.TabularInline):
    model = AdditionalApproval
    extra = 0
    fields = ['approver', 'status', 'reason', 'created_at', 'decided_at']
    readonly_fields = ['created_at']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        'contract_number', 'title', 'status', 'category',
        'customer_or_vendor_name', 'owner', 'created_at'
    ]
    list_filter = ['status', 'category', 'bu_team', 'contract_type', 'is_confidential']
    search_fields = ['contract_number', 'title', 'customer_or_vendor_name']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    readonly_fields = ['id', 'contract_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'contract_number', 'title', 'status', 'category', 'sub_category')
        }),
        ('Organization', {
            'fields': ('org_entity', 'region_country', 'bu_team')
        }),
        ('Party Information', {
            'fields': ('customer_or_vendor_name', 'customer_or_vendor_address', 'contract_type')
        }),
        ('Value', {
            'fields': ('value_amount', 'currency', 'opportunity_id')
        }),
        ('Dates', {
            'fields': ('effective_date', 'end_date', 'auto_renewal', 'renewal_notice_date')
        }),
        ('Assignment', {
            'fields': ('assignment_status', 'owner', 'is_confidential')
        }),
        ('Metadata', {
            'fields': ('extra_metadata', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ContractFileInline, ContractVersionInline, AdditionalApprovalInline]


@admin.register(ContractFile)
class ContractFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'contract', 'is_primary', 'uploaded_by', 'uploaded_at']
    list_filter = ['is_primary']
    search_fields = ['original_filename', 'contract__title']
    date_hierarchy = 'uploaded_at'


@admin.register(ContractVersion)
class ContractVersionAdmin(admin.ModelAdmin):
    list_display = ['contract', 'version_number', 'label', 'created_by', 'created_at']
    search_fields = ['contract__title', 'label']
    date_hierarchy = 'created_at'


@admin.register(ContractShare)
class ContractShareAdmin(admin.ModelAdmin):
    list_display = ['contract', 'shared_with_user', 'shared_with_department', 'access_level', 'shared_at']
    list_filter = ['access_level']
    search_fields = ['contract__title']


@admin.register(AdditionalApproval)
class AdditionalApprovalAdmin(admin.ModelAdmin):
    list_display = ['contract', 'requested_by', 'approver', 'status', 'created_at', 'decided_at']
    list_filter = ['status']
    search_fields = ['contract__title', 'requested_by__username', 'approver__username']
    date_hierarchy = 'created_at'


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = ['label', 'contract', 'risk_level', 'is_from_playbook', 'created_at']
    list_filter = ['risk_level', 'is_from_playbook']
    search_fields = ['label', 'text', 'contract__title']


@admin.register(ClausePlaybookEntry)
class ClausePlaybookEntryAdmin(admin.ModelAdmin):
    list_display = ['label', 'category', 'risk_level', 'active', 'created_at']
    list_filter = ['risk_level', 'active', 'category']
    search_fields = ['label', 'recommended_text']


@admin.register(Deviation)
class DeviationAdmin(admin.ModelAdmin):
    list_display = ['contract', 'risk_level', 'approved', 'created_by', 'created_at']
    list_filter = ['risk_level', 'approved']
    search_fields = ['description', 'contract__title']


@admin.register(RiskItem)
class RiskItemAdmin(admin.ModelAdmin):
    list_display = ['contract', 'severity', 'status', 'created_by', 'created_at']
    list_filter = ['severity', 'status']
    search_fields = ['description', 'contract__title']


@admin.register(SignatureRecord)
class SignatureRecordAdmin(admin.ModelAdmin):
    list_display = ['contract', 'party', 'signatory_name', 'sign_type', 'signed_at']
    list_filter = ['party', 'sign_type']
    search_fields = ['signatory_name', 'signatory_email', 'contract__title']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['contract', 'action', 'actor', 'created_at']
    list_filter = ['action']
    search_fields = ['contract__title', 'actor__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['contract', 'action', 'actor', 'metadata', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

