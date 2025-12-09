import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator


class Department(models.Model):
    """Department/Business Unit model"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts_department'
        ordering = ['name']

    def __str__(self):
        return self.name


class ContractType(models.Model):
    """Contract Type classification"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts_contract_type'
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tags for contract categorization"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    color = models.CharField(max_length=7, default='#6c757d')  # Bootstrap secondary color
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts_tag'
        ordering = ['name']

    def __str__(self):
        return self.name


class Contract(models.Model):
    """Main Contract model"""
    
    # Status choices
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Pending'
        ACTIVE = 'ACTIVE', 'Active'
        EXPIRED = 'EXPIRED', 'Expired'
        TERMINATED = 'TERMINATED', 'Terminated'
        ARCHIVED = 'ARCHIVED', 'Archived'

    # Assignment status choices
    class AssignmentStatus(models.TextChoices):
        NOT_ASSIGNED = 'NOT_ASSIGNED', 'Not Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'

    # Category choices (can be extended)
    class Category(models.TextChoices):
        SALES = 'SALES', 'Sales'
        PROCUREMENT = 'PROCUREMENT', 'Procurement'
        HR = 'HR', 'Human Resources'
        LEGAL = 'LEGAL', 'Legal'
        FINANCE = 'FINANCE', 'Finance'
        PARTNERSHIP = 'PARTNERSHIP', 'Partnership'
        NDA = 'NDA', 'Non-Disclosure Agreement'
        SERVICE = 'SERVICE', 'Service Agreement'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract_number = models.CharField(max_length=50, blank=True, default='', db_index=True)
    title = models.CharField(max_length=500, db_index=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OTHER
    )
    sub_category = models.CharField(max_length=100, blank=True, default='')
    
    org_entity = models.CharField(max_length=255, blank=True, default='')
    region_country = models.CharField(max_length=100, blank=True, default='')
    
    bu_team = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts'
    )
    
    customer_or_vendor_name = models.CharField(max_length=500, db_index=True)
    customer_or_vendor_address = models.TextField(blank=True, default='')
    
    contract_type = models.ForeignKey(
        ContractType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts'
    )
    
    value_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField(max_length=8, blank=True, default='INR')
    
    opportunity_id = models.CharField(max_length=100, blank=True, default='')
    
    effective_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    
    auto_renewal = models.BooleanField(default=False)
    renewal_notice_date = models.DateField(null=True, blank=True)
    
    assignment_status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.NOT_ASSIGNED
    )
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_contracts'
    )
    
    is_confidential = models.BooleanField(default=False)
    
    # Flexible metadata storage
    extra_metadata = models.JSONField(default=dict, blank=True)
    
    # Tags (many-to-many)
    tags = models.ManyToManyField(Tag, through='ContractTag', related_name='contracts')
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contracts'
    )

    class Meta:
        db_table = 'contracts_contract'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['end_date', 'status']),
        ]

    def __str__(self):
        return f"{self.contract_number or 'No Number'} - {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate contract number if not set
        if not self.contract_number:
            super().save(*args, **kwargs)
            self.contract_number = f"CNT-{timezone.now().strftime('%Y%m')}-{str(self.id)[:8].upper()}"
            super().save(update_fields=['contract_number'])
        else:
            super().save(*args, **kwargs)

    @property
    def is_expiring_soon(self):
        """Check if contract expires within 30 days"""
        if self.end_date and self.status == self.Status.ACTIVE:
            days_until_expiry = (self.end_date - timezone.now().date()).days
            return 0 < days_until_expiry <= 30
        return False

    @property
    def is_expired(self):
        """Check if contract is past end date"""
        if self.end_date:
            return self.end_date < timezone.now().date()
        return False

    @property
    def primary_file(self):
        """Get the primary contract file"""
        return self.files.filter(is_primary=True).first()


class ContractTag(models.Model):
    """Through model for Contract-Tag relationship"""
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contracts_contract_tag'
        unique_together = ['contract', 'tag']


class ContractFile(models.Model):
    """Files attached to contracts"""
    
    def contract_file_path(instance, filename):
        """Generate upload path for contract files"""
        return f'contracts/{instance.contract.id}/files/{filename}'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(
        upload_to=contract_file_path,
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'xlsx', 'xls', 'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png']
        )]
    )
    original_filename = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField(default=0)  # Size in bytes
    mime_type = models.CharField(max_length=100, blank=True, default='')
    is_primary = models.BooleanField(default=False)
    description = models.TextField(blank=True, default='')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contracts_contract_file'
        ordering = ['-is_primary', '-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.contract.title})"

    def save(self, *args, **kwargs):
        # Ensure only one primary file per contract
        if self.is_primary:
            ContractFile.objects.filter(
                contract=self.contract, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ContractVersion(models.Model):
    """Version tracking for contracts"""
    
    def version_file_path(instance, filename):
        return f'contracts/{instance.contract.id}/versions/{filename}'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    label = models.CharField(max_length=255)
    file = models.FileField(upload_to=version_file_path, blank=True, null=True)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contracts_contract_version'
        ordering = ['-version_number']
        unique_together = ['contract', 'version_number']

    def __str__(self):
        return f"v{self.version_number} - {self.label}"


class ContractShare(models.Model):
    """Sharing permissions for contracts"""
    
    class AccessLevel(models.TextChoices):
        VIEW = 'VIEW', 'View Only'
        EDIT = 'EDIT', 'Edit'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='shares'
    )
    shared_with_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shared_contracts'
    )
    shared_with_department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shared_contracts'
    )
    access_level = models.CharField(
        max_length=10,
        choices=AccessLevel.choices,
        default=AccessLevel.VIEW
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='shares_created'
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contracts_contract_share'
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(shared_with_user__isnull=False, shared_with_department__isnull=True) |
                    models.Q(shared_with_user__isnull=True, shared_with_department__isnull=False)
                ),
                name='share_user_or_department'
            )
        ]

    def __str__(self):
        target = self.shared_with_user or self.shared_with_department
        return f"{self.contract.title} shared with {target}"


class AdditionalApproval(models.Model):
    """Additional approval requests for contracts"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='approvals_requested'
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='approvals_to_review'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_comment = models.TextField(blank=True, default='')
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'contracts_additional_approval'
        ordering = ['-created_at']

    def __str__(self):
        return f"Approval for {self.contract.title} - {self.status}"


class Clause(models.Model):
    """Contract clauses"""
    
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='clauses'
    )
    label = models.CharField(max_length=255)
    text = models.TextField()
    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW
    )
    is_from_playbook = models.BooleanField(default=False)
    playbook_entry = models.ForeignKey(
        'ClausePlaybookEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_in_clauses'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts_clause'
        ordering = ['label']

    def __str__(self):
        return f"{self.label} ({self.contract.title})"


class ClausePlaybookEntry(models.Model):
    """Pre-approved clause templates"""
    
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'

    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, default='')
    recommended_text = models.TextField()
    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW
    )
    guidance_notes = models.TextField(blank=True, default='')
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts_clause_playbook_entry'
        ordering = ['category', 'label']

    def __str__(self):
        return f"{self.label}"


class Deviation(models.Model):
    """Deviations from standard clauses"""
    
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='deviations'
    )
    clause = models.ForeignKey(
        Clause,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deviations'
    )
    description = models.TextField()
    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW
    )
    justification = models.TextField(blank=True, default='')
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_deviations'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_deviations'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contracts_deviation'
        ordering = ['-created_at']

    def __str__(self):
        return f"Deviation: {self.description[:50]}..."


class RiskItem(models.Model):
    """Risk items identified in contracts"""
    
    class Severity(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='risks'
    )
    description = models.TextField()
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.LOW
    )
    mitigation = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=[
            ('OPEN', 'Open'),
            ('MITIGATED', 'Mitigated'),
            ('ACCEPTED', 'Accepted'),
            ('CLOSED', 'Closed'),
        ],
        default='OPEN'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts_risk_item'
        ordering = ['-severity', '-created_at']

    def __str__(self):
        return f"Risk ({self.severity}): {self.description[:50]}..."


class SignatureRecord(models.Model):
    """Signature tracking for contracts"""
    
    class Party(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        VENDOR = 'VENDOR', 'Vendor'
        INTERNAL = 'INTERNAL', 'Internal'

    class SignType(models.TextChoices):
        AADHAAR = 'AADHAAR', 'Aadhaar eSign'
        WET = 'WET', 'Wet Signature'
        ESIGN = 'ESIGN', 'Electronic Signature'
        DSC = 'DSC', 'Digital Signature Certificate'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    party = models.CharField(
        max_length=20,
        choices=Party.choices
    )
    signatory_name = models.CharField(max_length=255)
    signatory_email = models.EmailField()
    signatory_phone = models.CharField(max_length=20, blank=True, default='')
    signatory_designation = models.CharField(max_length=255, blank=True, default='')
    sign_type = models.CharField(
        max_length=20,
        choices=SignType.choices,
        default=SignType.ESIGN
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    signature_reference = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contracts_signature_record'
        ordering = ['party', 'created_at']

    def __str__(self):
        status = "Signed" if self.signed_at else "Pending"
        return f"{self.signatory_name} ({self.party}) - {status}"


class AuditLog(models.Model):
    """Audit trail for contract actions"""
    
    class Action(models.TextChoices):
        CREATE_CONTRACT = 'CREATE_CONTRACT', 'Contract Created'
        UPDATE_CONTRACT = 'UPDATE_CONTRACT', 'Contract Updated'
        DELETE_CONTRACT = 'DELETE_CONTRACT', 'Contract Deleted'
        CHANGE_STATUS = 'CHANGE_STATUS', 'Status Changed'
        ADD_FILE = 'ADD_FILE', 'File Added'
        REMOVE_FILE = 'REMOVE_FILE', 'File Removed'
        ADD_VERSION = 'ADD_VERSION', 'Version Added'
        CREATE_APPROVAL = 'CREATE_APPROVAL', 'Approval Requested'
        APPROVE = 'APPROVE', 'Approved'
        REJECT = 'REJECT', 'Rejected'
        CANCEL_APPROVAL = 'CANCEL_APPROVAL', 'Approval Cancelled'
        SHARE = 'SHARE', 'Contract Shared'
        UNSHARE = 'UNSHARE', 'Share Removed'
        ADD_CLAUSE = 'ADD_CLAUSE', 'Clause Added'
        UPDATE_CLAUSE = 'UPDATE_CLAUSE', 'Clause Updated'
        ADD_DEVIATION = 'ADD_DEVIATION', 'Deviation Added'
        ADD_RISK = 'ADD_RISK', 'Risk Added'
        ADD_SIGNATURE = 'ADD_SIGNATURE', 'Signature Added'
        SIGN = 'SIGN', 'Document Signed'
        VIEW = 'VIEW', 'Contract Viewed'
        DOWNLOAD = 'DOWNLOAD', 'File Downloaded'

    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'contracts_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract', 'action', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor} at {self.created_at}"

