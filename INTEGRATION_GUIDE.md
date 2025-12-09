# Contract Module - Integration Guide for Netcore Pulse

**Version:** 1.0  
**Last Updated:** December 2025  
**Module:** Contract Management (SimpliContract Replacement)

---

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [File Structure](#file-structure)
4. [Installation Steps](#installation-steps)
5. [Role & Permission System](#role--permission-system)
6. [Database Schema](#database-schema)
7. [URL Endpoints](#url-endpoints)
8. [Configuration Options](#configuration-options)
9. [Important Notes](#important-notes)
10. [Customization Guide](#customization-guide)

---

## Overview

The Contract Management module provides a complete contract repository system with:
- Multi-step contract creation wizard
- Document upload and versioning
- Role-based access control (4 roles)
- Approval workflows
- Clause management with playbook
- Risk and deviation tracking
- Signature tracking
- Full audit logging

---

## Requirements

### Python Dependencies

```
Django>=4.2
Pillow>=10.0.0
```

### Django Version
- Tested with Django 4.2+ and Django 6.0
- Uses `settings.AUTH_USER_MODEL` for user references (compatible with custom User models)

### Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Bootstrap 5.3 for UI components
- Bootstrap Icons for iconography

---

## File Structure

```
contracts/
├── __init__.py
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── forms.py              # All form definitions
├── middleware.py         # Demo middleware (REMOVE IN PRODUCTION)
├── models.py             # Database models (14 models)
├── permissions.py        # Role-based access control logic
├── services.py           # Business logic services
├── urls.py               # URL routing
├── views.py              # View controllers
├── migrations/           # Database migrations
└── templatetags/
    └── contracts_extras.py  # Custom template filters/tags

templates/
└── contracts/
    ├── base_contracts.html      # Base template for module
    ├── dashboard.html           # Main dashboard
    ├── contract_list.html       # Contract listing
    ├── contract_detail.html     # Contract detail view
    ├── contract_form.html       # Creation wizard
    ├── contract_edit.html       # Edit form
    ├── approvals_list.html      # Approvals listing
    ├── approval_detail.html     # Approval detail/decision
    ├── configurations.html      # Settings page
    └── includes/
        ├── modals.html          # Modal dialogs
        ├── contract_card.html   # Contract card component
        └── status_select.html   # Status dropdown

static/
└── contracts/
    ├── css/
    │   └── contracts.css    # Module styles
    └── js/
        └── contracts.js     # JavaScript functionality
```

---

## Installation Steps

### Step 1: Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Add contracts app
    'contracts',
]
```

### Step 2: Configure URLs

```python
# urls.py (main project)
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('contracts/', include('contracts.urls')),
    # ... other urls
]

# For development - serve media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Step 3: Configure Settings

```python
# settings.py

# Templates - ensure templates directory is configured
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Project-level templates
        'APP_DIRS': True,
        # ... rest of config
    },
]

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (for contract documents)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Login configuration
LOGIN_URL = '/your-login-url/'  # Adjust to your auth system
LOGIN_REDIRECT_URL = '/contracts/'
```

### Step 4: Run Migrations

```bash
python manage.py makemigrations contracts
python manage.py migrate
```

### Step 5: Create User Groups (for RBAC)

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import Group

# Create the required groups
Group.objects.get_or_create(name='Legal Admin')
Group.objects.get_or_create(name='Legal User')
Group.objects.get_or_create(name='Finance Viewer')
```

### Step 6: ⚠️ REMOVE Demo Middleware

**IMPORTANT:** Remove the `MockUserMiddleware` from settings before production:

```python
# settings.py - REMOVE this line:
MIDDLEWARE = [
    # ...
    'contracts.middleware.MockUserMiddleware',  # DELETE THIS LINE
    # ...
]
```

This middleware auto-creates a demo superuser. It must be removed for production.

---

## Role & Permission System

### Role Hierarchy

| Role | Priority | Description |
|------|----------|-------------|
| `LEGAL_ADMIN` | 1 (Highest) | Full administrative access |
| `LEGAL_USER` | 2 | Create/edit contracts |
| `FINANCE_VIEWER` | 3 | Read-only access |
| `USER` | 4 (Default) | Basic shared access only |

### How Roles Are Determined

The system checks in this order (first match wins):

1. `user.is_superuser == True` → **LEGAL_ADMIN**
2. User in group `"Legal Admin"` or `"legal_admin"` → **LEGAL_ADMIN**
3. User in group `"Legal User"` or `"legal_user"` → **LEGAL_USER**
4. User in group `"Finance Viewer"` or `"finance_viewer"` → **FINANCE_VIEWER**
5. `user.is_staff == True` → **LEGAL_USER**
6. Default → **USER**

### Permission Matrix

| Action | LEGAL_ADMIN | LEGAL_USER | FINANCE_VIEWER | USER |
|--------|:-----------:|:----------:|:--------------:|:----:|
| View all contracts | ✅ | ❌ | ❌ | ❌ |
| View owned/shared contracts | ✅ | ✅ | ✅* | ✅ |
| Create contracts | ✅ | ✅ | ❌ | ❌ |
| Edit any contract | ✅ | ❌ | ❌ | ❌ |
| Edit owned contracts | ✅ | ✅ | ❌ | ❌ |
| Delete any contract | ✅ | ❌ | ❌ | ❌ |
| Delete own DRAFT | ✅ | ✅ | ❌ | ❌ |
| Change status | ✅ | ✅** | ❌ | ❌ |
| Manage approvals | ✅ | ✅** | ❌ | ❌ |
| Approve requests | ✅ | ✅*** | ❌ | ❌ |
| Access Settings | ✅ | ❌ | ❌ | ❌ |
| Manage configurations | ✅ | ❌ | ❌ | ❌ |

*Non-confidential only | **If owner or has edit access | ***Only if designated approver

### Django Admin Group Setup

Create these groups in Django Admin (`/admin/auth/group/`):

| Group Name | Maps to Role |
|------------|--------------|
| `Legal Admin` | LEGAL_ADMIN |
| `Legal User` | LEGAL_USER |
| `Finance Viewer` | FINANCE_VIEWER |

Then assign users to groups via User admin page.

---

## Database Schema

### Models Overview (14 Total)

| Model | Table Name | Description |
|-------|------------|-------------|
| `Department` | `contracts_department` | Business units/teams |
| `ContractType` | `contracts_contract_type` | Contract classifications |
| `Tag` | `contracts_tag` | Categorization tags |
| `Contract` | `contracts_contract` | Main contract records |
| `ContractTag` | `contracts_contract_tag` | Contract-Tag relations |
| `ContractFile` | `contracts_contract_file` | Uploaded documents |
| `ContractVersion` | `contracts_contract_version` | Version history |
| `ContractShare` | `contracts_contract_share` | Sharing permissions |
| `AdditionalApproval` | `contracts_additional_approval` | Approval requests |
| `Clause` | `contracts_clause` | Contract clauses |
| `ClausePlaybookEntry` | `contracts_clause_playbook_entry` | Clause templates |
| `Deviation` | `contracts_deviation` | Clause deviations |
| `RiskItem` | `contracts_risk_item` | Risk tracking |
| `SignatureRecord` | `contracts_signature_record` | Signature tracking |
| `AuditLog` | `contracts_audit_log` | Activity audit trail |

### Contract Status Values

```python
DRAFT = 'DRAFT'        # Initial state
PENDING = 'PENDING'    # Awaiting action/approval
ACTIVE = 'ACTIVE'      # Currently active
EXPIRED = 'EXPIRED'    # Past end date
TERMINATED = 'TERMINATED'  # Manually ended
ARCHIVED = 'ARCHIVED'  # Archived/inactive
```

### Contract Categories

```python
SALES = 'SALES'
PROCUREMENT = 'PROCUREMENT'
HR = 'HR'
LEGAL = 'LEGAL'
FINANCE = 'FINANCE'
PARTNERSHIP = 'PARTNERSHIP'
NDA = 'NDA'
SERVICE = 'SERVICE'
OTHER = 'OTHER'
```

### Approval Status Values

```python
PENDING = 'PENDING'
APPROVED = 'APPROVED'
REJECTED = 'REJECTED'
CANCELLED = 'CANCELLED'
```

---

## URL Endpoints

### Main Pages

| URL | Name | Description |
|-----|------|-------------|
| `/contracts/` | `dashboard` | Main dashboard |
| `/contracts/list/` | `list` | Contract listing (with tabs) |
| `/contracts/new/` | `create` | Contract creation wizard |
| `/contracts/<uuid>/` | `detail` | Contract detail view |
| `/contracts/<uuid>/edit/` | `edit` | Edit contract |
| `/contracts/approvals/` | `approvals` | Approvals list |
| `/contracts/approvals/<id>/` | `approval_detail` | Approval detail/decision |
| `/contracts/configurations/` | `configurations` | Settings page |

### Contract Actions

| URL | Method | Description |
|-----|--------|-------------|
| `/contracts/<uuid>/status/` | POST | Change status |
| `/contracts/<uuid>/share/` | POST | Share contract |
| `/contracts/<uuid>/files/upload/` | POST | Upload file |
| `/contracts/<uuid>/files/<id>/download/` | GET | Download file |
| `/contracts/<uuid>/versions/add/` | POST | Add version |
| `/contracts/<uuid>/approvals/request/` | POST | Request approval |
| `/contracts/<uuid>/clauses/add/` | POST | Add clause |
| `/contracts/<uuid>/deviations/add/` | POST | Add deviation |
| `/contracts/<uuid>/risks/add/` | POST | Add risk |
| `/contracts/<uuid>/signatures/add/` | POST | Add signature |

### Configuration Endpoints

| URL | Method | Description |
|-----|--------|-------------|
| `/contracts/configurations/type/create/` | POST | Create contract type |
| `/contracts/configurations/type/<id>/delete/` | POST | Delete contract type |
| `/contracts/configurations/tag/create/` | POST | Create tag |
| `/contracts/configurations/tag/<id>/delete/` | POST | Delete tag |
| `/contracts/configurations/dept/create/` | POST | Create department |
| `/contracts/configurations/dept/<id>/delete/` | POST | Delete department |
| `/contracts/configurations/clause/create/` | POST | Create playbook clause |
| `/contracts/configurations/clause/<id>/delete/` | POST | Delete playbook clause |

---

## Configuration Options

### Adapting the Role System

If Pulse uses a different role system, modify `contracts/permissions.py`:

```python
def get_user_role(user):
    """Adapt this to your Pulse user system"""
    
    # Option 1: Check user.role attribute
    if hasattr(user, 'role'):
        return user.role
    
    # Option 2: Check profile
    if hasattr(user, 'profile'):
        if user.profile.is_legal_admin:
            return Roles.LEGAL_ADMIN
        # ... etc
    
    # Option 3: Check custom permission system
    if user.has_perm('contracts.admin'):
        return Roles.LEGAL_ADMIN
    
    return Roles.USER
```

### Integrating with Existing Department Model

If Pulse has an existing Department model:

```python
# contracts/models.py - Change this:
bu_team = models.ForeignKey(
    'contracts.Department',  # Current
    ...
)

# To this:
bu_team = models.ForeignKey(
    'pulse_core.Department',  # Your existing model
    ...
)
```

### User Department Integration

If your User model has a `department` field, the module will automatically use it for:
- Department-based visibility
- Department-based sharing

---

## Important Notes

### ⚠️ Production Checklist

Before deploying to production:

- [ ] **Remove MockUserMiddleware** from `MIDDLEWARE` in settings.py
- [ ] **Configure proper authentication** (LOGIN_URL, etc.)
- [ ] **Set up Django groups** (Legal Admin, Legal User, Finance Viewer)
- [ ] **Assign users to appropriate groups**
- [ ] **Configure media file storage** (consider S3 for production)
- [ ] **Set DEBUG = False**
- [ ] **Configure ALLOWED_HOSTS**
- [ ] **Run collectstatic** for static files

### File Upload Limits

Default allowed extensions:
- Documents: `pdf, doc, docx, xlsx, xls, ppt, pptx, txt`
- Images: `jpg, jpeg, png`

To modify, edit `ContractFile` model in `contracts/models.py`.

### Audit Logging

All significant actions are automatically logged to `AuditLog`:
- Contract CRUD operations
- Status changes
- File uploads/downloads
- Approval actions
- Sharing changes

### Base Template Requirement

The module extends a `base.html` template. Ensure it includes:
- Bootstrap 5 CSS
- Bootstrap Icons CSS
- Bootstrap 5 JS
- `{% block content %}` block
- `{% block extra_css %}` block
- `{% block extra_js %}` block

---

## Customization Guide

### Changing Colors/Theme

Edit `static/contracts/css/contracts.css`:

```css
:root {
    --primary: #059669;        /* Main brand color */
    --primary-light: #ecfdf5;  /* Light variant */
    /* ... other variables */
}
```

### Adding Contract Categories

Edit `contracts/models.py`:

```python
class Category(models.TextChoices):
    SALES = 'SALES', 'Sales'
    # Add your categories here
    NEW_CATEGORY = 'NEW_CAT', 'New Category Name'
```

Then run migrations.

### Adding Custom Fields

1. Add field to `Contract` model in `models.py`
2. Create migration: `python manage.py makemigrations`
3. Apply migration: `python manage.py migrate`
4. Add to forms in `forms.py`
5. Add to templates as needed

---

## Support Contacts

For integration questions, contact your development team.

**Module Files Location:** `contracts/`  
**Templates Location:** `templates/contracts/`  
**Static Files Location:** `static/contracts/`

---

## Quick Start Summary

```bash
# 1. Add 'contracts' to INSTALLED_APPS

# 2. Add URL pattern
path('contracts/', include('contracts.urls')),

# 3. Run migrations
python manage.py migrate

# 4. Create groups
python manage.py shell
>>> from django.contrib.auth.models import Group
>>> Group.objects.create(name='Legal Admin')
>>> Group.objects.create(name='Legal User')
>>> Group.objects.create(name='Finance Viewer')

# 5. Remove MockUserMiddleware from settings.py

# 6. Assign users to groups via Django Admin

# 7. Done! Access at /contracts/
```
