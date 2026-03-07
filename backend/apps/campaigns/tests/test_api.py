"""
Tests for Campaign API endpoints
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.campaigns.models import Campaign
from apps.contacts.models import ContactList

User = get_user_model()


class CampaignAPITest(TestCase):
    """Test Campaign API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='admin'
        )
        
        self.client.force_authenticate(user=self.user)
        
        self.contact_list = ContactList.objects.create(
            name='Test Contacts',
            created_by=self.user
        )
        
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            campaign_type='outbound',
            dialer_type='progressive',
            status='draft',
            start_date=timezone.now(),
            contact_list=self.contact_list,
            created_by=self.user
        )
    
    def test_list_campaigns(self):
        """Test listing campaigns"""
        response = self.client.get('/api/campaigns/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_campaign(self):
        """Test creating a campaign"""
        data = {
            'name': 'New Campaign',
            'campaign_type': 'outbound',
            'dialer_type': 'predictive',
            'status': 'draft',
            'start_date': timezone.now().isoformat(),
            'contact_list': self.contact_list.id
        }
        
        response = self.client.post('/api/campaigns/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 2)
    
    def test_retrieve_campaign(self):
        """Test retrieving a single campaign"""
        response = self.client.get(f'/api/campaigns/{self.campaign.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Campaign')
    
    def test_update_campaign(self):
        """Test updating a campaign"""
        data = {
            'name': 'Updated Campaign',
            'campaign_type': 'outbound',
            'start_date': timezone.now().isoformat()
        }
        
        response = self.client.patch(
            f'/api/campaigns/{self.campaign.id}/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, 'Updated Campaign')
    
    def test_start_campaign(self):
        """Test starting a campaign"""
        response = self.client.post(f'/api/campaigns/{self.campaign.id}/start/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'active')
    
    def test_pause_campaign(self):
        """Test pausing a campaign"""
        self.campaign.status = 'active'
        self.campaign.save()
        
        response = self.client.post(f'/api/campaigns/{self.campaign.id}/pause/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'paused')
    
    def test_campaign_stats(self):
        """Test getting campaign statistics"""
        self.campaign.total_contacts = 100
        self.campaign.contacted = 75
        self.campaign.successful = 50
        self.campaign.save()
        
        response = self.client.get(f'/api/campaigns/{self.campaign.id}/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_contacts'], 100)
        self.assertEqual(response.data['contacted'], 75)
        self.assertEqual(response.data['successful'], 50)
        self.assertEqual(response.data['success_rate'], 66.67)
    
    def test_unauthorized_access(self):
        """Test unauthorized access is denied"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/campaigns/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
