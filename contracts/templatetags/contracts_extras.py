"""
Template tags and filters for Contract Management module.
"""

from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import timedelta

from contracts.permissions import (
    can_view_contract, can_edit_contract, can_delete_contract,
    can_manage_approvals, can_admin_contracts, can_create_contract,
    is_legal_admin, is_legal_user, is_finance_viewer, get_user_role
)

register = template.Library()


# ============================================================================
# Permission Tags
# ============================================================================

@register.simple_tag
def can_view(user, contract):
    """Check if user can view a contract"""
    return can_view_contract(user, contract)


@register.simple_tag
def can_edit(user, contract):
    """Check if user can edit a contract"""
    return can_edit_contract(user, contract)


@register.simple_tag
def can_delete(user, contract):
    """Check if user can delete a contract"""
    return can_delete_contract(user, contract)


@register.simple_tag
def can_manage_approval(user, contract):
    """Check if user can manage approvals for a contract"""
    return can_manage_approvals(user, contract)


@register.simple_tag
def user_is_admin(user):
    """Check if user is a legal admin"""
    return is_legal_admin(user)


@register.simple_tag
def user_is_legal(user):
    """Check if user is a legal user"""
    return is_legal_user(user)


@register.simple_tag
def user_role(user):
    """Get user's role"""
    return get_user_role(user)


# ============================================================================
# Status Tags
# ============================================================================

@register.filter
def status_badge(status):
    """Return Bootstrap badge class for contract status"""
    badges = {
        'DRAFT': 'bg-secondary',
        'PENDING': 'bg-warning text-dark',
        'ACTIVE': 'bg-success',
        'EXPIRED': 'bg-danger',
        'TERMINATED': 'bg-dark',
        'ARCHIVED': 'bg-info',
    }
    badge_class = badges.get(status, 'bg-secondary')
    return mark_safe(f'<span class="badge {badge_class}">{status}</span>')


@register.filter
def approval_status_badge(status):
    """Return Bootstrap badge class for approval status"""
    badges = {
        'PENDING': 'bg-warning text-dark',
        'APPROVED': 'bg-success',
        'REJECTED': 'bg-danger',
        'CANCELLED': 'bg-secondary',
    }
    badge_class = badges.get(status, 'bg-secondary')
    return mark_safe(f'<span class="badge {badge_class}">{status}</span>')


@register.filter
def risk_badge(risk_level):
    """Return Bootstrap badge class for risk level"""
    badges = {
        'LOW': 'bg-success',
        'MEDIUM': 'bg-warning text-dark',
        'HIGH': 'bg-danger',
        'CRITICAL': 'bg-dark',
    }
    badge_class = badges.get(risk_level, 'bg-secondary')
    return mark_safe(f'<span class="badge {badge_class}">{risk_level}</span>')


@register.filter
def assignment_badge(status):
    """Return Bootstrap badge class for assignment status"""
    badges = {
        'NOT_ASSIGNED': 'bg-secondary',
        'IN_PROGRESS': 'bg-primary',
        'COMPLETED': 'bg-success',
    }
    badge_class = badges.get(status, 'bg-secondary')
    label = status.replace('_', ' ').title()
    return mark_safe(f'<span class="badge {badge_class}">{label}</span>')


# ============================================================================
# Date Tags
# ============================================================================

@register.filter
def days_until(date):
    """Calculate days until a date"""
    if not date:
        return None
    today = timezone.now().date()
    delta = date - today
    return delta.days


@register.filter
def is_expiring_soon(date, days=30):
    """Check if date is within specified days"""
    if not date:
        return False
    today = timezone.now().date()
    threshold = today + timedelta(days=days)
    return today <= date <= threshold


@register.filter
def expiry_class(date):
    """Return CSS class based on how soon a date is"""
    if not date:
        return ''
    
    days = days_until(date)
    if days is None:
        return ''
    
    if days < 0:
        return 'text-danger fw-bold'
    elif days <= 7:
        return 'text-danger'
    elif days <= 30:
        return 'text-warning'
    else:
        return 'text-muted'


# ============================================================================
# Formatting Tags
# ============================================================================

@register.filter
def currency_format(value, currency='INR'):
    """Format a decimal value as currency"""
    if value is None:
        return '-'
    
    symbols = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'AED': 'د.إ',
        'SGD': 'S$',
    }
    
    symbol = symbols.get(currency, currency + ' ')
    formatted = f"{value:,.2f}"
    return f"{symbol}{formatted}"


@register.filter
def file_size_format(size_bytes):
    """Format file size in human-readable format"""
    if not size_bytes:
        return '0 B'
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} TB"


@register.filter
def truncate_middle(value, length=50):
    """Truncate a string in the middle if too long"""
    if not value or len(value) <= length:
        return value
    
    half = (length - 3) // 2
    return f"{value[:half]}...{value[-half:]}"


# ============================================================================
# Audit Log Tags
# ============================================================================

@register.filter
def audit_action_icon(action):
    """Return Bootstrap icon class for audit action"""
    icons = {
        'CREATE_CONTRACT': 'bi-file-plus',
        'UPDATE_CONTRACT': 'bi-pencil',
        'DELETE_CONTRACT': 'bi-trash',
        'CHANGE_STATUS': 'bi-arrow-repeat',
        'ADD_FILE': 'bi-paperclip',
        'REMOVE_FILE': 'bi-x-circle',
        'ADD_VERSION': 'bi-layers',
        'CREATE_APPROVAL': 'bi-person-plus',
        'APPROVE': 'bi-check-circle',
        'REJECT': 'bi-x-circle',
        'CANCEL_APPROVAL': 'bi-slash-circle',
        'SHARE': 'bi-share',
        'UNSHARE': 'bi-share-fill',
        'ADD_CLAUSE': 'bi-list-check',
        'UPDATE_CLAUSE': 'bi-pencil-square',
        'ADD_DEVIATION': 'bi-exclamation-triangle',
        'ADD_RISK': 'bi-shield-exclamation',
        'ADD_SIGNATURE': 'bi-pen',
        'SIGN': 'bi-pen-fill',
        'VIEW': 'bi-eye',
        'DOWNLOAD': 'bi-download',
    }
    return icons.get(action, 'bi-circle')


@register.filter
def audit_action_color(action):
    """Return color class for audit action"""
    colors = {
        'CREATE_CONTRACT': 'text-success',
        'UPDATE_CONTRACT': 'text-primary',
        'DELETE_CONTRACT': 'text-danger',
        'CHANGE_STATUS': 'text-info',
        'APPROVE': 'text-success',
        'REJECT': 'text-danger',
        'ADD_RISK': 'text-warning',
        'ADD_DEVIATION': 'text-warning',
    }
    return colors.get(action, 'text-muted')


# ============================================================================
# Navigation Tags
# ============================================================================

@register.simple_tag(takes_context=True)
def active_tab(context, tab_name):
    """Return 'active' class if current tab matches"""
    request = context.get('request')
    if request:
        current_tab = request.GET.get('tab', 'repository')
        return 'active' if current_tab == tab_name else ''
    return ''


@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    """Build query string preserving existing params"""
    request = context.get('request')
    if not request:
        return ''
    
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    
    return params.urlencode()


# ============================================================================
# Contract Display Tags
# ============================================================================

@register.filter
def category_display(category):
    """Return display name for category"""
    from contracts.models import Contract
    try:
        return dict(Contract.Category.choices).get(category, category)
    except Exception:
        return category


@register.filter
def party_display(party):
    """Return display name for party type"""
    parties = {
        'CUSTOMER': 'Customer',
        'VENDOR': 'Vendor',
        'INTERNAL': 'Internal',
    }
    return parties.get(party, party)


@register.filter
def sign_type_display(sign_type):
    """Return display name for signature type"""
    types = {
        'AADHAAR': 'Aadhaar eSign',
        'WET': 'Wet Signature',
        'ESIGN': 'Electronic Signature',
        'DSC': 'Digital Signature Certificate',
    }
    return types.get(sign_type, sign_type)


# ============================================================================
# Inclusion Tags
# ============================================================================

@register.inclusion_tag('contracts/includes/contract_card.html')
def contract_card(contract, user):
    """Render a contract card"""
    return {
        'contract': contract,
        'user': user,
        'can_edit': can_edit_contract(user, contract),
        'can_delete': can_delete_contract(user, contract),
    }


@register.inclusion_tag('contracts/includes/status_select.html')
def status_select(current_status, field_name='status'):
    """Render a status select dropdown"""
    from contracts.models import Contract
    return {
        'current_status': current_status,
        'field_name': field_name,
        'choices': Contract.Status.choices,
    }

