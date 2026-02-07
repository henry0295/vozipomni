from django.urls import path
from django.http import JsonResponse
from django.utils import timezone

def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'VoziPOmni Backend'
    })

urlpatterns = [
    path('', health_check, name='health_check'),
]
