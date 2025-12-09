"""
Views for Contract Management module.
Implements dashboard, contract CRUD, approvals, and admin views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, FileResponse
from django.views import View
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin

# Disable login requirement for demo - remove this mixin override in production
class LoginRequiredMixin:
    """Disabled for demo purposes"""
    pass
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator

from .models import (
    Contract, ContractFile, ContractVersion, ContractShare,
    AdditionalApproval, Clause, ClausePlaybookEntry, Deviation,
    RiskItem, SignatureRecord, AuditLog, Department, ContractType, Tag
)
from .forms import (
    ContractMethodForm, ContractUploadForm, ContractNameForm,
    ContractBasicInfoForm, ContractPartyInfoForm, ContractDatesForm,
    ContractValueForm, ContractOwnerTagsForm, ContractForm,
    ContractFileUploadForm, ContractVersionForm,
    AdditionalApprovalRequestForm, ApprovalDecisionForm,
    ContractShareForm, ClauseForm, DeviationForm, RiskItemForm,
    SignatureRecordForm, ContractTypeForm, TagForm,
    ClausePlaybookEntryForm, DepartmentForm, ContractFilterForm,
    ApprovalFilterForm, StatusChangeForm
)
from .services import (
    DashboardService, ContractQueryService, ApprovalService,
    ContractOperationsService, AuditLogService
)
from .permissions import (
    can_view_contract, can_edit_contract, can_delete_contract,
    can_manage_approvals, can_admin_contracts, can_create_contract,
    can_upload_files, can_add_version, can_change_status,
    can_approve_request, can_share_contract, get_user_permissions_context,
    is_legal_admin, admin_required, legal_user_required
)


# ============================================================================
# Dashboard Views
# ============================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view showing contract metrics and pending items"""
    template_name = 'contracts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        dashboard_service = DashboardService(self.request.user)
        metrics = dashboard_service.get_all_metrics()
        
        context.update({
            'pending_action': metrics['pending_action'],
            'pending_approvals': metrics['pending_approvals'],
            'expiring_contracts': metrics['expiring_contracts'],
            'notified_contracts': metrics['notified_contracts'],
            'contract_stats': metrics['contract_stats'],
            'recent_activity': metrics['recent_activity'],
            'quick_stats': metrics['quick_stats'],
            'can_create': can_create_contract(self.request.user),
            **get_user_permissions_context(self.request.user),
        })
        
        return context


# ============================================================================
# Contract List Views
# ============================================================================

class ContractListView(LoginRequiredMixin, ListView):
    """List view for contracts with tabs and filters"""
    template_name = 'contracts/contract_list.html'
    context_object_name = 'contracts'
    paginate_by = 20
    
    def get_queryset(self):
        tab = self.request.GET.get('tab', 'repository')
        
        # Build filters from GET params
        filters = {}
        filter_form = ContractFilterForm(self.request.GET)
        if filter_form.is_valid():
            filters = {k: v for k, v in filter_form.cleaned_data.items() if v}
        
        query_service = ContractQueryService(self.request.user)
        queryset = query_service.get_contracts_for_tab(tab, filters)
        
        # Sorting
        sort = self.request.GET.get('sort', '-created_at')
        if sort:
            queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        tab = self.request.GET.get('tab', 'repository')
        query_service = ContractQueryService(self.request.user)
        
        # Get counts for each tab
        context.update({
            'current_tab': tab,
            'draft_count': query_service.get_contracts_for_tab('draft').count(),
            'pending_count': query_service.get_contracts_for_tab('pending').count(),
            'repository_count': query_service.get_contracts_for_tab('repository').count(),
            'filter_form': ContractFilterForm(self.request.GET),
            'departments': Department.objects.all(),
            'contract_types': ContractType.objects.filter(active=True),
            'tags': Tag.objects.filter(active=True),
            'can_create': can_create_contract(self.request.user),
            **get_user_permissions_context(self.request.user),
        })
        
        return context


# ============================================================================
# Contract Detail View
# ============================================================================

class ContractDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a single contract"""
    model = Contract
    template_name = 'contracts/contract_detail.html'
    context_object_name = 'contract'
    
    def get_object(self, queryset=None):
        contract = get_object_or_404(
            Contract.objects.select_related(
                'owner', 'bu_team', 'contract_type', 'created_by'
            ).prefetch_related(
                'tags', 'files', 'versions', 'approvals__approver',
                'approvals__requested_by', 'clauses', 'deviations',
                'risks', 'signatures', 'shares__shared_with_user',
                'shares__shared_with_department'
            ),
            pk=self.kwargs['pk']
        )
        
        if not can_view_contract(self.request.user, contract):
            messages.error(self.request, "You don't have permission to view this contract.")
            return None
        
        # Log view action
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.VIEW,
            actor=self.request.user,
            request=self.request
        )
        
        return contract
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return redirect('contracts:list')
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.object
        
        # Get primary file for viewer
        primary_file = contract.files.filter(is_primary=True).first()
        
        # Get audit logs for this contract
        audit_logs = contract.audit_logs.select_related('actor').order_by('-created_at')[:20]
        
        # Forms for modals
        context.update({
            'primary_file': primary_file,
            'audit_logs': audit_logs,
            'file_upload_form': ContractFileUploadForm(),
            'version_form': ContractVersionForm(),
            'approval_form': AdditionalApprovalRequestForm(),
            'share_form': ContractShareForm(),
            'clause_form': ClauseForm(),
            'deviation_form': DeviationForm(contract=contract),
            'risk_form': RiskItemForm(),
            'signature_form': SignatureRecordForm(),
            'status_form': StatusChangeForm(initial={'new_status': contract.status}),
            'playbook_entries': ClausePlaybookEntry.objects.filter(active=True),
            **get_user_permissions_context(self.request.user, contract),
        })
        
        return context


# ============================================================================
# Contract Create Wizard
# ============================================================================

class ContractCreateWizardView(LoginRequiredMixin, View):
    """Multi-step contract creation wizard"""
    
    STEPS = ['method', 'upload', 'name', 'basic', 'party', 'dates', 'value', 'owner_tags']
    STEP_FORMS = {
        'method': ContractMethodForm,
        'upload': ContractUploadForm,
        'name': ContractNameForm,
        'basic': ContractBasicInfoForm,
        'party': ContractPartyInfoForm,
        'dates': ContractDatesForm,
        'value': ContractValueForm,
        'owner_tags': ContractOwnerTagsForm,
    }
    
    def dispatch(self, request, *args, **kwargs):
        if not can_create_contract(request.user):
            messages.error(request, "You don't have permission to create contracts.")
            return redirect('contracts:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        step = request.GET.get('step', 'method')
        
        # Get wizard data from session
        wizard_data = request.session.get('contract_wizard', {})
        
        # If starting fresh, clear session
        if step == 'method' and 'reset' in request.GET:
            request.session['contract_wizard'] = {}
            wizard_data = {}
        
        form_class = self.STEP_FORMS.get(step, ContractMethodForm)
        
        # Pre-populate form with session data
        initial_data = wizard_data.get(step, {})
        form = form_class(initial=initial_data)
        
        context = {
            'form': form,
            'step': step,
            'steps': self.STEPS,
            'current_step_index': self.STEPS.index(step) if step in self.STEPS else 0,
            'wizard_data': wizard_data,
            'name_suggestions': ContractNameForm.SUGGESTIONS,
        }
        
        return render(request, 'contracts/contract_form.html', context)
    
    def post(self, request):
        step = request.POST.get('current_step', 'method')
        action = request.POST.get('action', 'next')
        
        wizard_data = request.session.get('contract_wizard', {})
        
        # Handle back action
        if action == 'back':
            current_index = self.STEPS.index(step) if step in self.STEPS else 0
            if current_index > 0:
                prev_step = self.STEPS[current_index - 1]
                # Skip upload step if method is template
                if prev_step == 'upload' and wizard_data.get('method', {}).get('method') == 'template':
                    prev_step = 'method'
                return redirect(f"{reverse('contracts:create')}?step={prev_step}")
            return redirect(f"{reverse('contracts:create')}?step=method")
        
        # Handle save as draft
        if action == 'save_draft':
            return self._save_contract(request, wizard_data, as_draft=True)
        
        # Special handling for value step - don't use form validation
        if step == 'value':
            # Store data directly
            value_amount = request.POST.get('value_amount', '')
            wizard_data[step] = {
                'value_amount': value_amount if value_amount else None,
                'currency': request.POST.get('currency', 'INR'),
                'opportunity_id': request.POST.get('opportunity_id', ''),
            }
            request.session['contract_wizard'] = wizard_data
            request.session.modified = True
            
            # Move to next step
            next_step = 'owner_tags'
            return redirect(f"{reverse('contracts:create')}?step={next_step}")
        
        # Validate current step
        form_class = self.STEP_FORMS.get(step, ContractMethodForm)
        form = form_class(request.POST, request.FILES)
        
        if form.is_valid():
            # Store step data in session
            wizard_data[step] = form.cleaned_data
            
            # Handle file upload specially
            if step == 'upload' and 'file' in request.FILES:
                # Store file temporarily (in a real app, you'd use temp storage)
                wizard_data['uploaded_file'] = {
                    'name': request.FILES['file'].name,
                    'size': request.FILES['file'].size,
                }
                # Store file in session or temp storage for later
                request.session['contract_wizard_file'] = request.FILES['file'].read()
                request.session['contract_wizard_file_name'] = request.FILES['file'].name
            
            request.session['contract_wizard'] = wizard_data
            request.session.modified = True
            
            # Determine next step
            current_index = self.STEPS.index(step) if step in self.STEPS else 0
            
            # Special handling for method step
            if step == 'method':
                method = form.cleaned_data.get('method')
                if method == 'template':
                    # Skip upload step for template method
                    next_step = 'name'
                else:
                    next_step = 'upload'
            elif current_index < len(self.STEPS) - 1:
                next_step = self.STEPS[current_index + 1]
                # Skip upload if already done
                if next_step == 'upload' and wizard_data.get('method', {}).get('method') == 'template':
                    next_step = 'name'
            else:
                # Final step - create the contract
                return self._save_contract(request, wizard_data, as_draft=False)
            
            return redirect(f"{reverse('contracts:create')}?step={next_step}")
        
        # Form validation failed
        context = {
            'form': form,
            'step': step,
            'steps': self.STEPS,
            'current_step_index': self.STEPS.index(step) if step in self.STEPS else 0,
            'wizard_data': wizard_data,
            'name_suggestions': ContractNameForm.SUGGESTIONS,
        }
        
        return render(request, 'contracts/contract_form.html', context)
    
    def _parse_decimal(self, value):
        """Safely parse a decimal value"""
        if value is None or value == '':
            return None
        try:
            from decimal import Decimal
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None
    
    def _save_contract(self, request, wizard_data, as_draft=True):
        """Create the contract from wizard data"""
        
        # Build contract data
        contract_data = {
            'title': wizard_data.get('name', {}).get('title', 'Untitled Contract'),
            'status': Contract.Status.DRAFT if as_draft else Contract.Status.PENDING,
            'org_entity': wizard_data.get('basic', {}).get('org_entity', ''),
            'region_country': wizard_data.get('basic', {}).get('region_country', ''),
            'bu_team': wizard_data.get('basic', {}).get('bu_team'),
            'category': wizard_data.get('basic', {}).get('category', 'OTHER'),
            'sub_category': wizard_data.get('basic', {}).get('sub_category', ''),
            'customer_or_vendor_name': wizard_data.get('party', {}).get('customer_or_vendor_name', ''),
            'customer_or_vendor_address': wizard_data.get('party', {}).get('customer_or_vendor_address', ''),
            'contract_type': wizard_data.get('party', {}).get('contract_type'),
            'effective_date': wizard_data.get('dates', {}).get('effective_date'),
            'end_date': wizard_data.get('dates', {}).get('end_date'),
            'auto_renewal': wizard_data.get('dates', {}).get('auto_renewal', False),
            'renewal_notice_date': wizard_data.get('dates', {}).get('renewal_notice_date'),
            'value_amount': self._parse_decimal(wizard_data.get('value', {}).get('value_amount')),
            'currency': wizard_data.get('value', {}).get('currency', 'INR'),
            'opportunity_id': wizard_data.get('value', {}).get('opportunity_id', ''),
            'owner': wizard_data.get('owner_tags', {}).get('owner') or request.user,
            'is_confidential': wizard_data.get('owner_tags', {}).get('is_confidential', False),
            'tags': wizard_data.get('owner_tags', {}).get('tags', []),
        }
        
        # Handle file if uploaded
        file_data = request.session.get('contract_wizard_file')
        file_name = request.session.get('contract_wizard_file_name')
        
        ops_service = ContractOperationsService(request.user)
        
        # Create a file-like object if we have file data
        uploaded_file = None
        if file_data and file_name:
            from django.core.files.uploadedfile import SimpleUploadedFile
            uploaded_file = SimpleUploadedFile(file_name, file_data)
        
        contract = ops_service.create_contract(contract_data, file=uploaded_file)
        
        # Clear wizard session data
        request.session.pop('contract_wizard', None)
        request.session.pop('contract_wizard_file', None)
        request.session.pop('contract_wizard_file_name', None)
        
        messages.success(
            request,
            f"Contract '{contract.title}' created successfully as {'draft' if as_draft else 'pending'}."
        )
        
        return redirect('contracts:detail', pk=contract.pk)


# ============================================================================
# Contract Edit View
# ============================================================================

class ContractUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing contract"""
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_edit.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_edit_contract(request.user, self.object):
            messages.error(request, "You don't have permission to edit this contract.")
            return redirect('contracts:detail', pk=self.object.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            **get_user_permissions_context(self.request.user, self.object),
        })
        return context
    
    def form_valid(self, form):
        # Use service for update to trigger audit logging
        ops_service = ContractOperationsService(self.request.user)
        ops_service.update_contract(self.object, form.cleaned_data)
        
        messages.success(self.request, "Contract updated successfully.")
        return redirect('contracts:detail', pk=self.object.pk)


# ============================================================================
# Contract File Operations
# ============================================================================

class ContractFileUploadView(LoginRequiredMixin, View):
    """Handle file uploads for a contract"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_upload_files(request.user, contract):
            messages.error(request, "You don't have permission to upload files.")
            return redirect('contracts:detail', pk=pk)
        
        form = ContractFileUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            ops_service = ContractOperationsService(request.user)
            ops_service.upload_file(
                contract,
                request.FILES['file'],
                is_primary=form.cleaned_data.get('is_primary', False),
                description=form.cleaned_data.get('description', '')
            )
            messages.success(request, "File uploaded successfully.")
        else:
            messages.error(request, "Error uploading file. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


class ContractFileDownloadView(LoginRequiredMixin, View):
    """Download a contract file"""
    
    def get(self, request, pk, file_id):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_view_contract(request.user, contract):
            return HttpResponseForbidden("You don't have permission to access this file.")
        
        contract_file = get_object_or_404(ContractFile, pk=file_id, contract=contract)
        
        # Log download
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.DOWNLOAD,
            actor=request.user,
            metadata={'filename': contract_file.original_filename},
            request=request
        )
        
        return FileResponse(
            contract_file.file,
            as_attachment=True,
            filename=contract_file.original_filename
        )


class ContractVersionCreateView(LoginRequiredMixin, View):
    """Add a new version to a contract"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_add_version(request.user, contract):
            messages.error(request, "You don't have permission to add versions.")
            return redirect('contracts:detail', pk=pk)
        
        form = ContractVersionForm(request.POST, request.FILES)
        
        if form.is_valid():
            ops_service = ContractOperationsService(request.user)
            ops_service.add_version(
                contract,
                label=form.cleaned_data['label'],
                file=request.FILES.get('file'),
                notes=form.cleaned_data.get('notes', '')
            )
            messages.success(request, "Version added successfully.")
        else:
            messages.error(request, "Error adding version. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Contract Status Change
# ============================================================================

class ContractStatusChangeView(LoginRequiredMixin, View):
    """Change contract status"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_change_status(request.user, contract):
            messages.error(request, "You don't have permission to change the status.")
            return redirect('contracts:detail', pk=pk)
        
        form = StatusChangeForm(request.POST)
        
        if form.is_valid():
            ops_service = ContractOperationsService(request.user)
            ops_service.change_status(
                contract,
                form.cleaned_data['new_status'],
                form.cleaned_data.get('reason', '')
            )
            messages.success(request, f"Status changed to {form.cleaned_data['new_status']}.")
        else:
            messages.error(request, "Error changing status.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Contract Sharing
# ============================================================================

class ContractShareCreateView(LoginRequiredMixin, View):
    """Share a contract with a user or department"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_share_contract(request.user, contract):
            messages.error(request, "You don't have permission to share this contract.")
            return redirect('contracts:detail', pk=pk)
        
        form = ContractShareForm(request.POST)
        
        if form.is_valid():
            ops_service = ContractOperationsService(request.user)
            ops_service.share_contract(
                contract,
                user=form.cleaned_data.get('shared_with_user'),
                department=form.cleaned_data.get('shared_with_department'),
                access_level=form.cleaned_data['access_level']
            )
            messages.success(request, "Contract shared successfully.")
        else:
            messages.error(request, "Error sharing contract. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Approval Views
# ============================================================================

class ApprovalListView(LoginRequiredMixin, ListView):
    """List view for additional approvals"""
    template_name = 'contracts/approvals_list.html'
    context_object_name = 'approvals'
    paginate_by = 20
    
    def get_queryset(self):
        filters = {}
        filter_form = ApprovalFilterForm(self.request.GET)
        if filter_form.is_valid():
            filters = {k: v for k, v in filter_form.cleaned_data.items() if v}
        
        approval_service = ApprovalService(self.request.user)
        return approval_service.get_approvals_for_user(filters)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ApprovalFilterForm(self.request.GET)
        context.update(get_user_permissions_context(self.request.user))
        return context


class ApprovalDetailView(LoginRequiredMixin, View):
    """Detail view for a single approval with decision capability"""
    template_name = 'contracts/approval_detail.html'
    
    def get(self, request, pk):
        approval = get_object_or_404(
            AdditionalApproval.objects.select_related(
                'contract', 'requested_by', 'approver'
            ),
            pk=pk
        )
        
        # Check access
        if not is_legal_admin(request.user):
            if approval.approver != request.user and approval.requested_by != request.user:
                messages.error(request, "You don't have permission to view this approval.")
                return redirect('contracts:approvals')
        
        form = ApprovalDecisionForm()
        
        context = {
            'approval': approval,
            'form': form,
            'can_decide': can_approve_request(request.user, approval) and approval.status == 'PENDING',
            **get_user_permissions_context(request.user, approval.contract),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        approval = get_object_or_404(AdditionalApproval, pk=pk)
        
        if not can_approve_request(request.user, approval):
            messages.error(request, "You don't have permission to decide on this approval.")
            return redirect('contracts:approvals')
        
        if approval.status != AdditionalApproval.Status.PENDING:
            messages.error(request, "This approval has already been decided.")
            return redirect('contracts:approval_detail', pk=pk)
        
        form = ApprovalDecisionForm(request.POST)
        
        if form.is_valid():
            approval_service = ApprovalService(request.user)
            approval_service.process_decision(
                approval,
                form.cleaned_data['decision'],
                form.cleaned_data.get('comment', '')
            )
            
            messages.success(
                request,
                f"Approval {form.cleaned_data['decision'].lower()} successfully."
            )
            return redirect('contracts:approvals')
        
        context = {
            'approval': approval,
            'form': form,
            'can_decide': True,
            **get_user_permissions_context(request.user, approval.contract),
        }
        
        return render(request, self.template_name, context)


class ApprovalRequestCreateView(LoginRequiredMixin, View):
    """Create a new approval request for a contract"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_manage_approvals(request.user, contract):
            messages.error(request, "You don't have permission to request approvals.")
            return redirect('contracts:detail', pk=pk)
        
        form = AdditionalApprovalRequestForm(request.POST)
        
        if form.is_valid():
            approval_service = ApprovalService(request.user)
            approval_service.create_approval_request(
                contract,
                form.cleaned_data['approver'],
                form.cleaned_data.get('reason', ''),
                form.cleaned_data.get('due_date')
            )
            messages.success(request, "Approval request created successfully.")
        else:
            messages.error(request, "Error creating approval request. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Clause Views
# ============================================================================

class ClauseCreateView(LoginRequiredMixin, View):
    """Add a clause to a contract"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_edit_contract(request.user, contract):
            messages.error(request, "You don't have permission to add clauses.")
            return redirect('contracts:detail', pk=pk)
        
        form = ClauseForm(request.POST)
        
        if form.is_valid():
            clause = Clause.objects.create(
                contract=contract,
                label=form.cleaned_data['label'],
                text=form.cleaned_data['text'],
                risk_level=form.cleaned_data['risk_level'],
                is_from_playbook=form.cleaned_data.get('use_playbook', False),
                playbook_entry=form.cleaned_data.get('playbook_entry'),
                created_by=request.user
            )
            
            AuditLogService.log(
                contract=contract,
                action=AuditLog.Action.ADD_CLAUSE,
                actor=request.user,
                metadata={'clause_id': clause.id, 'label': clause.label}
            )
            
            messages.success(request, "Clause added successfully.")
        else:
            messages.error(request, "Error adding clause. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Deviation Views
# ============================================================================

class DeviationCreateView(LoginRequiredMixin, View):
    """Add a deviation to a contract"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_edit_contract(request.user, contract):
            messages.error(request, "You don't have permission to add deviations.")
            return redirect('contracts:detail', pk=pk)
        
        form = DeviationForm(request.POST, contract=contract)
        
        if form.is_valid():
            Deviation.objects.create(
                contract=contract,
                clause=form.cleaned_data.get('clause'),
                description=form.cleaned_data['description'],
                risk_level=form.cleaned_data['risk_level'],
                justification=form.cleaned_data.get('justification', ''),
                created_by=request.user
            )
            
            AuditLogService.log(
                contract=contract,
                action=AuditLog.Action.ADD_DEVIATION,
                actor=request.user,
                metadata={'risk_level': form.cleaned_data['risk_level']}
            )
            
            messages.success(request, "Deviation added successfully.")
        else:
            messages.error(request, "Error adding deviation. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Risk Item Views
# ============================================================================

class RiskItemCreateView(LoginRequiredMixin, View):
    """Add a risk item to a contract"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_edit_contract(request.user, contract):
            messages.error(request, "You don't have permission to add risk items.")
            return redirect('contracts:detail', pk=pk)
        
        form = RiskItemForm(request.POST)
        
        if form.is_valid():
            RiskItem.objects.create(
                contract=contract,
                description=form.cleaned_data['description'],
                severity=form.cleaned_data['severity'],
                mitigation=form.cleaned_data.get('mitigation', ''),
                created_by=request.user
            )
            
            AuditLogService.log(
                contract=contract,
                action=AuditLog.Action.ADD_RISK,
                actor=request.user,
                metadata={'severity': form.cleaned_data['severity']}
            )
            
            messages.success(request, "Risk item added successfully.")
        else:
            messages.error(request, "Error adding risk item. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Signature Views
# ============================================================================

class SignatureRecordCreateView(LoginRequiredMixin, View):
    """Add a signature record to a contract"""
    
    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        
        if not can_edit_contract(request.user, contract):
            messages.error(request, "You don't have permission to add signature records.")
            return redirect('contracts:detail', pk=pk)
        
        form = SignatureRecordForm(request.POST)
        
        if form.is_valid():
            SignatureRecord.objects.create(
                contract=contract,
                **form.cleaned_data
            )
            
            AuditLogService.log(
                contract=contract,
                action=AuditLog.Action.ADD_SIGNATURE,
                actor=request.user,
                metadata={
                    'signatory_name': form.cleaned_data['signatory_name'],
                    'party': form.cleaned_data['party']
                }
            )
            
            messages.success(request, "Signature record added successfully.")
        else:
            messages.error(request, "Error adding signature record. Please check the form.")
        
        return redirect('contracts:detail', pk=pk)


# ============================================================================
# Configurations - Single Page
# ============================================================================

class ConfigurationsView(LoginRequiredMixin, TemplateView):
    """Single page for all configurations"""
    template_name = 'contracts/configurations.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not can_admin_contracts(request.user):
            messages.error(request, "You don't have permission to access configurations.")
            return redirect('contracts:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'contract_types': ContractType.objects.all().order_by('name'),
            'tags': Tag.objects.all().order_by('name'),
            'departments': Department.objects.all().order_by('name'),
            'playbook_entries': ClausePlaybookEntry.objects.all().order_by('label'),
            **get_user_permissions_context(self.request.user),
        })
        return context


class ConfigTypeCreateView(LoginRequiredMixin, View):
    """Create contract type from configurations page"""
    
    def post(self, request):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        active = request.POST.get('active') == 'on'
        
        ContractType.objects.create(name=name, description=description, active=active)
        messages.success(request, f"Contract type '{name}' created.")
        
        return redirect('contracts:configurations')


class ConfigTypeDeleteView(LoginRequiredMixin, View):
    """Delete contract type"""
    
    def post(self, request, pk):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        obj = get_object_or_404(ContractType, pk=pk)
        obj.delete()
        messages.success(request, "Contract type deleted.")
        
        return redirect('contracts:configurations')


class ConfigTagCreateView(LoginRequiredMixin, View):
    """Create tag from configurations page"""
    
    def post(self, request):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        color = request.POST.get('color', '#10b981')
        active = request.POST.get('active') == 'on'
        
        Tag.objects.create(name=name, description=description, color=color, active=active)
        messages.success(request, f"Tag '{name}' created.")
        
        return redirect('contracts:configurations')


class ConfigTagDeleteView(LoginRequiredMixin, View):
    """Delete tag"""
    
    def post(self, request, pk):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        obj = get_object_or_404(Tag, pk=pk)
        obj.delete()
        messages.success(request, "Tag deleted.")
        
        return redirect('contracts:configurations')


class ConfigDeptCreateView(LoginRequiredMixin, View):
    """Create department from configurations page"""
    
    def post(self, request):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        name = request.POST.get('name')
        
        Department.objects.create(name=name)
        messages.success(request, f"Department '{name}' created.")
        
        return redirect('contracts:configurations')


class ConfigDeptDeleteView(LoginRequiredMixin, View):
    """Delete department"""
    
    def post(self, request, pk):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        obj = get_object_or_404(Department, pk=pk)
        obj.delete()
        messages.success(request, "Department deleted.")
        
        return redirect('contracts:configurations')


class ConfigClauseCreateView(LoginRequiredMixin, View):
    """Create clause playbook entry from configurations page"""
    
    def post(self, request):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        ClausePlaybookEntry.objects.create(
            label=request.POST.get('label'),
            category=request.POST.get('category', ''),
            recommended_text=request.POST.get('recommended_text'),
            risk_level=request.POST.get('risk_level', 'LOW'),
            guidance_notes=request.POST.get('guidance_notes', ''),
            active=request.POST.get('active') == 'on'
        )
        messages.success(request, "Clause added to playbook.")
        
        return redirect('contracts:configurations')


class ConfigClauseDeleteView(LoginRequiredMixin, View):
    """Delete clause playbook entry"""
    
    def post(self, request, pk):
        if not can_admin_contracts(request.user):
            return HttpResponseForbidden()
        
        obj = get_object_or_404(ClausePlaybookEntry, pk=pk)
        obj.delete()
        messages.success(request, "Clause deleted.")
        
        return redirect('contracts:configurations')
