"""
Base factory configuration for VoziPOmni Contact Center tests.

This module provides:
- Base factory configuration with Spanish locale
- Abstract factories for common model patterns
- Reusable factory mixins and traits
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker
import uuid
from django.utils import timezone


# Configure Faker with Spanish locale for realistic test data
fake = Faker('es_ES')


class BaseFactory(DjangoModelFactory):
    """
    Base factory class for all model factories.
    
    Provides common configuration and utilities for all factories.
    All model factories should inherit from this class.
    """
    
    class Meta:
        abstract = True
        # Skip creating related objects by default (use SubFactory explicitly)
        skip_postgeneration_save = False
    
    @classmethod
    def _setup_next_sequence(cls):
        """Reset sequence to avoid conflicts in tests."""
        return 0


class TimestampedModelFactory(BaseFactory):
    """
    Abstract factory for models with created_at and updated_at fields.
    
    Provides automatic timestamp generation for models that track
    creation and modification times.
    
    Usage:
        class MyCampaignFactory(TimestampedModelFactory):
            class Meta:
                model = Campaign
    """
    
    class Meta:
        abstract = True
    
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class UUIDModelFactory(BaseFactory):
    """
    Abstract factory for models with UUID primary keys.
    
    Generates unique UUIDs for models that use UUID as primary key.
    
    Usage:
        class MyModelFactory(UUIDModelFactory):
            class Meta:
                model = MyModel
    """
    
    class Meta:
        abstract = True
    
    id = factory.LazyFunction(uuid.uuid4)


class TimestampedUUIDModelFactory(TimestampedModelFactory, UUIDModelFactory):
    """
    Abstract factory combining timestamps and UUID.
    
    For models that have both UUID primary keys and timestamp fields.
    
    Usage:
        class MyModelFactory(TimestampedUUIDModelFactory):
            class Meta:
                model = MyModel
    """
    
    class Meta:
        abstract = True


# ============================================================================
# Factory Mixins
# ============================================================================

class SpanishPersonMixin:
    """
    Mixin for generating Spanish person data.
    
    Provides realistic Spanish names, addresses, and contact information.
    """
    
    first_name = factory.LazyFunction(lambda: fake.first_name())
    last_name = factory.LazyFunction(lambda: fake.last_name())
    email = factory.LazyAttribute(
        lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@{fake.free_email_domain()}"
    )
    phone = factory.LazyFunction(lambda: fake.phone_number())


class AddressMixin:
    """
    Mixin for generating Spanish address data.
    
    Provides realistic Colombian addresses.
    """
    
    address = factory.LazyFunction(lambda: fake.street_address())
    city = factory.LazyFunction(lambda: fake.city())
    state = factory.LazyFunction(lambda: fake.state())
    postal_code = factory.LazyFunction(lambda: fake.postcode())
    country = 'Colombia'


# ============================================================================
# Common Faker Providers
# ============================================================================

class SpanishFakerProvider:
    """
    Custom Faker provider for VoziPOmni-specific data.
    
    Provides domain-specific fake data generation for contact center
    entities like campaign names, queue names, etc.
    """
    
    @staticmethod
    def campaign_name():
        """Generate a realistic campaign name."""
        prefixes = ['Campaña', 'Promoción', 'Oferta', 'Venta', 'Encuesta']
        subjects = ['Verano', 'Navidad', 'Aniversario', 'Especial', 'Premium']
        years = ['2024', '2025', '2026']
        return f"{fake.random_element(prefixes)} {fake.random_element(subjects)} {fake.random_element(years)}"
    
    @staticmethod
    def queue_name():
        """Generate a realistic queue name."""
        types = ['Ventas', 'Soporte', 'Atención', 'Técnico', 'Comercial']
        levels = ['Nivel 1', 'Nivel 2', 'Premium', 'VIP', 'General']
        return f"{fake.random_element(types)} - {fake.random_element(levels)}"
    
    @staticmethod
    def extension_number():
        """Generate a realistic extension number (1000-9999)."""
        return str(fake.random_int(min=1000, max=9999))
    
    @staticmethod
    def sip_username():
        """Generate a realistic SIP username."""
        return f"sip{fake.random_int(min=1000, max=9999)}"
    
    @staticmethod
    def trunk_name():
        """Generate a realistic trunk name."""
        providers = ['Claro', 'Movistar', 'Tigo', 'ETB', 'WOM']
        types = ['Principal', 'Backup', 'Emergencia', 'Internacional']
        return f"{fake.random_element(providers)} {fake.random_element(types)}"
    
    @staticmethod
    def ivr_name():
        """Generate a realistic IVR name."""
        purposes = ['Menú Principal', 'Atención Cliente', 'Ventas', 'Soporte', 'Encuesta']
        return fake.random_element(purposes)
    
    @staticmethod
    def colombian_phone():
        """Generate a realistic Colombian phone number."""
        # Colombian mobile: +57 3XX XXX XXXX
        area_codes = ['300', '301', '302', '310', '311', '312', '313', '314', '315', '316', '317', '318', '319', '320', '321', '322', '323', '350', '351']
        area = fake.random_element(area_codes)
        number = fake.numerify('### ####')
        return f"+57 {area} {number}"
    
    @staticmethod
    def did_number():
        """Generate a realistic DID number."""
        # Colombian landline format
        city_codes = ['601', '602', '604', '605']  # Bogotá, Cali, Medellín, Barranquilla
        city = fake.random_element(city_codes)
        number = fake.numerify('#######')
        return f"+57 {city} {number}"


# Register custom provider
fake.add_provider(SpanishFakerProvider)


# ============================================================================
# Sequence Generators
# ============================================================================

def sequence_generator(prefix: str = '', start: int = 1):
    """
    Create a sequence generator for unique values.
    
    Args:
        prefix: Prefix for generated values
        start: Starting number
        
    Returns:
        Function that generates sequential values
        
    Usage:
        extension_seq = sequence_generator('ext', 1000)
        extension = factory.LazyFunction(extension_seq)
    """
    counter = start - 1
    
    def generate():
        nonlocal counter
        counter += 1
        return f"{prefix}{counter}" if prefix else str(counter)
    
    return generate


# ============================================================================
# Common Traits
# ============================================================================

class ActiveTrait:
    """Trait for active/enabled entities."""
    is_active = True
    status = 'active'


class InactiveTrait:
    """Trait for inactive/disabled entities."""
    is_active = False
    status = 'inactive'


class DraftTrait:
    """Trait for draft entities."""
    status = 'draft'


class ArchivedTrait:
    """Trait for archived entities."""
    status = 'archived'
    is_active = False


# ============================================================================
# Utility Functions
# ============================================================================

def build_batch(factory_class, size: int, **kwargs):
    """
    Build multiple factory instances without saving to database.
    
    Args:
        factory_class: Factory class to use
        size: Number of instances to build
        **kwargs: Additional factory parameters
        
    Returns:
        List of built instances (not saved)
    """
    return factory_class.build_batch(size, **kwargs)


def create_batch(factory_class, size: int, **kwargs):
    """
    Create and save multiple factory instances to database.
    
    Args:
        factory_class: Factory class to use
        size: Number of instances to create
        **kwargs: Additional factory parameters
        
    Returns:
        List of created instances (saved to database)
    """
    return factory_class.create_batch(size, **kwargs)


def stub_batch(factory_class, size: int, **kwargs):
    """
    Create stub instances (no database interaction).
    
    Args:
        factory_class: Factory class to use
        size: Number of stubs to create
        **kwargs: Additional factory parameters
        
    Returns:
        List of stub instances
    """
    return factory_class.stub_batch(size, **kwargs)


# ============================================================================
# Example Usage Documentation
# ============================================================================

"""
Example usage of base factories:

1. Simple model factory:
    
    class CampaignFactory(TimestampedModelFactory):
        class Meta:
            model = Campaign
        
        name = factory.LazyFunction(fake.campaign_name)
        status = 'draft'

2. Factory with relationships:
    
    class CallFactory(BaseFactory):
        class Meta:
            model = Call
        
        agent = factory.SubFactory(AgentFactory)
        campaign = factory.SubFactory(CampaignFactory)

3. Factory with traits:
    
    class UserFactory(BaseFactory):
        class Meta:
            model = User
        
        email = factory.Sequence(lambda n: f'user{n}@vozipomni.com')
        
        class Params:
            active = factory.Trait(is_active=True)
            inactive = factory.Trait(is_active=False)
    
    # Usage:
    active_user = UserFactory(active=True)
    inactive_user = UserFactory(inactive=True)

4. Factory with post-generation:
    
    class CampaignFactory(BaseFactory):
        class Meta:
            model = Campaign
        
        @factory.post_generation
        def contacts(self, create, extracted, **kwargs):
            if not create:
                return
            
            if extracted:
                for contact in extracted:
                    self.contacts.add(contact)

5. Using Spanish data:
    
    class ContactFactory(SpanishPersonMixin, BaseFactory):
        class Meta:
            model = Contact
        
        # first_name, last_name, email, phone inherited from mixin
        company = factory.LazyFunction(lambda: fake.company())
"""
