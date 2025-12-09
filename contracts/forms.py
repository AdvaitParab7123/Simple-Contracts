"""
Forms for Contract Management module.
Includes forms for contract creation wizard, editing, and admin functions.
"""

from django import forms
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model
from .models import (
    Contract, ContractFile, ContractVersion, ContractShare,
    AdditionalApproval, Clause, ClausePlaybookEntry, Deviation,
    RiskItem, SignatureRecord, Department, ContractType, Tag
)

User = get_user_model()


# ============================================================================
# Contract Wizard Forms (Multi-step)
# ============================================================================

class ContractMethodForm(forms.Form):
    """Step 1: Choose contract creation method"""
    
    METHOD_CHOICES = [
        ('upload', 'Upload a document'),
        ('template', 'Draft from pre-existing template'),
    ]
    
    method = forms.ChoiceField(
        choices=METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='upload'
    )


class ContractUploadForm(forms.Form):
    """Step 1b: Upload document"""
    
    file = forms.FileField(
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'xlsx', 'xls']
        )],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.xlsx,.xls'
        }),
        help_text='Supported formats: PDF, DOC, DOCX, XLSX, XLS. Max size: 20MB.'
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (20MB limit)
            if file.size > 20 * 1024 * 1024:
                raise forms.ValidationError('File size must be under 20MB.')
        return file


class ContractNameForm(forms.Form):
    """Step 2: Name your contract"""
    
    SUGGESTIONS = [
        'Service Agreement - [Company Name]',
        'NDA - [Party Name] - [Date]',
        'Master Services Agreement',
        'Software License Agreement',
        'Vendor Agreement - [Vendor Name]',
        'Employment Contract - [Employee Name]',
    ]
    
    title = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter contract name...',
            'autofocus': True
        }),
        help_text='Give your contract a clear, descriptive name.'
    )


class ContractBasicInfoForm(forms.Form):
    """Step 3: Basic contract information"""
    
    org_entity = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Organization Entity'
    )
    
    region_country = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Region / Country'
    )
    
    bu_team = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='BU / Team',
        empty_label='-- Select Department --'
    )
    
    category = forms.ChoiceField(
        choices=Contract.Category.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Category'
    )
    
    sub_category = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Sub-Category'
    )


class ContractPartyInfoForm(forms.Form):
    """Step 4: Customer/Vendor information"""
    
    customer_or_vendor_name = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter customer or vendor name'
        }),
        label='Customer / Vendor Name'
    )
    
    customer_or_vendor_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter address...'
        }),
        label='Address'
    )
    
    contract_type = forms.ModelChoiceField(
        queryset=ContractType.objects.filter(active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Contract Type',
        empty_label='-- Select Type --'
    )


class ContractDatesForm(forms.Form):
    """Step 5: Contract dates and renewal"""
    
    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Effective Date'
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='End Date'
    )
    
    auto_renewal = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Auto Renewal'
    )
    
    renewal_notice_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Renewal Notice Date',
        help_text='Date by which renewal notice must be given'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        effective_date = cleaned_data.get('effective_date')
        end_date = cleaned_data.get('end_date')
        renewal_notice_date = cleaned_data.get('renewal_notice_date')
        
        if effective_date and end_date and end_date < effective_date:
            raise forms.ValidationError('End date must be after effective date.')
        
        if renewal_notice_date and end_date and renewal_notice_date > end_date:
            raise forms.ValidationError('Renewal notice date must be before end date.')
        
        return cleaned_data


class ContractValueForm(forms.Form):
    """Step 6: Contract value and additional info"""
    
    CURRENCY_CHOICES = [
        ('INR', 'INR - Indian Rupee'),
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('AED', 'AED - UAE Dirham'),
        ('SGD', 'SGD - Singapore Dollar'),
    ]
    
    value_amount = forms.DecimalField(
        required=False,
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        label='Contract Value'
    )
    
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        initial='INR',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Currency'
    )
    
    opportunity_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'CRM Opportunity ID'
        }),
        label='Opportunity ID'
    )


class ContractOwnerTagsForm(forms.Form):
    """Step 7: Owner and tags"""
    
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Contract Owner',
        empty_label='-- Select Owner --'
    )
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.filter(active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Tags'
    )
    
    is_confidential = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Mark as Confidential',
        help_text='Confidential contracts are only visible to owner and shared users'
    )


# ============================================================================
# Contract Edit Form (Full form for editing)
# ============================================================================

class ContractForm(forms.ModelForm):
    """Full contract form for editing"""
    
    class Meta:
        model = Contract
        fields = [
            'title', 'contract_number', 'status', 'category', 'sub_category',
            'org_entity', 'region_country', 'bu_team', 'customer_or_vendor_name',
            'customer_or_vendor_address', 'contract_type', 'value_amount', 'currency',
            'opportunity_id', 'effective_date', 'end_date', 'auto_renewal',
            'renewal_notice_date', 'assignment_status', 'owner', 'is_confidential'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'sub_category': forms.TextInput(attrs={'class': 'form-control'}),
            'org_entity': forms.TextInput(attrs={'class': 'form-control'}),
            'region_country': forms.TextInput(attrs={'class': 'form-control'}),
            'bu_team': forms.Select(attrs={'class': 'form-select'}),
            'customer_or_vendor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_or_vendor_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contract_type': forms.Select(attrs={'class': 'form-select'}),
            'value_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 8}),
            'opportunity_id': forms.TextInput(attrs={'class': 'form-control'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'auto_renewal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'renewal_notice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'assignment_status': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].queryset = User.objects.filter(is_active=True)


# ============================================================================
# File Upload Forms
# ============================================================================

class ContractFileUploadForm(forms.ModelForm):
    """Form for uploading contract files"""
    
    class Meta:
        model = ContractFile
        fields = ['file', 'is_primary', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xlsx,.xls,.ppt,.pptx,.txt,.jpg,.jpeg,.png'
            }),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and file.size > 20 * 1024 * 1024:
            raise forms.ValidationError('File size must be under 20MB.')
        return file


class ContractVersionForm(forms.ModelForm):
    """Form for adding contract versions"""
    
    class Meta:
        model = ContractVersion
        fields = ['label', 'file', 'notes']
        widgets = {
            'label': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., v1.0 - Initial Draft'
            }),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ============================================================================
# Approval Forms
# ============================================================================

class AdditionalApprovalRequestForm(forms.ModelForm):
    """Form for requesting additional approval"""
    
    class Meta:
        model = AdditionalApproval
        fields = ['approver', 'reason', 'due_date']
        widgets = {
            'approver': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain why this approval is needed...'
            }),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['approver'].queryset = User.objects.filter(is_active=True)
        self.fields['approver'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username}"


class ApprovalDecisionForm(forms.Form):
    """Form for approving/rejecting approval requests"""
    
    DECISION_CHOICES = [
        ('APPROVED', 'Approve'),
        ('REJECTED', 'Reject'),
    ]
    
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add a comment (optional for approval, required for rejection)...'
        }),
        label='Decision Comment'
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comment = cleaned_data.get('comment')
        
        if decision == 'REJECTED' and not comment:
            raise forms.ValidationError('Please provide a reason for rejection.')
        
        return cleaned_data


# ============================================================================
# Sharing Forms
# ============================================================================

class ContractShareForm(forms.ModelForm):
    """Form for sharing contracts"""
    
    share_type = forms.ChoiceField(
        choices=[('user', 'Specific User'), ('department', 'Department')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='user'
    )
    
    class Meta:
        model = ContractShare
        fields = ['shared_with_user', 'shared_with_department', 'access_level']
        widgets = {
            'shared_with_user': forms.Select(attrs={'class': 'form-select'}),
            'shared_with_department': forms.Select(attrs={'class': 'form-select'}),
            'access_level': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shared_with_user'].queryset = User.objects.filter(is_active=True)
        self.fields['shared_with_user'].required = False
        self.fields['shared_with_department'].required = False

    def clean(self):
        cleaned_data = super().clean()
        share_type = cleaned_data.get('share_type')
        user = cleaned_data.get('shared_with_user')
        dept = cleaned_data.get('shared_with_department')
        
        if share_type == 'user' and not user:
            raise forms.ValidationError('Please select a user to share with.')
        elif share_type == 'department' and not dept:
            raise forms.ValidationError('Please select a department to share with.')
        
        # Clear the other field based on share type
        if share_type == 'user':
            cleaned_data['shared_with_department'] = None
        else:
            cleaned_data['shared_with_user'] = None
        
        return cleaned_data


# ============================================================================
# Clause and Risk Forms
# ============================================================================

class ClauseForm(forms.ModelForm):
    """Form for adding/editing clauses"""
    
    use_playbook = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Use Playbook Entry'
    )
    
    playbook_entry = forms.ModelChoiceField(
        queryset=ClausePlaybookEntry.objects.filter(active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select from Playbook'
    )
    
    class Meta:
        model = Clause
        fields = ['label', 'text', 'risk_level']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
        }


class DeviationForm(forms.ModelForm):
    """Form for adding deviations"""
    
    class Meta:
        model = Deviation
        fields = ['clause', 'description', 'risk_level', 'justification']
        widgets = {
            'clause': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'justification': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, contract=None, **kwargs):
        super().__init__(*args, **kwargs)
        if contract:
            self.fields['clause'].queryset = Clause.objects.filter(contract=contract)
        self.fields['clause'].required = False


class RiskItemForm(forms.ModelForm):
    """Form for adding risk items"""
    
    class Meta:
        model = RiskItem
        fields = ['description', 'severity', 'mitigation']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'mitigation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe mitigation strategy...'
            }),
        }


# ============================================================================
# Signature Forms
# ============================================================================

class SignatureRecordForm(forms.ModelForm):
    """Form for adding signature records"""
    
    class Meta:
        model = SignatureRecord
        fields = [
            'party', 'signatory_name', 'signatory_email', 'signatory_phone',
            'signatory_designation', 'sign_type'
        ]
        widgets = {
            'party': forms.Select(attrs={'class': 'form-select'}),
            'signatory_name': forms.TextInput(attrs={'class': 'form-control'}),
            'signatory_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'signatory_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'signatory_designation': forms.TextInput(attrs={'class': 'form-control'}),
            'sign_type': forms.Select(attrs={'class': 'form-select'}),
        }


# ============================================================================
# Admin Forms (Contract Types, Tags, Playbook)
# ============================================================================

class ContractTypeForm(forms.ModelForm):
    """Form for managing contract types"""
    
    class Meta:
        model = ContractType
        fields = ['name', 'description', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TagForm(forms.ModelForm):
    """Form for managing tags"""
    
    class Meta:
        model = Tag
        fields = ['name', 'description', 'color', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ClausePlaybookEntryForm(forms.ModelForm):
    """Form for managing clause playbook entries"""
    
    class Meta:
        model = ClausePlaybookEntry
        fields = ['label', 'category', 'recommended_text', 'risk_level', 'guidance_notes', 'active']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'recommended_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'guidance_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DepartmentForm(forms.ModelForm):
    """Form for managing departments"""
    
    class Meta:
        model = Department
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


# ============================================================================
# Filter Forms
# ============================================================================

class ContractFilterForm(forms.Form):
    """Form for filtering contract list"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search contracts...'
        })
    )
    
    status = forms.MultipleChoiceField(
        choices=Contract.Status.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    category = forms.MultipleChoiceField(
        choices=Contract.Category.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    bu_team = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='All Departments'
    )
    
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='All Owners'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Created From'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Created To'
    )
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.filter(active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )


class ApprovalFilterForm(forms.Form):
    """Form for filtering approval list"""
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(AdditionalApproval.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    assigned_to_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Assigned to me'
    )
    
    requested_by_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Requested by me'
    )


# ============================================================================
# Status Change Form
# ============================================================================

class StatusChangeForm(forms.Form):
    """Form for changing contract status"""
    
    new_status = forms.ChoiceField(
        choices=Contract.Status.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Reason for status change (optional)...'
        })
    )

