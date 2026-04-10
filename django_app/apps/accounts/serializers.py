"""REST API serializers for the accounts app."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "organization", "preferred_mass_unit",
            "active_year", "chatbot_enabled",
        ]
        read_only_fields = ["id", "username", "email"]
