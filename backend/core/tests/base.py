"""
Base test classes for VoziPOmni Contact Center tests.

This module provides base test classes that encapsulate common patterns:
- APITestCase: Base class for API endpoint testing
- WebSocketTestCase: Base class for WebSocket consumer testing
- CeleryTestCase: Base class for Celery task testing
- ModelTestCase: Base class for model testing
"""

import pytest
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APITestCase as DRFAPITestCase
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model


User = get_user_model()


class APITestCase(DRFAPITestCase):
    """
    Base test case for API endpoint testing.
    
    Provides common setup and helper methods for testing REST API endpoints.
    Includes authentication helpers and assertion methods.
    
    Usage:
        class CampaignAPITest(APITestCase):
            def test_list_campaigns(self):
                response = self.get('/api/campaigns/')
                self.assert_status_ok(response)
    """
    
    def setUp(self):
        """Set up test case with common test data."""
        super().setUp()
        self.user = None
        self.admin = None
    
    def create_user(self, email='test@vozipomni.com', role='agent', **kwargs):
        """
        Create a test user with specified role.
        
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
    
    def authenticate(self, user=None):
        """
        Authenticate the API client with JWT token.
        
        Args:
            user: User to authenticate as (creates one if None)
        """
        if user is None:
            user = self.create_user()
        
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.user = user
    
    def authenticate_as_admin(self):
        """Authenticate as an admin user."""
        self.admin = User.objects.create_superuser(
            email='admin@vozipomni.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        self.authenticate(self.admin)
    
    def authenticate_as_supervisor(self):
        """Authenticate as a supervisor user."""
        supervisor = self.create_user(
            email='supervisor@vozipomni.com',
            role='supervisor'
        )
        self.authenticate(supervisor)
    
    def get(self, url, **kwargs):
        """Perform GET request."""
        return self.client.get(url, **kwargs)
    
    def post(self, url, data=None, **kwargs):
        """Perform POST request."""
        return self.client.post(url, data, format='json', **kwargs)
    
    def put(self, url, data=None, **kwargs):
        """Perform PUT request."""
        return self.client.put(url, data, format='json', **kwargs)
    
    def patch(self, url, data=None, **kwargs):
        """Perform PATCH request."""
        return self.client.patch(url, data, format='json', **kwargs)
    
    def delete(self, url, **kwargs):
        """Perform DELETE request."""
        return self.client.delete(url, **kwargs)
    
    # Assertion helpers
    
    def assert_status_ok(self, response):
        """Assert response status is 200 OK."""
        self.assertEqual(response.status_code, 200, 
                        f"Expected 200, got {response.status_code}: {response.data}")
    
    def assert_status_created(self, response):
        """Assert response status is 201 Created."""
        self.assertEqual(response.status_code, 201,
                        f"Expected 201, got {response.status_code}: {response.data}")
    
    def assert_status_no_content(self, response):
        """Assert response status is 204 No Content."""
        self.assertEqual(response.status_code, 204,
                        f"Expected 204, got {response.status_code}")
    
    def assert_status_bad_request(self, response):
        """Assert response status is 400 Bad Request."""
        self.assertEqual(response.status_code, 400,
                        f"Expected 400, got {response.status_code}: {response.data}")
    
    def assert_status_unauthorized(self, response):
        """Assert response status is 401 Unauthorized."""
        self.assertEqual(response.status_code, 401,
                        f"Expected 401, got {response.status_code}: {response.data}")
    
    def assert_status_forbidden(self, response):
        """Assert response status is 403 Forbidden."""
        self.assertEqual(response.status_code, 403,
                        f"Expected 403, got {response.status_code}: {response.data}")
    
    def assert_status_not_found(self, response):
        """Assert response status is 404 Not Found."""
        self.assertEqual(response.status_code, 404,
                        f"Expected 404, got {response.status_code}: {response.data}")
    
    def assert_has_key(self, response, key):
        """Assert response data contains specified key."""
        self.assertIn(key, response.data,
                     f"Key '{key}' not found in response: {response.data}")
    
    def assert_count(self, response, expected_count):
        """Assert response results count matches expected."""
        if 'results' in response.data:
            actual = len(response.data['results'])
        elif isinstance(response.data, list):
            actual = len(response.data)
        else:
            self.fail(f"Cannot determine count from response: {response.data}")
        
        self.assertEqual(actual, expected_count,
                        f"Expected {expected_count} items, got {actual}")


class WebSocketTestCase(TransactionTestCase):
    """
    Base test case for WebSocket consumer testing.
    
    Provides helper methods for testing Django Channels WebSocket consumers.
    Uses TransactionTestCase for proper async support.
    
    Usage:
        class AgentConsumerTest(WebSocketTestCase):
            async def test_connect(self):
                communicator = await self.create_communicator('/ws/agents/')
                connected, _ = await communicator.connect()
                self.assertTrue(connected)
    """
    
    async def create_communicator(self, path, user=None, headers=None):
        """
        Create a WebSocket communicator for testing.
        
        Args:
            path: WebSocket path
            user: User to authenticate as (optional)
            headers: Additional headers (optional)
            
        Returns:
            WebsocketCommunicator: Configured communicator
        """
        from config.asgi import application
        
        # Add authentication headers if user provided
        if user:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            token = str(refresh.access_token)
            
            if headers is None:
                headers = []
            headers.append((b'authorization', f'Bearer {token}'.encode()))
        
        return WebsocketCommunicator(application, path, headers=headers or [])
    
    async def connect_and_receive(self, communicator):
        """
        Connect to WebSocket and receive first message.
        
        Args:
            communicator: WebsocketCommunicator instance
            
        Returns:
            tuple: (connected, subprotocol, message)
        """
        connected, subprotocol = await communicator.connect()
        message = None
        
        if connected:
            message = await communicator.receive_json_from()
        
        return connected, subprotocol, message
    
    async def send_and_receive(self, communicator, data):
        """
        Send data and receive response.
        
        Args:
            communicator: WebsocketCommunicator instance
            data: Data to send (will be JSON encoded)
            
        Returns:
            dict: Received response
        """
        await communicator.send_json_to(data)
        return await communicator.receive_json_from()


class CeleryTestCase(TestCase):
    """
    Base test case for Celery task testing.
    
    Provides helper methods for testing Celery tasks with proper
    mocking and assertion utilities.
    
    Usage:
        class ProcessCallsTaskTest(CeleryTestCase):
            def test_process_pending_calls(self):
                result = self.run_task(process_pending_calls)
                self.assert_task_success(result)
    """
    
    def setUp(self):
        """Set up Celery test configuration."""
        super().setUp()
        
        # Configure Celery for synchronous execution
        from django.conf import settings
        from celery import current_app
        
        current_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
    
    def run_task(self, task, *args, **kwargs):
        """
        Run a Celery task synchronously.
        
        Args:
            task: Task function to run
            *args: Task positional arguments
            **kwargs: Task keyword arguments
            
        Returns:
            Result of task execution
        """
        return task.apply(*args, **kwargs)
    
    def run_task_async(self, task, *args, **kwargs):
        """
        Run a Celery task asynchronously (returns AsyncResult).
        
        Args:
            task: Task function to run
            *args: Task positional arguments
            **kwargs: Task keyword arguments
            
        Returns:
            AsyncResult: Task result object
        """
        return task.apply_async(args=args, kwargs=kwargs)
    
    def assert_task_success(self, result):
        """Assert task completed successfully."""
        self.assertTrue(result.successful(),
                       f"Task failed: {result.traceback if hasattr(result, 'traceback') else 'Unknown error'}")
    
    def assert_task_failed(self, result):
        """Assert task failed."""
        self.assertTrue(result.failed(),
                       "Expected task to fail but it succeeded")
    
    def assert_task_retry(self, result):
        """Assert task was retried."""
        self.assertEqual(result.state, 'RETRY',
                        f"Expected RETRY state, got {result.state}")


class ModelTestCase(TestCase):
    """
    Base test case for model testing.
    
    Provides helper methods for testing Django models including
    validation, relationships, and custom methods.
    
    Usage:
        class CampaignModelTest(ModelTestCase):
            def test_campaign_creation(self):
                campaign = self.create_instance(Campaign, name='Test')
                self.assert_valid(campaign)
    """
    
    def create_instance(self, model_class, **kwargs):
        """
        Create a model instance with specified fields.
        
        Args:
            model_class: Model class to instantiate
            **kwargs: Field values
            
        Returns:
            Model instance (not saved)
        """
        return model_class(**kwargs)
    
    def create_and_save(self, model_class, **kwargs):
        """
        Create and save a model instance.
        
        Args:
            model_class: Model class to instantiate
            **kwargs: Field values
            
        Returns:
            Saved model instance
        """
        instance = model_class(**kwargs)
        instance.full_clean()  # Validate before saving
        instance.save()
        return instance
    
    def assert_valid(self, instance):
        """
        Assert model instance passes validation.
        
        Args:
            instance: Model instance to validate
        """
        try:
            instance.full_clean()
        except Exception as e:
            self.fail(f"Model validation failed: {e}")
    
    def assert_invalid(self, instance, field=None):
        """
        Assert model instance fails validation.
        
        Args:
            instance: Model instance to validate
            field: Specific field expected to fail (optional)
        """
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError) as cm:
            instance.full_clean()
        
        if field:
            self.assertIn(field, cm.exception.error_dict,
                         f"Expected validation error on field '{field}'")
    
    def assert_field_required(self, model_class, field_name):
        """
        Assert field is required (cannot be null/blank).
        
        Args:
            model_class: Model class
            field_name: Field name to check
        """
        field = model_class._meta.get_field(field_name)
        self.assertFalse(field.null and field.blank,
                        f"Field '{field_name}' should be required")
    
    def assert_relationship_exists(self, instance, related_name):
        """
        Assert relationship exists on model instance.
        
        Args:
            instance: Model instance
            related_name: Name of related field/manager
        """
        self.assertTrue(hasattr(instance, related_name),
                       f"Relationship '{related_name}' not found on {instance.__class__.__name__}")
