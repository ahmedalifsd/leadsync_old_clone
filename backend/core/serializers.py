from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Lead, Category, Source, OwnerCategory, OwnerSource, ActivityLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser']
        read_only_fields = ['id']


class UserDetailSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'profile']
        read_only_fields = ['id']
    
    def get_profile(self, obj):
        from accounts.serializers import UserProfileSerializer
        if hasattr(obj, 'profile'):
            return UserProfileSerializer(obj.profile).data
        return None


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class OwnerCategorySerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = OwnerCategory
        fields = ['id', 'owner', 'owner_username', 'name', 'created_at']
        read_only_fields = ['id', 'created_at', 'owner']


class OwnerSourceSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = OwnerSource
        fields = ['id', 'owner', 'owner_username', 'name', 'created_at']
        read_only_fields = ['id', 'created_at', 'owner']


class LeadListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    source_name = serializers.CharField(source='source.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'owner', 'owner_name', 'created_by', 'created_by_name',
            'category', 'category_name', 'source', 'source_name',
            'client_name', 'contact_number', 'email', 'status',
            'follow_up_date', 'assigned_to', 'assigned_to_name',
            'lead_score', 'converted_to_customer', 'created_at', 'updated_at',
            'deleted_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeadDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, allow_null=True)
    deleted_by_name = serializers.CharField(source='deleted_by.get_full_name', read_only=True, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    source_name = serializers.CharField(source='source.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'owner', 'owner_name', 'created_by', 'created_by_name',
            'category', 'category_name', 'category_other', 'source', 'source_name', 'source_other',
            'client_name', 'contact_number', 'email', 'requirement', 'status',
            'follow_up_date', 'notes', 'assigned_to', 'assigned_to_name',
            'lead_score', 'budget', 'timeline', 'decision_maker',
            'converted_to_customer', 'conversion_date', 'contact_attempts',
            'status_repeat_count', 'custom_fields',
            'created_at', 'updated_at', 'deleted_by', 'deleted_by_name', 'deleted_at',
            'assignment_date'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'deleted_at']


class LeadCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'owner', 'category', 'category_other', 'source', 'source_other',
            'client_name', 'contact_number', 'email', 'requirement', 'status',
            'follow_up_date', 'notes', 'assigned_to',
            'lead_score', 'budget', 'timeline', 'decision_maker',
            'converted_to_customer', 'custom_fields'
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'user_name', 'action', 'target_model',
            'target_id', 'target_name', 'details', 'ip_address',
            'user_agent', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
