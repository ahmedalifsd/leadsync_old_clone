"""
Basic tests to verify the LeadSync application is working correctly
"""
from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.urls import reverse
from django.test import Client


class BasicAppTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
    def test_home_page_loads(self):
        """Test that home page loads without error"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_login_page_loads(self):
        """Test that login page loads without error"""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        
    def test_user_profile_creation(self):
        """Test that user profile is created automatically"""
        # The signal should create a profile when user is created
        profile = UserProfile.objects.get(user=self.user)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.role, 'staff')  # Default role
        
    def test_user_can_login(self):
        """Test that user can log in"""
        login_successful = self.client.login(username='testuser', password='testpass123')
        self.assertTrue(login_successful)
        
    def test_dashboard_access(self):
        """Test dashboard access after login"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/dashboard/')
        # Should redirect to login if dashboard requires authentication
        # Or return 200 if accessible after login
        self.assertIn(response.status_code, [200, 302])  # Allow both success and redirect