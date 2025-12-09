"""
Business logic and service functions for Contract Management module.
Includes dashboard metrics, query helpers, and contract operations.
"""

from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.db.models import Count, Q, Sum, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    Contract, ContractFile, ContractVersion, ContractShare,
    AdditionalApproval, Clause, Deviation, RiskItem, AuditLog,
    Department, ContractType, Tag
)
from .permissions import (
    is_legal_admin, is_legal_user, is_finance_viewer,
    can_view_contract
)

User = get_user_model()


# ============================================================================
# Dashboard Metrics Service
# ============================================================================

class DashboardService:
    """Service class for computing dashboard metrics"""
    
    def __init__(self, user):
        self.user = user
        self.today = timezone.now().date()
    
    def get_all_metrics(self):
        """Get all dashboard metrics for the user"""
        return {
            'pending_action': self.get_pending_action_contracts(),
            'pending_approvals': self.get_pending_approvals(),
            'expiring_contracts': self.get_expiring_contracts(),
            'notified_contracts': self.get_notified_contracts(),
            'contract_stats': self.get_contract_stats(),
            'recent_activity': self.get_recent_activity(),
            'quick_stats': self.get_quick_stats(),
        }
    
    def get_pending_action_contracts(self):
        """
        Get contracts pending user's action.
        These are contracts where user is owner and status is DRAFT or PENDING.
        """
        contracts = Contract.objects.filter(
            owner=self.user,
            status__in=[Contract.Status.DRAFT, Contract.Status.PENDING]
        ).order_by('-updated_at')[:10]
        
        return {
            'count': contracts.count(),
            'items': list(contracts),
        }
    
    def get_pending_approvals(self):
        """
        Get additional approvals pending user's action.
        """
        approvals = AdditionalApproval.objects.filter(
            approver=self.user,
            status=AdditionalApproval.Status.PENDING
        ).select_related('contract', 'requested_by').order_by('-created_at')[:10]
        
        return {
            'count': approvals.count(),
            'items': list(approvals),
        }
    
    def get_expiring_contracts(self, days=30):
        """
        Get contracts expiring within specified days.
        """
        expiry_date = self.today + timedelta(days=days)
        
        # Build base query
        queryset = Contract.objects.filter(
            status=Contract.Status.ACTIVE,
            end_date__isnull=False,
            end_date__lte=expiry_date,
            end_date__gte=self.today
        )
        
        # Filter based on user access
        if not is_legal_admin(self.user):
            queryset = self._filter_user_accessible_contracts(queryset)
        
        contracts = queryset.order_by('end_date')[:10]
        
        return {
            'count': queryset.count(),
            'items': list(contracts),
        }
    
    def get_notified_contracts(self):
        """
        Get contracts with upcoming renewal notice dates.
        """
        notice_date = self.today + timedelta(days=30)
        
        queryset = Contract.objects.filter(
            status=Contract.Status.ACTIVE,
            auto_renewal=True,
            renewal_notice_date__isnull=False,
            renewal_notice_date__lte=notice_date,
            renewal_notice_date__gte=self.today
        )
        
        if not is_legal_admin(self.user):
            queryset = self._filter_user_accessible_contracts(queryset)
        
        contracts = queryset.order_by('renewal_notice_date')[:10]
        
        return {
            'count': queryset.count(),
            'items': list(contracts),
        }
    
    def get_contract_stats(self):
        """
        Get contract statistics by status.
        """
        queryset = Contract.objects.all()
        
        if not is_legal_admin(self.user):
            queryset = self._filter_user_accessible_contracts(queryset)
        
        stats = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Convert to dict for easy access
        status_counts = {item['status']: item['count'] for item in stats}
        
        return {
            'draft': status_counts.get(Contract.Status.DRAFT, 0),
            'pending': status_counts.get(Contract.Status.PENDING, 0),
            'active': status_counts.get(Contract.Status.ACTIVE, 0),
            'expired': status_counts.get(Contract.Status.EXPIRED, 0),
            'terminated': status_counts.get(Contract.Status.TERMINATED, 0),
            'archived': status_counts.get(Contract.Status.ARCHIVED, 0),
            'total': sum(status_counts.values()),
        }
    
    def get_quick_stats(self):
        """
        Get quick statistics for dashboard cards.
        """
        queryset = Contract.objects.all()
        
        if not is_legal_admin(self.user):
            queryset = self._filter_user_accessible_contracts(queryset)
        
        # Total value of active contracts
        active_value = queryset.filter(
            status=Contract.Status.ACTIVE,
            value_amount__isnull=False
        ).aggregate(total=Sum('value_amount'))['total'] or Decimal('0')
        
        # Contracts created this month
        start_of_month = self.today.replace(day=1)
        created_this_month = queryset.filter(
            created_at__date__gte=start_of_month
        ).count()
        
        # High risk items count
        high_risk_count = RiskItem.objects.filter(
            contract__in=queryset,
            severity__in=['HIGH', 'CRITICAL'],
            status='OPEN'
        ).count()
        
        return {
            'active_value': active_value,
            'created_this_month': created_this_month,
            'high_risk_count': high_risk_count,
        }
    
    def get_recent_activity(self, limit=10):
        """
        Get recent audit log entries for contracts user can access.
        """
        queryset = AuditLog.objects.select_related('contract', 'actor')
        
        if not is_legal_admin(self.user):
            accessible_contracts = self._filter_user_accessible_contracts(
                Contract.objects.all()
            )
            queryset = queryset.filter(
                Q(contract__in=accessible_contracts) |
                Q(actor=self.user)
            )
        
        return list(queryset.order_by('-created_at')[:limit])
    
    def _filter_user_accessible_contracts(self, queryset):
        """
        Filter queryset to only include contracts the user can access.
        """
        # User owns or created
        user_contracts = Q(owner=self.user) | Q(created_by=self.user)
        
        # Shared directly with user
        shared_with_user = Q(shares__shared_with_user=self.user)
        
        # Build the filter
        filter_q = user_contracts | shared_with_user
        
        # Shared with user's department
        if hasattr(self.user, 'department') and self.user.department:
            filter_q |= Q(shares__shared_with_department=self.user.department)
            filter_q |= Q(bu_team=self.user.department)
        
        # Finance viewers can see non-confidential
        if is_finance_viewer(self.user):
            filter_q |= Q(is_confidential=False)
        
        # Legal users can see contracts they have approvals for
        if is_legal_user(self.user):
            filter_q |= Q(approvals__approver=self.user)
            filter_q |= Q(approvals__requested_by=self.user)
        
        return queryset.filter(filter_q).distinct()


# ============================================================================
# Contract Query Service
# ============================================================================

class ContractQueryService:
    """Service for querying and filtering contracts"""
    
    def __init__(self, user):
        self.user = user
    
    def get_contracts_for_tab(self, tab, filters=None):
        """
        Get contracts for a specific tab.
        
        Tabs:
        - new: Not really a tab, just CTA
        - draft: DRAFT status contracts
        - pending: PENDING status or has pending approvals
        - repository: All other contracts (ACTIVE, EXPIRED, etc.)
        """
        queryset = self._get_base_queryset()
        
        if tab == 'draft':
            queryset = queryset.filter(status=Contract.Status.DRAFT)
        elif tab == 'pending':
            queryset = queryset.filter(
                Q(status=Contract.Status.PENDING) |
                Q(approvals__status=AdditionalApproval.Status.PENDING)
            ).distinct()
        elif tab == 'repository':
            queryset = queryset.exclude(
                status__in=[Contract.Status.DRAFT, Contract.Status.PENDING]
            ).exclude(
                Q(status=Contract.Status.DRAFT) &
                Q(approvals__status=AdditionalApproval.Status.PENDING)
            )
        
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        return queryset
    
    def _get_base_queryset(self):
        """Get base queryset filtered by user access"""
        queryset = Contract.objects.select_related(
            'owner', 'bu_team', 'contract_type', 'created_by'
        ).prefetch_related('tags')
        
        if not is_legal_admin(self.user):
            dashboard_service = DashboardService(self.user)
            queryset = dashboard_service._filter_user_accessible_contracts(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset, filters):
        """Apply filters to queryset"""
        
        # Search filter
        search = filters.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(contract_number__icontains=search) |
                Q(customer_or_vendor_name__icontains=search)
            )
        
        # Status filter
        status = filters.get('status')
        if status:
            if isinstance(status, list):
                queryset = queryset.filter(status__in=status)
            else:
                queryset = queryset.filter(status=status)
        
        # Category filter
        category = filters.get('category')
        if category:
            if isinstance(category, list):
                queryset = queryset.filter(category__in=category)
            else:
                queryset = queryset.filter(category=category)
        
        # BU/Team filter
        bu_team = filters.get('bu_team')
        if bu_team:
            queryset = queryset.filter(bu_team=bu_team)
        
        # Owner filter
        owner = filters.get('owner')
        if owner:
            queryset = queryset.filter(owner=owner)
        
        # Date range filter
        date_from = filters.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = filters.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Tags filter
        tags = filters.get('tags')
        if tags:
            queryset = queryset.filter(tags__in=tags).distinct()
        
        return queryset
    
    def get_contract_detail(self, contract_id):
        """Get full contract details with related data"""
        try:
            contract = Contract.objects.select_related(
                'owner', 'bu_team', 'contract_type', 'created_by'
            ).prefetch_related(
                'tags',
                'files',
                'versions',
                'approvals__approver',
                'approvals__requested_by',
                'clauses',
                'deviations',
                'risks',
                'signatures',
                'shares__shared_with_user',
                'shares__shared_with_department',
            ).get(pk=contract_id)
            
            if can_view_contract(self.user, contract):
                return contract
            return None
        except Contract.DoesNotExist:
            return None


# ============================================================================
# Approval Service
# ============================================================================

class ApprovalService:
    """Service for managing additional approvals"""
    
    def __init__(self, user):
        self.user = user
    
    def get_approvals_for_user(self, filters=None):
        """Get approvals relevant to the user"""
        queryset = AdditionalApproval.objects.select_related(
            'contract', 'requested_by', 'approver'
        )
        
        # Base filter: user is approver or requester, or is legal admin
        if not is_legal_admin(self.user):
            queryset = queryset.filter(
                Q(approver=self.user) | Q(requested_by=self.user)
            )
        
        if filters:
            status = filters.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            if filters.get('assigned_to_me'):
                queryset = queryset.filter(approver=self.user)
            
            if filters.get('requested_by_me'):
                queryset = queryset.filter(requested_by=self.user)
        
        return queryset.order_by('-created_at')
    
    def create_approval_request(self, contract, approver, reason='', due_date=None):
        """Create a new approval request"""
        approval = AdditionalApproval.objects.create(
            contract=contract,
            requested_by=self.user,
            approver=approver,
            reason=reason,
            due_date=due_date,
            status=AdditionalApproval.Status.PENDING
        )
        
        # Log the action
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.CREATE_APPROVAL,
            actor=self.user,
            metadata={
                'approval_id': approval.id,
                'approver': str(approver),
                'reason': reason
            }
        )
        
        return approval
    
    def process_decision(self, approval, decision, comment=''):
        """Process an approval decision"""
        approval.status = decision
        approval.decision_comment = comment
        approval.decided_at = timezone.now()
        approval.save()
        
        # Determine action for audit log
        action = AuditLog.Action.APPROVE if decision == 'APPROVED' else AuditLog.Action.REJECT
        
        AuditLogService.log(
            contract=approval.contract,
            action=action,
            actor=self.user,
            metadata={
                'approval_id': approval.id,
                'comment': comment
            }
        )
        
        return approval


# ============================================================================
# Audit Log Service
# ============================================================================

class AuditLogService:
    """Service for creating audit log entries"""
    
    @staticmethod
    def log(contract, action, actor, metadata=None, request=None):
        """Create an audit log entry"""
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = AuditLogService._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return AuditLog.objects.create(
            contract=contract,
            action=action,
            actor=actor,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================================================
# Contract Operations Service
# ============================================================================

class ContractOperationsService:
    """Service for contract CRUD operations"""
    
    def __init__(self, user):
        self.user = user
    
    def create_contract(self, data, file=None):
        """Create a new contract"""
        # Set defaults
        data['created_by'] = self.user
        if not data.get('owner'):
            data['owner'] = self.user
        
        # Extract tags if present
        tags = data.pop('tags', [])
        
        # Create contract
        contract = Contract.objects.create(**data)
        
        # Add tags
        if tags:
            contract.tags.set(tags)
        
        # Handle file upload
        if file:
            self._create_contract_file(contract, file, is_primary=True)
        
        # Create initial version
        ContractVersion.objects.create(
            contract=contract,
            version_number=1,
            label='Initial Version',
            created_by=self.user
        )
        
        # Log creation
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.CREATE_CONTRACT,
            actor=self.user,
            metadata={'title': contract.title, 'status': contract.status}
        )
        
        return contract
    
    def update_contract(self, contract, data):
        """Update an existing contract"""
        old_status = contract.status
        
        # Extract tags if present
        tags = data.pop('tags', None)
        
        # Update fields
        for field, value in data.items():
            setattr(contract, field, value)
        contract.save()
        
        # Update tags if provided
        if tags is not None:
            contract.tags.set(tags)
        
        # Log status change if changed
        if contract.status != old_status:
            AuditLogService.log(
                contract=contract,
                action=AuditLog.Action.CHANGE_STATUS,
                actor=self.user,
                metadata={
                    'old_status': old_status,
                    'new_status': contract.status
                }
            )
        else:
            AuditLogService.log(
                contract=contract,
                action=AuditLog.Action.UPDATE_CONTRACT,
                actor=self.user,
                metadata={'updated_fields': list(data.keys())}
            )
        
        return contract
    
    def change_status(self, contract, new_status, reason=''):
        """Change contract status"""
        old_status = contract.status
        contract.status = new_status
        contract.save()
        
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.CHANGE_STATUS,
            actor=self.user,
            metadata={
                'old_status': old_status,
                'new_status': new_status,
                'reason': reason
            }
        )
        
        return contract
    
    def upload_file(self, contract, file, is_primary=False, description=''):
        """Upload a file to a contract"""
        contract_file = self._create_contract_file(
            contract, file, is_primary=is_primary, description=description
        )
        
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.ADD_FILE,
            actor=self.user,
            metadata={
                'filename': contract_file.original_filename,
                'is_primary': is_primary
            }
        )
        
        return contract_file
    
    def _create_contract_file(self, contract, file, is_primary=False, description=''):
        """Create a ContractFile record"""
        return ContractFile.objects.create(
            contract=contract,
            file=file,
            original_filename=file.name,
            file_size=file.size,
            mime_type=getattr(file, 'content_type', ''),
            is_primary=is_primary,
            description=description,
            uploaded_by=self.user
        )
    
    def add_version(self, contract, label, file=None, notes=''):
        """Add a new version to a contract"""
        # Get next version number
        last_version = contract.versions.order_by('-version_number').first()
        next_version = (last_version.version_number + 1) if last_version else 1
        
        version = ContractVersion.objects.create(
            contract=contract,
            version_number=next_version,
            label=label,
            file=file,
            notes=notes,
            created_by=self.user
        )
        
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.ADD_VERSION,
            actor=self.user,
            metadata={
                'version_number': next_version,
                'label': label
            }
        )
        
        return version
    
    def share_contract(self, contract, user=None, department=None, access_level='VIEW'):
        """Share a contract with a user or department"""
        share = ContractShare.objects.create(
            contract=contract,
            shared_with_user=user,
            shared_with_department=department,
            access_level=access_level,
            shared_by=self.user
        )
        
        AuditLogService.log(
            contract=contract,
            action=AuditLog.Action.SHARE,
            actor=self.user,
            metadata={
                'shared_with_user': str(user) if user else None,
                'shared_with_department': str(department) if department else None,
                'access_level': access_level
            }
        )
        
        return share


# ============================================================================
# Reports Service
# ============================================================================

class ReportsService:
    """Service for generating reports and analytics"""
    
    def __init__(self, user):
        self.user = user
    
    def get_contracts_by_month(self, year=None):
        """Get contract counts by month"""
        if not year:
            year = timezone.now().year
        
        queryset = Contract.objects.filter(
            created_at__year=year
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        return list(queryset)
    
    def get_contracts_by_category(self):
        """Get contract counts by category"""
        return list(
            Contract.objects.values('category').annotate(
                count=Count('id')
            ).order_by('-count')
        )
    
    def get_contracts_by_department(self):
        """Get contract counts by department"""
        return list(
            Contract.objects.filter(
                bu_team__isnull=False
            ).values(
                'bu_team__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
        )
    
    def get_value_by_status(self):
        """Get total contract value by status"""
        return list(
            Contract.objects.filter(
                value_amount__isnull=False
            ).values('status').annotate(
                total_value=Sum('value_amount')
            ).order_by('status')
        )
    
    def get_expiring_contracts_summary(self):
        """Get summary of expiring contracts by time period"""
        today = timezone.now().date()
        
        return {
            'next_7_days': Contract.objects.filter(
                status=Contract.Status.ACTIVE,
                end_date__lte=today + timedelta(days=7),
                end_date__gte=today
            ).count(),
            'next_30_days': Contract.objects.filter(
                status=Contract.Status.ACTIVE,
                end_date__lte=today + timedelta(days=30),
                end_date__gte=today
            ).count(),
            'next_90_days': Contract.objects.filter(
                status=Contract.Status.ACTIVE,
                end_date__lte=today + timedelta(days=90),
                end_date__gte=today
            ).count(),
        }

