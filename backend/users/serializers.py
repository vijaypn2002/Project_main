from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Address

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_username(self, v):
        return v.strip()

    def validate_email(self, v):
        return (v or "").strip().lower()

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_staff", "is_superuser"]
        read_only_fields = ["is_staff", "is_superuser"]

    def validate_email(self, v):
        return (v or "").strip().lower()

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ["user", "created_at", "updated_at", "id"]

    def validate_country(self, v):
        return (v or "IN").strip().upper()[:2]
