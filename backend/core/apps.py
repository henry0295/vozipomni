"""
Core application configuration
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for core application"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'
    
    def ready(self):
        """
        Initialize application when Django starts.
        
        This method is called once Django has loaded all models and is ready.
        We use it to register event handlers for cross-module communication.
        """
        # Import and register event handlers
        try:
            from core.event_handlers import register_event_handlers
            register_event_handlers()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error registering event handlers: {e}", exc_info=True)
