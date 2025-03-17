from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class FarmerRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict view access to farmers only"""
    
    def test_func(self):
        return self.request.user.is_farmer
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Only farmers can access this page.")
        return super().handle_no_permission()
