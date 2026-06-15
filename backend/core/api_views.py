from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.utils import timezone
from .models import Lead, Category, Source, OwnerCategory, OwnerSource, ActivityLog
from .serializers import (
    LeadListSerializer, LeadDetailSerializer, LeadCreateUpdateSerializer,
    CategorySerializer, SourceSerializer, OwnerCategorySerializer,
    OwnerSourceSerializer, ActivityLogSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['client_name', 'email', 'contact_number']
    ordering_fields = ['created_at', 'client_name', 'status', 'lead_score']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        # Filter leads where user is owner or created_by
        queryset = Lead.objects.filter(Q(owner=user) | Q(created_by=user)).exclude(deleted_at__isnull=False)
        
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by category if provided
        category_param = self.request.query_params.get('category')
        if category_param:
            queryset = queryset.filter(category_id=category_param)
        
        # Filter by source if provided
        source_param = self.request.query_params.get('source')
        if source_param:
            queryset = queryset.filter(source_id=source_param)
        
        # Filter by assigned_to if provided
        assigned_param = self.request.query_params.get('assigned_to')
        if assigned_param:
            queryset = queryset.filter(assigned_to_id=assigned_param)
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LeadDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return LeadCreateUpdateSerializer
        return LeadListSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(owner=user, created_by=user)
        # Log activity
        lead = serializer.instance
        ActivityLog.objects.create(
            user=user,
            action='create',
            target_model='Lead',
            target_id=lead.id,
            target_name=lead.client_name
        )

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save()
        # Log activity
        lead = serializer.instance
        ActivityLog.objects.create(
            user=user,
            action='update',
            target_model='Lead',
            target_id=lead.id,
            target_name=lead.client_name
        )

    def perform_destroy(self, instance):
        user = self.request.user
        instance.deleted_by = user
        instance.deleted_at = timezone.now()
        instance.save()
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action='delete',
            target_model='Lead',
            target_id=instance.id,
            target_name=instance.client_name
        )

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        lead = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Lead.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        lead.status = new_status
        lead.status_repeat_count += 1
        lead.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='update',
            target_model='Lead',
            target_id=lead.id,
            target_name=f"{lead.client_name} - Status changed to {new_status}"
        )
        
        return Response(LeadDetailSerializer(lead).data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        lead = self.get_object()
        assigned_to_id = request.data.get('assigned_to_id')
        
        if assigned_to_id:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(id=assigned_to_id)
                lead.assigned_to = user
                lead.assignment_date = timezone.now()
                lead.save()
                
                ActivityLog.objects.create(
                    user=request.user,
                    action='update',
                    target_model='Lead',
                    target_id=lead.id,
                    target_name=f"{lead.client_name} - Assigned to {user.get_full_name()}"
                )
                
                return Response(LeadDetailSerializer(lead).data)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'error': 'assigned_to_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def deleted_leads(self, request):
        """Get soft-deleted leads"""
        user = request.user
        queryset = Lead.objects.filter(
            Q(owner=user) | Q(created_by=user),
            deleted_at__isnull=False
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = LeadListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = LeadListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted lead"""
        lead = Lead.objects.filter(deleted_at__isnull=False).get(pk=pk)
        lead.deleted_at = None
        lead.deleted_by = None
        lead.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='update',
            target_model='Lead',
            target_id=lead.id,
            target_name=f"{lead.client_name} - Restored"
        )
        
        return Response(LeadDetailSerializer(lead).data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    permission_classes = [IsAuthenticated]


class OwnerCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = OwnerCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OwnerCategory.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class OwnerSourceViewSet(viewsets.ModelViewSet):
    serializer_class = OwnerSourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OwnerSource.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    ordering_fields = ['-timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        user = self.request.user
        return ActivityLog.objects.filter(user=user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics for the current user"""
    user = request.user
    
    leads = Lead.objects.filter(Q(owner=user) | Q(created_by=user)).exclude(deleted_at__isnull=False)
    
    stats = {
        'total_leads': leads.count(),
        'new_leads': leads.filter(status='new').count(),
        'contacted': leads.filter(status='contacted').count(),
        'interested': leads.filter(status='interested').count(),
        'qualified': leads.filter(status='qualified').count(),
        'won': leads.filter(status='won').count(),
        'lost': leads.filter(status='lost').count(),
        'conversion_rate': round(
            (leads.filter(converted_to_customer=True).count() / leads.count() * 100)
            if leads.count() > 0 else 0,
            2
        ),
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lead_status_distribution(request):
    """Get lead distribution by status"""
    user = request.user
    leads = Lead.objects.filter(Q(owner=user) | Q(created_by=user)).exclude(deleted_at__isnull=False)
    
    distribution = {}
    for status, label in Lead.STATUS_CHOICES:
        distribution[status] = {
            'label': label,
            'count': leads.filter(status=status).count()
        }
    
    return Response(distribution)
