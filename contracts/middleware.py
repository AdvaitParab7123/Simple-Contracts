"""
Middleware for Contract Management module.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser


class MockUserMiddleware:
    """
    Middleware to provide a mock authenticated user for demo purposes.
    Remove this in production and use proper authentication.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._mock_user = None
    
    def __call__(self, request):
        # Create or get a mock user for demo
        if not request.user.is_authenticated:
            request.user = self.get_mock_user()
        
        response = self.get_response(request)
        return response
    
    def get_mock_user(self):
        if self._mock_user is None:
            User = get_user_model()
            # Try to get existing demo user or create one
            self._mock_user, created = User.objects.get_or_create(
                username='demo_user',
                defaults={
                    'email': 'demo@netcore.com',
                    'first_name': 'Demo',
                    'last_name': 'User',
                    'is_staff': True,  # Give admin access for demo
                    'is_superuser': True,
                }
            )
        return self._mock_user

