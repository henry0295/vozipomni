"""
API de seguridad y antifraude (solo administradores):

  GET/PUT  /api/telephony/security/policy/        política de marcación
  POST     /api/telephony/security/policy/test/   {number} → ¿se permitiría?
  POST     /api/telephony/security/policy/apply/  regenerar dialplan y recargar Asterisk
  GET      /api/telephony/security/events/        eventos (?event_type=&severity=&days=)
  GET      /api/telephony/security/summary/       contadores últimas 24 h
"""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminUser
from .models import TelephonySecurityEvent, TelephonySecurityPolicy


class SecurityPolicySerializer(serializers.ModelSerializer):
    updated_by_name = serializers.SerializerMethodField()
    blocked_list = serializers.ListField(read_only=True)
    allowed_list = serializers.ListField(read_only=True)

    class Meta:
        model = TelephonySecurityPolicy
        exclude = ['id', 'updated_by']
        read_only_fields = ['updated_at']

    def get_updated_by_name(self, obj):
        u = obj.updated_by
        return (u.get_full_name() or u.username) if u else None

    def validate_home_country_code(self, value):
        value = ''.join(ch for ch in value if ch.isdigit())
        if not value:
            raise serializers.ValidationError('Indicativo numérico, ej: 57')
        return value

    def validate_alert_emails(self, value):
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email
        emails = [e.strip() for e in (value or '').replace(',', '\n').splitlines() if e.strip()]
        for e in emails:
            try:
                validate_email(e)
            except ValidationError:
                raise serializers.ValidationError(f'Correo inválido: {e}')
        return '\n'.join(emails)

    def validate_max_number_length(self, value):
        if value and not 7 <= value <= 20:
            raise serializers.ValidationError('Entre 7 y 20 dígitos (0 = sin límite).')
        return value


class SecurityPolicyView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(SecurityPolicySerializer(TelephonySecurityPolicy.get()).data)

    def put(self, request):
        from .security import apply_policy
        policy = TelephonySecurityPolicy.get()
        ser = SecurityPolicySerializer(policy, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(updated_by=request.user)
        result = apply_policy()
        return Response({**ser.data, 'apply_result': result})

    patch = put


class SecurityPolicyTestView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        number = str(request.data.get('number', '')).strip()
        allowed, reason = TelephonySecurityPolicy.get().check_number(number)
        labels = dict(TelephonySecurityEvent.TYPE_CHOICES)
        return Response({'number': number, 'allowed': allowed, 'reason': reason,
                         'reason_label': labels.get(reason, '') if reason else ''})


class SecurityPolicyApplyView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .security import apply_policy
        result = apply_policy()
        code = status.HTTP_200_OK if result.get('dialplan') else status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(result, status=code)


class SecurityEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = TelephonySecurityEvent
        fields = ['id', 'event_type', 'event_type_display', 'severity', 'number', 'trunk',
                  'source', 'detail', 'notified', 'created_at']


class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = TelephonySecurityEvent.objects.all()
        p = self.request.query_params
        if p.get('event_type'):
            qs = qs.filter(event_type=p['event_type'])
        if p.get('severity'):
            qs = qs.filter(severity=p['severity'])
        try:
            days = int(p.get('days', 7))
        except ValueError:
            days = 7
        return qs.filter(created_at__gte=timezone.now() - timedelta(days=max(1, min(days, 90))))


class SecuritySummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import Call
        since = timezone.now() - timedelta(hours=24)
        policy = TelephonySecurityPolicy.get()
        events = TelephonySecurityEvent.objects.filter(created_at__gte=since)
        by_type = dict(events.values_list('event_type').annotate(n=Count('id')))
        outbound = Call.objects.filter(direction='outbound', start_time__gte=since)
        intl = sum(1 for n in outbound.values_list('called_number', flat=True) if policy.is_international(n))
        return Response({
            'events_24h': events.count(),
            'critical_24h': events.filter(severity='critical').count(),
            'by_type': by_type,
            'outbound_24h': outbound.count(),
            'international_24h': intl,
        })
