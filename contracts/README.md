# Contract Management Module for Netcore Pulse

A Django 4.x Contract Management / Contract Repository module designed to replace SimpliContract.

## Features

- **Dashboard**: Overview of contracts pending action, expiring contracts, approvals, and key metrics
- **Contract Repository**: Full CRUD with tabs (Draft, Pending, Repository), search, and filtering
- **New Contract Wizard**: Multi-step form for creating contracts with file uploads
- **Contract Detail View**: Document viewer, key information, clauses, deviations, risks, signatures
- **Additional Approvals**: Request and manage approval workflows
- **Clause Playbook**: Pre-approved clause library for quick insertion
- **Role-based Access Control**: LEGAL_ADMIN, LEGAL_USER, FINANCE_VIEWER, USER roles
- **Audit Logging**: Complete activity tracking for compliance

## Installation

### 1. Add to INSTALLED_APPS

In your `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'contracts',
]
```

### 2. Configure URLs

In your main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other urls
    path('contracts/', include('contracts.urls')),
]
```

### 3. Configure Media Files

Ensure your `settings.py` has media file configuration:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

And in development, add to `urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### 4. Run Migrations

```bash
python manage.py makemigrations contracts
python manage.py migrate
```

### 5. Create Base Template

The module extends a `base.html` template. Ensure your Pulse project has this template with:

- Bootstrap 5 CSS/JS included
- A `{% block content %}` block
- A `{% block extra_css %}` block
- A `{% block extra_js %}` block

Example minimal `base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netcore Pulse</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Your navigation bar here -->
    
    {% block content %}{% endblock %}
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

## Role Configuration

### Option 1: User Groups (Recommended)

Create Django groups with these names:
- `Legal Admin` or `legal_admin` - Full access
- `Legal User` or `legal_user` - Create/edit contracts
- `Finance Viewer` or `finance_viewer` - Read-only access

### Option 2: User Role Field

Add a `role` field to your User model:

```python
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('LEGAL_ADMIN', 'Legal Admin'),
        ('LEGAL_USER', 'Legal User'),
        ('FINANCE_VIEWER', 'Finance Viewer'),
        ('USER', 'User'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='USER')
```

### Option 3: Adapt permissions.py

Edit `contracts/permissions.py` to match your existing role system:

```python
def get_user_role(user):
    # Adapt to your role system
    if user.profile.is_legal_admin:
        return Roles.LEGAL_ADMIN
    # ... etc
```

## Department Integration

If you have an existing Department/Team model, you can:

1. Modify `contracts/models.py` to use your model:

```python
from your_app.models import YourDepartment

class Contract(models.Model):
    bu_team = models.ForeignKey(
        'your_app.YourDepartment',  # Point to your model
        on_delete=models.SET_NULL,
        null=True,
        related_name='contracts'
    )
```

2. Or create a data migration to sync departments.

## User Integration

The module uses `settings.AUTH_USER_MODEL` for user references, so it will work with custom User models.

If your user model has a `department` field, update the permission checks in `permissions.py`:

```python
if hasattr(user, 'department') and user.department:
    # Department-based access checks
```

## URL Structure

| URL | View | Description |
|-----|------|-------------|
| `/contracts/` | Dashboard | Main dashboard |
| `/contracts/list/` | Contract List | List with tabs |
| `/contracts/new/` | Create Wizard | Multi-step creation |
| `/contracts/<uuid>/` | Contract Detail | Full contract view |
| `/contracts/<uuid>/edit/` | Contract Edit | Edit form |
| `/contracts/approvals/` | Approvals List | Approval requests |
| `/contracts/configurations/` | Configurations | Manage types, tags, departments, clauses |

## Customization

### Styling

The module uses CSS variables for theming. Override in your base template:

```css
:root {
    --contracts-primary: #your-brand-color;
    --contracts-accent: #your-accent-color;
}
```

### Categories

Edit the `Category` choices in `contracts/models.py`:

```python
class Category(models.TextChoices):
    SALES = 'SALES', 'Sales'
    # Add your categories
```

### File Storage

Configure Django's file storage backend in `settings.py` for production:

```python
# For AWS S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'your-bucket'
```

## Testing

Run the test suite:

```bash
python manage.py test contracts
```

## Support

For issues or customization requests, contact your development team.

## License

Internal use only - Netcore Pulse

