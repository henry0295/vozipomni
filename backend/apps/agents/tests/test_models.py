"""
Tests for Agent models
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.agents.models import Agent, AgentStatusHistory, AgentBreakReason

User = get_user_model()


class AgentModelTest(TestCase):
    """Test Agent model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='agent1',
            email='agent1@example.com',
            password='testpass123',
            role='agent'
        )
        
        self.agent = Agent.objects.create(
            user=self.user,
            agent_id='AGT001',
            sip_extension='1001',
            status='offline'
        )
    
    def test_agent_creation(self):
        """Test agent is created correctly"""
        self.assertEqual(self.agent.agent_id, 'AGT001')
        self.assertEqual(self.agent.sip_extension, '1001')
        self.assertEqual(self.agent.status, 'offline')
    
    def test_agent_str(self):
        """Test agent string representation"""
        expected = f"{self.user.get_full_name()} - {self.agent.sip_extension}"
        self.assertEqual(str(self.agent), expected)
    
    def test_agent_login(self):
        """Test agent login"""
        self.agent.login()
        
        self.assertEqual(self.agent.status, 'available')
        self.assertIsNotNone(self.agent.logged_in_at)
    
    def test_agent_logout(self):
        """Test agent logout"""
        self.agent.login()
        self.agent.logout()
        
        self.assertEqual(self.agent.status, 'offline')
        self.assertIsNone(self.agent.logged_in_at)
        self.assertEqual(self.agent.current_calls, 0)
    
    def test_is_available_property(self):
        """Test is_available property"""
        self.agent.status = 'available'
        self.agent.current_calls = 0
        self.agent.max_concurrent_calls = 1
        self.agent.save()
        
        self.assertTrue(self.agent.is_available)
        
        # Not available when busy
        self.agent.status = 'busy'
        self.agent.save()
        self.assertFalse(self.agent.is_available)
        
        # Not available when at max calls
        self.agent.status = 'available'
        self.agent.current_calls = 1
        self.agent.save()
        self.assertFalse(self.agent.is_available)
    
    def test_session_duration(self):
        """Test session duration calculation"""
        # Not logged in
        self.assertEqual(self.agent.session_duration, 0)
        
        # Logged in
        self.agent.logged_in_at = timezone.now() - timedelta(hours=2)
        self.agent.save()
        
        duration = self.agent.session_duration
        self.assertGreater(duration, 7000)  # ~2 hours in seconds
        self.assertLess(duration, 7300)
    
    def test_occupancy_calculation(self):
        """Test occupancy percentage calculation"""
        self.agent.logged_in_at = timezone.now() - timedelta(hours=1)
        self.agent.oncall_time_today = 1800  # 30 minutes
        self.agent.talk_time_today = 900  # 15 minutes
        self.agent.wrapup_time_today = 300  # 5 minutes
        self.agent.save()
        
        # Total productive: 50 minutes out of 60 = 83.3%
        occupancy = self.agent.occupancy
        self.assertGreater(occupancy, 80)
        self.assertLess(occupancy, 90)


class AgentStatusHistoryModelTest(TestCase):
    """Test AgentStatusHistory model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='agent1',
            email='agent1@example.com',
            password='testpass123'
        )
        
        self.agent = Agent.objects.create(
            user=self.user,
            agent_id='AGT001',
            sip_extension='1001'
        )
        
        self.history = AgentStatusHistory.objects.create(
            agent=self.agent,
            status='available',
            started_at=timezone.now() - timedelta(minutes=30)
        )
    
    def test_history_creation(self):
        """Test history record is created"""
        self.assertEqual(self.history.agent, self.agent)
        self.assertEqual(self.history.status, 'available')
        self.assertIsNone(self.history.ended_at)
    
    def test_history_str(self):
        """Test history string representation"""
        result = str(self.history)
        self.assertIn(self.agent.user.username, result)
        self.assertIn('available', result)


class AgentBreakReasonModelTest(TestCase):
    """Test AgentBreakReason model"""
    
    def test_break_reason_creation(self):
        """Test break reason is created"""
        reason = AgentBreakReason.objects.create(
            name='Almuerzo',
            code='LUNCH',
            is_paid=True,
            max_duration=60
        )
        
        self.assertEqual(reason.name, 'Almuerzo')
        self.assertEqual(reason.code, 'LUNCH')
        self.assertTrue(reason.is_paid)
        self.assertEqual(reason.max_duration, 60)
    
    def test_break_reason_str(self):
        """Test break reason string representation"""
        reason = AgentBreakReason.objects.create(
            name='Almuerzo',
            code='LUNCH'
        )
        
        self.assertEqual(str(reason), 'Almuerzo')
