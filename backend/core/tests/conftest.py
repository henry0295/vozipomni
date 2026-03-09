"""
Shared pytest fixtures and configuration for VoziPOmni Contact Center tests.

This module provides reusable fixtures for:
- Database access
- API clients (authenticated and unauthenticated)
- WebSocket testing
- Celery task testing
- Common test data setup
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from channels.testing import WebsocketCommunicator
from celery import Celery


User = get_user_model()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def db_access(db):
    """
    Provide access to the test database.
    
    This is a simple wrapper around pytest-django's db fixture
    for explicit database access in tests.
    """
    return db


@pytest.fixture
def transactional_db_access(transactional_db):
    """
    Provide access to the test database with transaction support.
    
    Use this for tests that need to test transaction behavior
    or use TransactionTestCase features.
    """
    return transactional_db


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def user(db):
    """
    Create a basic test user.
    
    Returns:
        User: A standard user with email and password set
    """
    return User.objects.create_user(
        email='testuser@vozipomni.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        role='agent',
        is_active=True
    )


@pytest.fixture
def admin_user(db):
    """
    Create an admin user for testing admin functionality.
    
    Returns:
        User: An admin user with superuser privileges
    """
    return User.objects.create_superuser(
        email='admin@vozipomni.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User'
    )


@pytest.fixture
def supervisor_user(db):
    """
    Create a supervisor user for testing supervisor functionality.
    
    Returns:
        User: A supervisor user
    """
    return User.objects.create_user(
        email='supervisor@vozipomni.com',
        password='supervisorpass123',
        first_name='Supervisor',
        last_name='User',
        role='supervisor',
        is_active=True
    )


@pytest.fixture
def agent_user(db):
    """
    Create an agent user for testing agent functionality.
    
    Returns:
        User: An agent user
    """
    return User.objects.create_user(
        email='agent@vozipomni.com',
        password='agentpass123',
        first_name='Agent',
        last_name='User',
        role='agent',
        is_active=True
    )


# ============================================================================
# Client Fixtures
# ============================================================================

@pytest.fixture
def client():
    """
    Provide a Django test client for making requests.
    
    Returns:
        Client: Django test client instance
    """
    return Client()


@pytest.fixture
def api_client():
    """
    Provide a DRF API client for testing API endpoints.
    
    Returns:
        APIClient: DRF API client instance (unauthenticated)
    """
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """
    Provide an authenticated API client with JWT token.
    
    Args:
        api_client: DRF API client fixture
        user: User fixture
        
    Returns:
        APIClient: Authenticated API client with JWT credentials
    """
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user  # Attach user for easy access in tests
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """
    Provide an authenticated API client with admin user.
    
    Args:
        api_client: DRF API client fixture
        admin_user: Admin user fixture
        
    Returns:
        APIClient: Authenticated API client with admin credentials
    """
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = admin_user
    return api_client


@pytest.fixture
def supervisor_client(api_client, supervisor_user):
    """
    Provide an authenticated API client with supervisor user.
    
    Args:
        api_client: DRF API client fixture
        supervisor_user: Supervisor user fixture
        
    Returns:
        APIClient: Authenticated API client with supervisor credentials
    """
    refresh = RefreshToken.for_user(supervisor_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = supervisor_user
    return api_client


# ============================================================================
# WebSocket Fixtures
# ============================================================================

@pytest.fixture
def websocket_communicator():
    """
    Factory fixture for creating WebSocket communicators.
    
    Returns:
        function: Factory function that creates WebsocketCommunicator instances
        
    Example:
        communicator = websocket_communicator(MyConsumer, '/ws/path/')
        connected, _ = await communicator.connect()
    """
    def _create_communicator(application, path, headers=None):
        """
        Create a WebSocket communicator for testing.
        
        Args:
            application: ASGI application or consumer class
            path: WebSocket path
            headers: Optional headers dict
            
        Returns:
            WebsocketCommunicator: Configured communicator instance
        """
        return WebsocketCommunicator(application, path, headers=headers or [])
    
    return _create_communicator


# ============================================================================
# Celery Fixtures
# ============================================================================

@pytest.fixture
def celery_app():
    """
    Provide a Celery app instance for testing tasks.
    
    Returns:
        Celery: Celery application instance configured for testing
    """
    app = Celery('vozipomni_test')
    app.conf.update(
        task_always_eager=True,  # Execute tasks synchronously
        task_eager_propagates=True,  # Propagate exceptions
        broker_url='memory://',  # Use in-memory broker
        result_backend='cache+memory://',  # Use in-memory result backend
    )
    return app


@pytest.fixture
def celery_worker(celery_app):
    """
    Provide a Celery worker for testing task execution.
    
    Note: Most tests should use task_always_eager=True instead.
    This fixture is for tests that need actual worker behavior.
    
    Returns:
        Worker: Celery worker instance
    """
    from celery.contrib.testing import worker
    
    with worker.start_worker(celery_app, perform_ping_check=False) as w:
        yield w


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def mock_redis(mocker):
    """
    Provide a mocked Redis client for testing.
    
    Args:
        mocker: pytest-mock fixture
        
    Returns:
        Mock: Mocked Redis client
    """
    mock = mocker.MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_ami_client(mocker):
    """
    Provide a mocked Asterisk AMI client for testing.
    
    Args:
        mocker: pytest-mock fixture
        
    Returns:
        Mock: Mocked AMI client
    """
    mock = mocker.MagicMock()
    mock.connect.return_value = True
    mock.disconnect.return_value = True
    mock.originate_call.return_value = {'Response': 'Success'}
    mock.hangup_call.return_value = {'Response': 'Success'}
    return mock


@pytest.fixture(autouse=True)
def reset_sequences(db):
    """
    Reset database sequences after each test.
    
    This ensures consistent IDs across test runs when using --reuse-db.
    Automatically applied to all tests that use the database.
    """
    yield
    # Sequences are automatically reset by pytest-django after each test


@pytest.fixture
def capture_on_commit_callbacks(db):
    """
    Capture and execute on_commit callbacks immediately for testing.
    
    Django's transaction.on_commit() callbacks are normally executed
    after the transaction commits. In tests, this can cause issues.
    This fixture makes them execute immediately.
    
    Returns:
        list: List of captured callbacks
    """
    from django.test import TestCase
    
    callbacks = []
    
    def capture_callback(callback):
        callbacks.append(callback)
        callback()  # Execute immediately
    
    # Monkey patch transaction.on_commit
    import django.db.transaction
    original_on_commit = django.db.transaction.on_commit
    django.db.transaction.on_commit = capture_callback
    
    yield callbacks
    
    # Restore original
    django.db.transaction.on_commit = original_on_commit
