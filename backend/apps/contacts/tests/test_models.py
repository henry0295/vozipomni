"""
Tests for Contact models
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.contacts.models import Contact, ContactList, ContactNote, Blacklist

User = get_user_model()


class ContactListModelTest(TestCase):
    """Test ContactList model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.contact_list = ContactList.objects.create(
            name='Test List',
            description='Test description',
            created_by=self.user
        )
    
    def test_contact_list_creation(self):
        """Test contact list is created correctly"""
        self.assertEqual(self.contact_list.name, 'Test List')
        self.assertEqual(self.contact_list.total_contacts, 0)
        self.assertTrue(self.contact_list.is_active)
    
    def test_contact_list_str(self):
        """Test contact list string representation"""
        expected = f"{self.contact_list.name} (0 contactos)"
        self.assertEqual(str(self.contact_list), expected)


class ContactModelTest(TestCase):
    """Test Contact model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.contact_list = ContactList.objects.create(
            name='Test List',
            created_by=self.user
        )
        
        self.contact = Contact.objects.create(
            contact_list=self.contact_list,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='+573001234567',
            company='Test Company',
            status='new'
        )
    
    def test_contact_creation(self):
        """Test contact is created correctly"""
        self.assertEqual(self.contact.first_name, 'John')
        self.assertEqual(self.contact.last_name, 'Doe')
        self.assertEqual(self.contact.phone, '+573001234567')
        self.assertEqual(self.contact.status, 'new')
    
    def test_contact_str(self):
        """Test contact string representation"""
        expected = "John Doe - +573001234567"
        self.assertEqual(str(self.contact), expected)
    
    def test_full_name_property(self):
        """Test full_name property"""
        self.assertEqual(self.contact.full_name, 'John Doe')
        
        # Test with only first name
        contact2 = Contact.objects.create(
            contact_list=self.contact_list,
            first_name='Jane',
            phone='+573009876543'
        )
        self.assertEqual(contact2.full_name, 'Jane')
    
    def test_validate_phone(self):
        """Test phone validation"""
        # Valid Colombian number
        self.assertTrue(self.contact.validate_phone('+573001234567'))
        
        # Invalid number
        self.assertFalse(self.contact.validate_phone('123'))


class ContactNoteModelTest(TestCase):
    """Test ContactNote model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.contact_list = ContactList.objects.create(
            name='Test List',
            created_by=self.user
        )
        
        self.contact = Contact.objects.create(
            contact_list=self.contact_list,
            first_name='John',
            last_name='Doe',
            phone='+573001234567'
        )
        
        self.note = ContactNote.objects.create(
            contact=self.contact,
            note='Test note',
            created_by=self.user,
            is_important=True
        )
    
    def test_note_creation(self):
        """Test note is created correctly"""
        self.assertEqual(self.note.contact, self.contact)
        self.assertEqual(self.note.note, 'Test note')
        self.assertTrue(self.note.is_important)
    
    def test_note_str(self):
        """Test note string representation"""
        result = str(self.note)
        self.assertIn('John Doe', result)


class BlacklistModelTest(TestCase):
    """Test Blacklist model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.blacklist = Blacklist.objects.create(
            phone='+573001234567',
            reason='Spam',
            added_by=self.user
        )
    
    def test_blacklist_creation(self):
        """Test blacklist entry is created"""
        self.assertEqual(self.blacklist.phone, '+573001234567')
        self.assertEqual(self.blacklist.reason, 'Spam')
        self.assertTrue(self.blacklist.is_active)
    
    def test_blacklist_str(self):
        """Test blacklist string representation"""
        self.assertEqual(str(self.blacklist), '+573001234567')
