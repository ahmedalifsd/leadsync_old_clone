from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Plan
from .serializers import PlanSerializer


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for retrieving Plan information.
    - GET /api/plans/ - List all active plans
    - GET /api/plans/{id}/ - Get plan details
    
    No authentication required for public plan listings.
    """
    queryset = Plan.objects.filter(is_active=True).order_by('monthly_price')
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]  # Public endpoint
    
    def get_queryset(self):
        """Return only active plans"""
        return Plan.objects.filter(is_active=True).order_by('monthly_price')

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def active(self, request):
        """Get all active plans with pricing"""
        plans = self.get_queryset()
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def default(self, request):
        """Get the default signup plan"""
        plan = Plan.objects.filter(is_default_signup_plan=True, is_active=True).first()
        if not plan:
            return Response(
                {'error': 'No default plan configured'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(plan)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def user_subscription(self, request, pk=None):
        """Get user's subscription for a specific plan (requires auth)"""
        plan = self.get_object()
        # This is a placeholder - actual subscription logic would go here
        return Response({
            'plan': self.get_serializer(plan).data,
            'user_has_subscription': False,
            'subscription_expires': None,
        })
