from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.validators import ValidationError
from .models import User

class SignUpSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=45)
    password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "password", "department", "employee_id"]

    def validate_email(self, value):
        allowed_domains = ['yourdomain.com', 'anotherdomain.com', 'example.com','tedtodd.co.uk']  # Add allowed domains
        domain = value.split('@')[1]

        if domain not in allowed_domains:
            raise serializers.ValidationError('Email domain not allowed for registration.')

        return value

    def validate(self, attrs):
        email_exists = User.objects.filter(email=attrs["email"]).exists()

        if email_exists:
            raise ValidationError("Email has already been used")

        return super().validate(attrs)

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = super().create(validated_data)

        user.set_password(password)
        user.save()

        Token.objects.create(user=user)

        return user
