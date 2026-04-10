"""REST API views for accounts."""
from rest_framework import generics, permissions

from .models import User
from .serializers import UserProfileSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """Return or update the authenticated user's own profile."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
