"""
Helper functions for test data setup and assertions.

This module provides utility functions for:
- Test data generation and setup
- Custom assertions
- Common test operations
- Mock object creation
"""

from typing import Any, Dict, List, Optional
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


# ============================================================================
# Test Data Helpers
# ============================================================================

def create_test_user(email: str = 'test@vozipomni.com', 
                     role: str = 'agent',
                     **kwargs) -> User:
    """
    Create a test user with default values.
    
    Args:
        email: User email address
        role: User role (admin, supervisor, agent, analyst)
        **kwargs: Additional user fields
        
    Returns:
        User: Created user instance
    """
    defaults = {
        'password': 'testpass123',
        'first_name': 'Test',
        'last_name': 'User',
        'is_active': True,
    }
    defaults.update(kwargs)
    
    return User.objects.create_user(
        email=email,
        role=role,
        **defaults
    )


def create_bulk_instances(model_class: type[models.Model],
                         count: int,
                         **base_kwargs) -> List[models.Model]:
    """
    Create multiple model instances efficiently using bulk_create.
    
    Args:
        model_class: Model class to instantiate
        count: Number of instances to create
        **base_kwargs: Base field values (will be used for all instances)
        
    Returns:
        List of created model instances
    """
    instances = []
    for i in range(count):
        kwargs = base_kwargs.copy()
        # Add index to make instances unique if needed
        for key, value in kwargs.items():
            if isinstance(value, str) and '{i}' in value:
                kwargs[key] = value.format(i=i)
        instances.append(model_class(**kwargs))
    
    return model_class.objects.bulk_create(instances)


def refresh_from_db(*instances: models.Model) -> None:
    """
    Refresh multiple model instances from database.
    
    Args:
        *instances: Model instances to refresh
    """
    for instance in instances:
        instance.refresh_from_db()


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_model_fields_equal(instance: models.Model,
                              expected_values: Dict[str, Any]) -> None:
    """
    Assert model instance fields match expected values.
    
    Args:
        instance: Model instance to check
        expected_values: Dict of field_name: expected_value
        
    Raises:
        AssertionError: If any field doesn't match
    """
    for field_name, expected_value in expected_values.items():
        actual_value = getattr(instance, field_name)
        assert actual_value == expected_value, (
            f"Field '{field_name}' mismatch: "
            f"expected {expected_value!r}, got {actual_value!r}"
        )


def assert_queryset_equal(qs1: models.QuerySet,
                         qs2: models.QuerySet,
                         ordered: bool = False) -> None:
    """
    Assert two querysets contain the same objects.
    
    Args:
        qs1: First queryset
        qs2: Second queryset
        ordered: Whether order matters
        
    Raises:
        AssertionError: If querysets don't match
    """
    if ordered:
        list1 = list(qs1)
        list2 = list(qs2)
        assert list1 == list2, f"Querysets don't match (ordered): {list1} != {list2}"
    else:
        set1 = set(qs1)
        set2 = set(qs2)
        assert set1 == set2, f"Querysets don't match (unordered): {set1} != {set2}"


def assert_dict_contains(actual: Dict, expected_subset: Dict) -> None:
    """
    Assert dictionary contains all keys and values from expected subset.
    
    Args:
        actual: Actual dictionary
        expected_subset: Expected subset of keys/values
        
    Raises:
        AssertionError: If any expected key/value is missing or different
    """
    for key, expected_value in expected_subset.items():
        assert key in actual, f"Key '{key}' not found in {actual}"
        actual_value = actual[key]
        assert actual_value == expected_value, (
            f"Value for key '{key}' mismatch: "
            f"expected {expected_value!r}, got {actual_value!r}"
        )


def assert_response_has_keys(response_data: Dict, *keys: str) -> None:
    """
    Assert response data contains all specified keys.
    
    Args:
        response_data: Response data dictionary
        *keys: Keys that should be present
        
    Raises:
        AssertionError: If any key is missing
    """
    for key in keys:
        assert key in response_data, (
            f"Key '{key}' not found in response: {response_data}"
        )


def assert_validation_error(instance: models.Model,
                           expected_field: Optional[str] = None) -> None:
    """
    Assert model instance fails validation.
    
    Args:
        instance: Model instance to validate
        expected_field: Specific field expected to fail (optional)
        
    Raises:
        AssertionError: If validation passes or wrong field fails
    """
    from django.core.exceptions import ValidationError
    
    try:
        instance.full_clean()
        raise AssertionError("Expected ValidationError but validation passed")
    except ValidationError as e:
        if expected_field:
            assert expected_field in e.error_dict, (
                f"Expected validation error on field '{expected_field}', "
                f"but got errors on: {list(e.error_dict.keys())}"
            )


# ============================================================================
# Query Counting Helpers
# ============================================================================

class QueryCounter:
    """
    Context manager for counting database queries.
    
    Usage:
        with QueryCounter() as counter:
            # Code that makes queries
            list(MyModel.objects.all())
        
        assert counter.count <= 5, f"Too many queries: {counter.count}"
    """
    
    def __init__(self):
        self.count = 0
        self.queries = []
    
    def __enter__(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        
        self.context = CaptureQueriesContext(connection)
        self.context.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.context.__exit__(exc_type, exc_val, exc_tb)
        self.count = len(self.context.captured_queries)
        self.queries = self.context.captured_queries
        return False
    
    def assert_max_queries(self, max_count: int) -> None:
        """Assert query count doesn't exceed maximum."""
        assert self.count <= max_count, (
            f"Too many queries: {self.count} > {max_count}\n"
            f"Queries:\n" + "\n".join(q['sql'] for q in self.queries)
        )


def assert_num_queries(num: int):
    """
    Decorator/context manager to assert exact number of queries.
    
    Usage as context manager:
        with assert_num_queries(3):
            # Code that should make exactly 3 queries
            pass
    
    Usage as decorator:
        @assert_num_queries(3)
        def test_something():
            # Test code
            pass
    """
    from django.test import override_settings
    from django.test.utils import CaptureQueriesContext
    from django.db import connection
    
    class AssertNumQueries:
        def __init__(self, num):
            self.num = num
            self.context = None
        
        def __enter__(self):
            self.context = CaptureQueriesContext(connection)
            self.context.__enter__()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.context.__exit__(exc_type, exc_val, exc_tb)
            actual = len(self.context.captured_queries)
            assert actual == self.num, (
                f"Expected {self.num} queries, got {actual}\n"
                f"Queries:\n" + "\n".join(q['sql'] for q in self.context.captured_queries)
            )
            return False
        
        def __call__(self, func):
            def wrapper(*args, **kwargs):
                with self:
                    return func(*args, **kwargs)
            return wrapper
    
    return AssertNumQueries(num)


# ============================================================================
# Mock Helpers
# ============================================================================

def create_mock_ami_response(success: bool = True,
                            message: str = 'Success',
                            **extra_fields) -> Dict[str, Any]:
    """
    Create a mock AMI response dictionary.
    
    Args:
        success: Whether response indicates success
        message: Response message
        **extra_fields: Additional response fields
        
    Returns:
        Dict representing AMI response
    """
    response = {
        'Response': 'Success' if success else 'Error',
        'Message': message,
    }
    response.update(extra_fields)
    return response


def create_mock_redis_client():
    """
    Create a mock Redis client for testing.
    
    Returns:
        Mock object with common Redis methods
    """
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    mock.incr.return_value = 1
    mock.decr.return_value = 0
    mock.expire.return_value = True
    
    return mock


# ============================================================================
# Time Helpers
# ============================================================================

def freeze_time(frozen_time: str):
    """
    Freeze time for testing time-dependent code.
    
    Args:
        frozen_time: Time to freeze at (ISO format string)
        
    Returns:
        Context manager that freezes time
        
    Usage:
        with freeze_time('2024-01-01 12:00:00'):
            # Code that uses current time
            pass
    """
    from unittest.mock import patch
    from datetime import datetime
    
    frozen_dt = datetime.fromisoformat(frozen_time)
    
    class FreezeTime:
        def __enter__(self):
            self.patcher = patch('django.utils.timezone.now', return_value=frozen_dt)
            self.patcher.__enter__()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.patcher.__exit__(exc_type, exc_val, exc_tb)
            return False
    
    return FreezeTime()


# ============================================================================
# File Helpers
# ============================================================================

def create_test_file(filename: str = 'test.txt',
                    content: bytes = b'test content') -> Any:
    """
    Create a test file object for upload testing.
    
    Args:
        filename: Name of the file
        content: File content as bytes
        
    Returns:
        File-like object suitable for testing file uploads
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    return SimpleUploadedFile(filename, content)


def create_test_audio_file(filename: str = 'test.wav',
                          duration_seconds: int = 10) -> Any:
    """
    Create a test audio file for recording testing.
    
    Args:
        filename: Name of the audio file
        duration_seconds: Duration in seconds
        
    Returns:
        File-like object with audio data
    """
    # Create minimal WAV file header + silence
    import struct
    
    sample_rate = 8000  # 8kHz for telephony
    num_samples = sample_rate * duration_seconds
    
    # WAV header
    header = b'RIFF'
    header += struct.pack('<I', 36 + num_samples * 2)  # File size
    header += b'WAVE'
    header += b'fmt '
    header += struct.pack('<I', 16)  # fmt chunk size
    header += struct.pack('<H', 1)   # PCM format
    header += struct.pack('<H', 1)   # Mono
    header += struct.pack('<I', sample_rate)
    header += struct.pack('<I', sample_rate * 2)  # Byte rate
    header += struct.pack('<H', 2)   # Block align
    header += struct.pack('<H', 16)  # Bits per sample
    header += b'data'
    header += struct.pack('<I', num_samples * 2)  # Data size
    
    # Silence (zeros)
    data = b'\x00' * (num_samples * 2)
    
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(filename, header + data, content_type='audio/wav')
