"""
Permission helpers for Contract Management module.

Roles:
- LEGAL_ADMIN: Full CRUD on contracts, tags, types, clause playbook. Can manage Additional Approvals.
- LEGAL_USER: Create and edit contracts they own or shared with them.
- FINANCE_VIEWER: Read-only on relevant contracts.
- USER: Read-only on contracts explicitly shared with them.

Adapt user.role or user.groups mapping as needed for your Pulse setup.
"""

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages


# Role constants
class Roles:
    LEGAL_ADMIN = 'LEGAL_ADMIN'
    LEGAL_USER = 'LEGAL_USER'
    FINANCE_VIEWER = 'FINANCE_VIEWER'
    USER = 'USER'

    ALL_ROLES = [LEGAL_ADMIN, LEGAL_USER, FINANCE_VIEWER, USER]


def get_user_role(user):
    """
    Get the user's role for contract management.
    
    This function should be adapted to your Pulse user/role system.
    Options:
    - user.role (CharField on User model)
    - user.groups.filter(name__in=[...]).first()
    - user.profile.role
    - Custom permission system
    """
    if not user or not user.is_authenticated:
        return None
    
    # Check if user is superuser or staff - treat as LEGAL_ADMIN
    if user.is_superuser:
        return Roles.LEGAL_ADMIN
    
    # Option 1: Direct role attribute on user
    if hasattr(user, 'role'):
        return user.role
    
    # Option 2: Check user groups
    if hasattr(user, 'groups'):
        group_names = user.groups.values_list('name', flat=True)
        if 'Legal Admin' in group_names or 'legal_admin' in group_names:
            return Roles.LEGAL_ADMIN
        elif 'Legal User' in group_names or 'legal_user' in group_names:
            return Roles.LEGAL_USER
        elif 'Finance Viewer' in group_names or 'finance_viewer' in group_names:
            return Roles.FINANCE_VIEWER
    
    # Option 3: Check staff status - treat staff as LEGAL_USER
    if user.is_staff:
        return Roles.LEGAL_USER
    
    # Default role
    return Roles.USER


def is_legal_admin(user):
    """Check if user has LEGAL_ADMIN role"""
    return get_user_role(user) == Roles.LEGAL_ADMIN


def is_legal_user(user):
    """Check if user has LEGAL_USER role or higher"""
    role = get_user_role(user)
    return role in [Roles.LEGAL_ADMIN, Roles.LEGAL_USER]


def is_finance_viewer(user):
    """Check if user has FINANCE_VIEWER role"""
    return get_user_role(user) == Roles.FINANCE_VIEWER


def can_admin_contracts(user):
    """
    Check if user can manage contract settings (types, tags, playbook).
    Only LEGAL_ADMIN can do this.
    """
    return is_legal_admin(user)


def can_create_contract(user):
    """
    Check if user can create new contracts.
    LEGAL_ADMIN and LEGAL_USER can create contracts.
    """
    return is_legal_user(user)


def can_view_contract(user, contract):
    """
    Check if user can view a contract.
    
    User can view if:
    - User is LEGAL_ADMIN (can see all)
    - User is the contract owner
    - User is the contract creator
    - Contract is shared with user directly
    - Contract is shared with user's department
    - User is FINANCE_VIEWER and contract is in a relevant category/department
    """
    if not user or not user.is_authenticated:
        return False
    
    # LEGAL_ADMIN can see everything
    if is_legal_admin(user):
        return True
    
    # Owner or creator can always see
    if contract.owner == user or contract.created_by == user:
        return True
    
    # Check direct shares
    from .models import ContractShare
    if ContractShare.objects.filter(
        contract=contract,
        shared_with_user=user
    ).exists():
        return True
    
    # Check department shares
    if hasattr(user, 'department') and user.department:
        if ContractShare.objects.filter(
            contract=contract,
            shared_with_department=user.department
        ).exists():
            return True
    
    # Check if user's department matches contract's BU/Team
    if hasattr(user, 'department') and user.department and contract.bu_team:
        if user.department == contract.bu_team:
            return True
    
    # FINANCE_VIEWER can see non-confidential contracts
    if is_finance_viewer(user) and not contract.is_confidential:
        return True
    
    # LEGAL_USER can see contracts they have approvals for
    if is_legal_user(user):
        if contract.approvals.filter(approver=user).exists():
            return True
        if contract.approvals.filter(requested_by=user).exists():
            return True
    
    return False


def can_edit_contract(user, contract):
    """
    Check if user can edit a contract.
    
    User can edit if:
    - User is LEGAL_ADMIN
    - User is the contract owner
    - User has EDIT access via share
    - User is LEGAL_USER and contract is shared with them
    """
    if not user or not user.is_authenticated:
        return False
    
    # LEGAL_ADMIN can edit everything
    if is_legal_admin(user):
        return True
    
    # Owner can always edit
    if contract.owner == user:
        return True
    
    # Check for EDIT shares
    from .models import ContractShare
    if ContractShare.objects.filter(
        contract=contract,
        shared_with_user=user,
        access_level='EDIT'
    ).exists():
        return True
    
    # Check department EDIT shares
    if hasattr(user, 'department') and user.department:
        if ContractShare.objects.filter(
            contract=contract,
            shared_with_department=user.department,
            access_level='EDIT'
        ).exists():
            return True
    
    return False


def can_delete_contract(user, contract):
    """
    Check if user can delete a contract.
    Only LEGAL_ADMIN or owner (for DRAFT contracts) can delete.
    """
    if not user or not user.is_authenticated:
        return False
    
    if is_legal_admin(user):
        return True
    
    # Owner can delete only DRAFT contracts
    if contract.owner == user and contract.status == 'DRAFT':
        return True
    
    return False


def can_manage_approvals(user, contract):
    """
    Check if user can manage approvals for a contract.
    
    User can manage approvals if:
    - User is LEGAL_ADMIN
    - User is the contract owner
    - User can edit the contract
    """
    if not user or not user.is_authenticated:
        return False
    
    if is_legal_admin(user):
        return True
    
    if contract.owner == user:
        return True
    
    return can_edit_contract(user, contract)


def can_approve_request(user, approval):
    """
    Check if user can approve/reject an approval request.
    User must be the designated approver.
    """
    if not user or not user.is_authenticated:
        return False
    
    # The designated approver
    if approval.approver == user:
        return True
    
    # LEGAL_ADMIN can act on behalf
    if is_legal_admin(user):
        return True
    
    return False


def can_upload_files(user, contract):
    """Check if user can upload files to a contract"""
    return can_edit_contract(user, contract)


def can_add_version(user, contract):
    """Check if user can add a new version to a contract"""
    return can_edit_contract(user, contract)


def can_change_status(user, contract):
    """
    Check if user can change contract status.
    LEGAL_ADMIN, owner, or users with edit permission can change status.
    """
    if not user or not user.is_authenticated:
        return False
    
    if is_legal_admin(user):
        return True
    
    if contract.owner == user:
        return True
    
    return can_edit_contract(user, contract)


def can_manage_clauses(user, contract):
    """Check if user can manage clauses for a contract"""
    return can_edit_contract(user, contract)


def can_manage_risks(user, contract):
    """Check if user can manage risk items for a contract"""
    return can_edit_contract(user, contract)


def can_manage_deviations(user, contract):
    """Check if user can manage deviations for a contract"""
    return can_edit_contract(user, contract)


def can_manage_signatures(user, contract):
    """Check if user can manage signature records for a contract"""
    return can_edit_contract(user, contract)


def can_share_contract(user, contract):
    """Check if user can share a contract with others"""
    if not user or not user.is_authenticated:
        return False
    
    if is_legal_admin(user):
        return True
    
    if contract.owner == user:
        return True
    
    return False


# Decorators for view protection

def contract_permission_required(permission_func):
    """
    Decorator for views that require contract-specific permission.
    Expects the view to receive 'pk' as the contract ID.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            from .models import Contract
            
            pk = kwargs.get('pk')
            if not pk:
                return HttpResponseForbidden("Contract ID required")
            
            try:
                contract = Contract.objects.get(pk=pk)
            except Contract.DoesNotExist:
                return HttpResponseForbidden("Contract not found")
            
            if not permission_func(request.user, contract):
                messages.error(request, "You don't have permission to perform this action.")
                return redirect('contracts:dashboard')
            
            # Add contract to kwargs for convenience
            kwargs['contract_obj'] = contract
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator for views that require LEGAL_ADMIN role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not can_admin_contracts(request.user):
            messages.error(request, "You don't have admin permission for contract management.")
            return redirect('contracts:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def legal_user_required(view_func):
    """Decorator for views that require LEGAL_USER role or higher"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_legal_user(request.user):
            messages.error(request, "You don't have permission to access this feature.")
            return redirect('contracts:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Template context processor helper
def get_user_permissions_context(user, contract=None):
    """
    Get a dictionary of user permissions for use in templates.
    """
    context = {
        'is_legal_admin': is_legal_admin(user),
        'is_legal_user': is_legal_user(user),
        'is_finance_viewer': is_finance_viewer(user),
        'can_admin_contracts': can_admin_contracts(user),
        'can_create_contract': can_create_contract(user),
        'user_role': get_user_role(user),
    }
    
    if contract:
        context.update({
            'can_view_contract': can_view_contract(user, contract),
            'can_edit_contract': can_edit_contract(user, contract),
            'can_delete_contract': can_delete_contract(user, contract),
            'can_manage_approvals': can_manage_approvals(user, contract),
            'can_upload_files': can_upload_files(user, contract),
            'can_add_version': can_add_version(user, contract),
            'can_change_status': can_change_status(user, contract),
            'can_manage_clauses': can_manage_clauses(user, contract),
            'can_manage_risks': can_manage_risks(user, contract),
            'can_manage_deviations': can_manage_deviations(user, contract),
            'can_manage_signatures': can_manage_signatures(user, contract),
            'can_share_contract': can_share_contract(user, contract),
        })
    
    return context

