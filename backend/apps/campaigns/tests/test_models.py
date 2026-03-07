"""
Tests for Campaign models
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.campaigns.models import Campaign, CampaignDisposition
from apps.contacts.models import ContactList
from apps.queues.models import Queue

User = get_user_model()


class CampaignModelTest(TestCase):
    """Test Campaign model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.queue = Queue.objects.create(
            name='Test Queue',
            extension='8000',
            strategy='ringall'
        )
        
        self.contact_list = ContactList.objects.create(
            name='Test Contacts',
            created_by=self.user
        )
        
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            description='Test description',
            campaign_type='outbound',
            dialer_type='progressive',
            status='draft',
            start_date=timezone.now(),
            queue=self.queue,
            contact_list=self.contact_list,
            created_by=self.user
        )
    
    def test_campaign_creation(self):
        """Test campaign is created correctly"""
        self.assertEqual(self.campaign.name, 'Test Campaign')
        self.assertEqual(self.campaign.campaign_type, 'outbound')
        self.assertEqual(self.campaign.status, 'draft')
        self.assertIsNotNone(self.campaign.created_at)
    
    def test_campaign_str(self):
        """Test campaign string representation"""
        expected = f"{self.campaign.name} (Saliente)"
        self.assertEqual(str(self.campaign), expected)
    
    def test_success_rate_calculation(self):
        """Test success rate property"""
        self.campaign.contacted = 100
        self.campaign.successful = 75
        self.campaign.save()
        
        self.assertEqual(self.campaign.success_rate, 75.0)
    
    def test_success_rate_zero_contacted(self):
        """Test success rate when no contacts"""
        self.campaign.contacted = 0
        self.campaign.successful = 0
        self.campaign.save()
        
        self.assertEqual(self.campaign.success_rate, 0)
    
    def test_campaign_unique_name(self):
        """Test campaign name must be unique"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            Campaign.objects.create(
                name='Test Campaign',  # Duplicate name
                campaign_type='inbound',
                start_date=timezone.now(),
                created_by=self.user
            )


class CampaignDispositionModelTest(TestCase):
    """Test CampaignDisposition model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            campaign_type='outbound',
            start_date=timezone.now(),
            created_by=self.user
        )
        
        self.disposition = CampaignDisposition.objects.create(
            campaign=self.campaign,
            code='SALE',
            name='Venta Exitosa',
            description='Cliente realizó compra',
            is_success=True,
            order=1
        )
    
    def test_disposition_creation(self):
        """Test disposition is created correctly"""
        self.assertEqual(self.disposition.code, 'SALE')
        self.assertEqual(self.disposition.name, 'Venta Exitosa')
        self.assertTrue(self.disposition.is_success)
    
    def test_disposition_str(self):
        """Test disposition string representation"""
        expected = f"{self.campaign.name} - {self.disposition.name}"
        self.assertEqual(str(self.disposition), expected)
    
    def test_disposition_unique_code_per_campaign(self):
        """Test disposition code must be unique per campaign"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            CampaignDisposition.objects.create(
                campaign=self.campaign,
                code='SALE',  # Duplicate code
                name='Another Sale',
                order=2
            )
    
    def test_disposition_ordering(self):
        """Test dispositions are ordered correctly"""
        CampaignDisposition.objects.create(
            campaign=self.campaign,
            code='NO_ANSWER',
            name='No Contesta',
            order=3
        )
        
        CampaignDisposition.objects.create(
            campaign=self.campaign,
            code='CALLBACK',
            name='Rellamada',
            order=2
        )
        
        dispositions = CampaignDisposition.objects.filter(campaign=self.campaign)
        self.assertEqual(dispositions[0].order, 1)
        self.assertEqual(dispositions[1].order, 2)
        self.assertEqual(dispositions[2].order, 3)
