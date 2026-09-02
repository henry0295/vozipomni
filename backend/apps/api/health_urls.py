from django.urls import path
from django.http import JsonResponse
from django.utils import timezone
from django.db import connection
from django.core.cache import cache

def health_check(request):
    """Health check endpoint"""
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception:
        checks['database'] = 'error'
    try:
        cache.set('healthcheck', 'ok', 5)
        checks['redis'] = 'ok' if cache.get('healthcheck') == 'ok' else 'error'
    except Exception:
        checks['redis'] = 'error'
    healthy = all(value == 'ok' for value in checks.values())
    return JsonResponse({
        'status': 'healthy' if healthy else 'unhealthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'VoziPOmni Backend',
        'checks': checks,
    }, status=200 if healthy else 503)

urlpatterns = [
    path('', health_check, name='health_check'),
]
