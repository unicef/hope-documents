from rest_framework import serializers

from hope_documents.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email")
