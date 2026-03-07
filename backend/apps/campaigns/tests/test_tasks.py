"""
Tests for Campaign tasks
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.campaigns.models import Campaign
from apps.campaigns.tasks import process_pending_calls, update_campaign_statistics
from apps.contacts.models import ContactList

User = get_user_model()


class CampaignTasksTest(TestCase):
    """Test Campaign Celery tasks"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.contact_list = ContactList.objects.create(
            name='Test Contacts',
            total_contacts=100,
            created_by=self.user
        )
        
        self.campaign = Campaign.objects.create(
            name='Active Campaign',
            campaign_type='outbound',
            dialer_type='progressive',
            status='active',
            start_date=timezone.now(),
            contact_list=self.contact_list,
            created_by=self.user
        )
    
    @patch('apps.campaigns.tasks.DialerService')
    def test_process_pending_calls(self, mock_dialer):
        """Test process_pending_calls task"""
        mock_dialer_instance = MagicMock()
        mock_dialer.return_value = mock_dialer_instance
        
        result = process_pending_calls()
        
        self.assertIn('Processed', result)
        mock_dialer.assert_called_once()
        mock_dialer_instance.process_pending_contacts.assert_called_once()
    
    @patch('apps.campaigns.tasks.DialerService')
    def test_process_pending_calls_handles_errors(self, mock_dialer):
        """Test process_pending_calls handles errors gracefully"""
        mock_dialer.side_effect = Exception('Test error')
        
        # Should not raise exception
        result = process_pending_calls()
        self.assertIn('Processed', result)
    
    def test_update_campaign_statistics(self):
        """Test update_campaign_statistics task"""
        result = update_campaign_statistics(self.campaign.id)
        
        self.assertIn('Updated statistics', result)
        
        # Refresh from DB
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.total_contacts, 100)
    
    def test_update_campaign_statistics_not_found(self):
        """Test update_campaign_statistics with non-existent campaign"""
        result = update_campaign_statistics(99999)
        
        self.assertIn('not found', result)
