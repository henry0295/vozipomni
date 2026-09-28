"""
ViewSets de administración y calidad:

  UserAdminViewSet          → /api/users/                  gestión de usuarios y roles
  BlacklistViewSet          → /api/blacklist/              lista negra DNC
  EvaluationTemplateViewSet → /api/evaluation-templates/   plantillas de evaluación
  RecordingEvaluationViewSet→ /api/evaluations/            evaluaciones de grabaciones

  PasswordResetRequestView  → POST /api/auth/password-reset/
  PasswordResetConfirmView  → POST /api/auth/password-reset/confirm/
  ChangePasswordView        → POST /api/auth/change-password/
"""
import csv
import io
import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.permissions import IsAdminOrSupervisor, IsAdminSupervisorOrAnalyst, IsAdminUser

logger = logging.getLogger(__name__)
User = get_user_model()


def _normalize_phone(phone: str) -> str:
    """Deja solo dígitos y '+' inicial."""
    phone = (phone or '').strip()
    plus = phone.startswith('+')
    digits = re.sub(r'\D', '', phone)
    return f'+{digits}' if plus and digits else digits


def _invalidate_dnc_cache(phone: str):
    """El dialer cachea DNC en Redis 5 min por número: invalidarlo al cambiar la lista."""
    try:
        import redis
        digits = re.sub(r'\D', '', phone or '')
        if not digits:
            return
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.delete(f'dnc:{digits[-10:]}')
    except Exception as e:
        logger.debug(f"[DNC] No se pudo invalidar caché de {phone}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Usuarios y roles
# ══════════════════════════════════════════════════════════════════════════════

class UserAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=False,
        style={'input_type': 'password'},
    )
    name = serializers.SerializerMethodField()
    has_agent_profile = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'name',
            'role', 'role_display', 'phone', 'department',
            'is_active', 'is_active_agent', 'has_agent_profile',
            'last_login', 'last_activity', 'date_joined', 'password',
        ]
        read_only_fields = ['last_login', 'last_activity', 'date_joined']

    def get_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_has_agent_profile(self, obj):
        return hasattr(obj, 'agent_profile')

    def validate_email(self, value):
        if value:
            qs = User.objects.filter(email__iexact=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('Este correo ya está en uso.')
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        if not self.instance and not password:
            raise serializers.ValidationError({'password': 'La contraseña es obligatoria al crear un usuario.'})
        if password:
            try:
                validate_password(password, user=self.instance)
            except DjangoValidationError as e:
                raise serializers.ValidationError({'password': list(e.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserAdminViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios. Solo administradores. DELETE desactiva (no borra) al usuario."""
    queryset = User.objects.all().order_by('username')
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active', 'is_active_agent']
    ordering_fields = ['username', 'date_joined', 'last_login']

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.pk == self.request.user.pk:
            # Un admin no puede quitarse el rol ni desactivarse a sí mismo
            if serializer.validated_data.get('role', instance.role) != instance.role:
                raise serializers.ValidationError({'role': 'No puedes cambiar tu propio rol.'})
            if serializer.validated_data.get('is_active', True) is False:
                raise serializers.ValidationError({'is_active': 'No puedes desactivar tu propia cuenta.'})
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({'error': 'No puedes eliminar tu propia cuenta.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'status': 'deactivated'})

    @action(detail=True, methods=['post'], url_path='set-password')
    def set_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get('password', '')
        try:
            validate_password(password, user=user)
        except DjangoValidationError as e:
            return Response({'password': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'status': 'password updated'})

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({'error': 'No puedes desactivar tu propia cuenta.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return Response({'is_active': user.is_active})


# ══════════════════════════════════════════════════════════════════════════════
# Lista negra (DNC)
# ══════════════════════════════════════════════════════════════════════════════

class BlacklistSerializer(serializers.ModelSerializer):
    added_by_name = serializers.SerializerMethodField()

    class Meta:
        from apps.contacts.models import Blacklist
        model = Blacklist
        fields = ['id', 'phone', 'reason', 'is_active', 'added_by', 'added_by_name', 'added_at']
        read_only_fields = ['added_by', 'added_at']

    def get_added_by_name(self, obj):
        if obj.added_by:
            return obj.added_by.get_full_name() or obj.added_by.username
        return None

    def validate_phone(self, value):
        phone = _normalize_phone(value)
        if len(re.sub(r'\D', '', phone)) < 7:
            raise serializers.ValidationError('Número demasiado corto.')
        return phone


class BlacklistViewSet(viewsets.ModelViewSet):
    """Lista negra de números que el dialer nunca debe marcar."""
    serializer_class = BlacklistSerializer
    permission_classes = [IsAdminOrSupervisor]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['phone', 'reason']
    ordering = ['-added_at']
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        from apps.contacts.models import Blacklist
        return Blacklist.objects.select_related('added_by').all()

    def perform_create(self, serializer):
        obj = serializer.save(added_by=self.request.user)
        _invalidate_dnc_cache(obj.phone)

    def perform_update(self, serializer):
        obj = serializer.save()
        _invalidate_dnc_cache(obj.phone)

    def perform_destroy(self, instance):
        phone = instance.phone
        instance.delete()
        _invalidate_dnc_cache(phone)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        """
        Importación masiva. Acepta:
          - archivo CSV/XLSX (campo `file`), columnas: phone[, reason]
          - texto plano (campo `numbers`), un número por línea
        """
        from apps.contacts.models import Blacklist

        default_reason = request.data.get('reason', '') or 'Importación masiva'
        rows = []

        uploaded = request.FILES.get('file')
        if uploaded:
            name = uploaded.name.lower()
            if name.endswith(('.xlsx', '.xls')):
                import openpyxl
                wb = openpyxl.load_workbook(uploaded, read_only=True, data_only=True)
                ws = wb.active
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if not row or row[0] is None:
                        continue
                    first = str(row[0]).strip()
                    if i == 0 and not re.search(r'\d', first):
                        continue  # cabecera
                    rows.append((first, str(row[1]).strip() if len(row) > 1 and row[1] else ''))
            else:
                content = uploaded.read().decode('utf-8-sig', errors='ignore')
                for i, row in enumerate(csv.reader(io.StringIO(content))):
                    if not row:
                        continue
                    first = row[0].strip()
                    if i == 0 and not re.search(r'\d', first):
                        continue
                    rows.append((first, row[1].strip() if len(row) > 1 else ''))
        else:
            for line in (request.data.get('numbers') or '').splitlines():
                if line.strip():
                    rows.append((line.strip(), ''))

        if not rows:
            return Response({'error': 'No se encontraron números para importar.'}, status=status.HTTP_400_BAD_REQUEST)

        existing = set(Blacklist.objects.values_list('phone', flat=True))
        to_create, skipped, invalid = [], 0, 0
        seen = set()
        for raw, reason in rows:
            phone = _normalize_phone(raw)
            if len(re.sub(r'\D', '', phone)) < 7:
                invalid += 1
                continue
            if phone in existing or phone in seen:
                skipped += 1
                continue
            seen.add(phone)
            to_create.append(Blacklist(
                phone=phone[:20], reason=(reason or default_reason)[:200],
                added_by=request.user, is_active=True,
            ))

        Blacklist.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=1000)
        for obj in to_create:
            _invalidate_dnc_cache(obj.phone)

        return Response({'imported': len(to_create), 'skipped': skipped, 'invalid': invalid})

    @action(detail=False, methods=['get'])
    def check(self, request):
        """GET /api/blacklist/check/?phone=... → ¿está bloqueado?"""
        from apps.contacts.models import Blacklist, Contact
        phone = re.sub(r'\D', '', request.query_params.get('phone', ''))
        if not phone:
            return Response({'error': 'phone requerido'}, status=status.HTTP_400_BAD_REQUEST)
        tail = phone[-10:]
        in_blacklist = Blacklist.objects.filter(phone__endswith=tail, is_active=True).exists()
        opt_out = Contact.objects.filter(phone__endswith=tail, dnc_opt_out=True).exists()
        return Response({'phone': phone, 'blocked': in_blacklist or opt_out,
                         'in_blacklist': in_blacklist, 'dnc_opt_out': opt_out})


# ══════════════════════════════════════════════════════════════════════════════
# Plantillas y evaluaciones de calidad
# ══════════════════════════════════════════════════════════════════════════════

class EvaluationTemplateSerializer(serializers.ModelSerializer):
    max_total_score = serializers.ReadOnlyField()
    evaluations_count = serializers.SerializerMethodField()

    class Meta:
        from apps.recordings.models import EvaluationTemplate
        model = EvaluationTemplate
        fields = ['id', 'name', 'description', 'criteria', 'is_active', 'is_default',
                  'max_total_score', 'evaluations_count', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_evaluations_count(self, obj):
        return obj.evaluations.count()

    def validate_criteria(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('Debe definir al menos un criterio.')
        names = set()
        for i, c in enumerate(value):
            if not isinstance(c, dict):
                raise serializers.ValidationError(f'Criterio {i + 1}: formato inválido.')
            label = str(c.get('label', '')).strip()
            if not label:
                raise serializers.ValidationError(f'Criterio {i + 1}: la etiqueta es obligatoria.')
            name = str(c.get('name') or '').strip() or re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
            if not name:
                raise serializers.ValidationError(f'Criterio {i + 1}: nombre inválido.')
            if name in names:
                raise serializers.ValidationError(f'Criterio duplicado: {name}')
            names.add(name)
            try:
                max_score = int(c.get('max_score', 5))
            except (TypeError, ValueError):
                raise serializers.ValidationError(f'Criterio {label}: max_score debe ser numérico.')
            if not 1 <= max_score <= 100:
                raise serializers.ValidationError(f'Criterio {label}: max_score entre 1 y 100.')
            c['name'] = name
            c['label'] = label
            c['max_score'] = max_score
            c['description'] = str(c.get('description', '')).strip()
        return value


class EvaluationTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = EvaluationTemplateSerializer
    permission_classes = [IsAdminSupervisorOrAnalyst]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'is_default']
    search_fields = ['name']

    def get_queryset(self):
        from apps.recordings.models import EvaluationTemplate
        return EvaluationTemplate.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        tpl = self.get_object()
        if tpl.evaluations.exists():
            # Conservar el histórico: solo desactivar
            tpl.is_active = False
            tpl.is_default = False
            tpl.save(update_fields=['is_active', 'is_default'])
            return Response({'status': 'deactivated', 'reason': 'La plantilla tiene evaluaciones asociadas'})
        return super().destroy(request, *args, **kwargs)


class RecordingEvaluationSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    agent_id = serializers.IntegerField(source='recording.agent_id', read_only=True)
    recording_filename = serializers.CharField(source='recording.filename', read_only=True)
    call_id = serializers.CharField(source='recording.call.call_id', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        from apps.recordings.models import RecordingEvaluation
        model = RecordingEvaluation
        fields = [
            'id', 'recording', 'recording_filename', 'call_id', 'agent_id', 'agent_name',
            'evaluator', 'evaluator_name', 'template', 'template_name', 'scores_data',
            'greeting', 'clarity', 'professionalism', 'resolution', 'closing',
            'total_score', 'comments', 'feedback_sent', 'created_at', 'updated_at',
        ]
        read_only_fields = ['evaluator', 'total_score', 'created_at', 'updated_at']

    def get_evaluator_name(self, obj):
        return (obj.evaluator.get_full_name() or obj.evaluator.username) if obj.evaluator else None

    def get_agent_name(self, obj):
        agent = obj.recording.agent
        if agent and agent.user:
            return agent.user.get_full_name() or agent.user.username
        return None

    def validate(self, attrs):
        template = attrs.get('template', getattr(self.instance, 'template', None))
        scores = attrs.get('scores_data', getattr(self.instance, 'scores_data', None)) or {}
        if template:
            clean = {}
            for c in template.criteria or []:
                if c['name'] not in scores:
                    raise serializers.ValidationError({'scores_data': f'Falta el criterio "{c.get("label", c["name"])}".'})
                try:
                    v = float(scores[c['name']])
                except (TypeError, ValueError):
                    raise serializers.ValidationError({'scores_data': f'Valor inválido en "{c["name"]}".'})
                if not 0 <= v <= c.get('max_score', 5):
                    raise serializers.ValidationError(
                        {'scores_data': f'"{c.get("label")}" debe estar entre 0 y {c.get("max_score", 5)}.'}
                    )
                clean[c['name']] = v
            attrs['scores_data'] = clean
        else:
            for f in ('greeting', 'clarity', 'professionalism', 'resolution', 'closing'):
                v = attrs.get(f, getattr(self.instance, f, 0) if self.instance else 0)
                if not 0 <= int(v) <= 5:
                    raise serializers.ValidationError({f: 'Debe estar entre 0 y 5.'})
        return attrs


class RecordingEvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = RecordingEvaluationSerializer
    permission_classes = [IsAdminSupervisorOrAnalyst]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['template', 'recording__agent', 'feedback_sent']
    search_fields = ['recording__filename', 'recording__call__call_id', 'comments']
    ordering = ['-created_at']

    def get_queryset(self):
        from apps.recordings.models import RecordingEvaluation
        return RecordingEvaluation.objects.select_related(
            'recording__agent__user', 'recording__call', 'evaluator', 'template'
        )

    def perform_create(self, serializer):
        serializer.save(evaluator=self.request.user)

    @action(detail=False, methods=['get'], url_path='pending-recordings')
    def pending_recordings(self, request):
        """Grabaciones completadas aún sin evaluar (para el modal "Nueva evaluación")."""
        from apps.recordings.models import Recording
        qs = Recording.objects.filter(status='completed', evaluation__isnull=True).select_related(
            'agent__user', 'call', 'campaign'
        ).order_by('-created_at')
        agent = request.query_params.get('agent')
        if agent:
            qs = qs.filter(agent_id=agent)
        data = [{
            'id': r.id,
            'filename': r.filename,
            'duration': r.duration,
            'created_at': r.created_at,
            'call_id': r.call.call_id if r.call else None,
            'agent_id': r.agent_id,
            'agent_name': (r.agent.user.get_full_name() or r.agent.user.username) if r.agent and r.agent.user else None,
            'campaign': r.campaign.name if r.campaign else None,
        } for r in qs[:200]]
        return Response(data)


# ══════════════════════════════════════════════════════════════════════════════
# Contraseñas
# ══════════════════════════════════════════════════════════════════════════════

class PasswordResetThrottle(AnonRateThrottle):
    scope = 'password_reset'


class PasswordResetRequestView(APIView):
    """
    POST {email} → envía enlace de recuperación.
    Respuesta siempre genérica para no revelar qué correos existen.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        identifier = (request.data.get('email') or '').strip()
        generic = {'message': 'Si la cuenta existe, recibirás un correo con instrucciones.'}
        if not identifier:
            return Response({'email': ['Ingresa tu correo o usuario.']}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(is_active=True).filter(
            email__iexact=identifier
        ).first() or User.objects.filter(is_active=True, username=identifier).first()

        if user and user.email:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            base = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
            link = f"{base}/reset-password?uid={uid}&token={token}"
            try:
                send_mail(
                    subject='VozipOmni — Recuperación de contraseña',
                    message=(
                        f"Hola {user.get_full_name() or user.username},\n\n"
                        f"Recibimos una solicitud para restablecer tu contraseña.\n"
                        f"Abre este enlace para crear una nueva (válido por tiempo limitado):\n\n{link}\n\n"
                        f"Si no fuiste tú, ignora este mensaje."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                logger.info(f"[Auth] Enlace de recuperación enviado a user_id={user.pk}")
            except Exception as e:
                logger.error(f"[Auth] No se pudo enviar correo de recuperación: {e}")
        return Response(generic)


class PasswordResetConfirmView(APIView):
    """POST {uid, token, password} → establece la nueva contraseña."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        password = request.data.get('password', '')
        invalid = Response({'error': 'El enlace es inválido o ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return invalid
        if not default_token_generator.check_token(user, token):
            return invalid
        try:
            validate_password(password, user=user)
        except DjangoValidationError as e:
            return Response({'password': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=['password'])
        # Invalidar sesiones: blacklist de todos los refresh tokens del usuario
        try:
            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
            for t in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=t)
        except Exception:
            pass
        return Response({'message': 'Contraseña actualizada. Ya puedes iniciar sesión.'})


class ChangePasswordView(APIView):
    """POST {current_password, new_password} → cambio de contraseña del usuario autenticado."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current = request.data.get('current_password', '')
        new = request.data.get('new_password', '')
        if not user.check_password(current):
            return Response({'current_password': ['La contraseña actual no es correcta.']},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new, user=user)
        except DjangoValidationError as e:
            return Response({'new_password': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new)
        user.save(update_fields=['password'])
        return Response({'message': 'Contraseña actualizada.'})
