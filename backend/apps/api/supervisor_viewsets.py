"""
VozipOmni — Supervisor ViewSet

Endpoints exclusivos para supervisores:
  GET  /api/supervisor/dashboard/            → métricas en tiempo real
  GET  /api/supervisor/agents/               → estado de todos los agentes
  POST /api/supervisor/spy/{call_id}/        → escuchar llamada en silencio
  POST /api/supervisor/whisper/{call_id}/    → susurrar al agente
  POST /api/supervisor/barge/{call_id}/      → entrar a la llamada
  POST /api/supervisor/force_break/{agent}/  → forzar pausa del agente
  POST /api/supervisor/force_logout/{agent}/ → desconectar agente

Solo accesible por admin y supervisor.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta

from core.permissions import IsAdminOrSupervisor


class SupervisorViewSet(viewsets.ViewSet):
    """Panel de supervisión en tiempo real."""
    permission_classes = [IsAdminOrSupervisor]

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """Métricas globales del contact center en tiempo real."""
        from apps.agents.models import Agent
        from apps.campaigns.models import Campaign
        from apps.telephony.models import Call
        from apps.queues.models import Queue

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Resumen de agentes
        agents = Agent.objects.all()
        agent_summary = {
            'total': agents.count(),
            'online': agents.exclude(status='offline').count(),
            'available': agents.filter(status='available').count(),
            'oncall': agents.filter(status='oncall').count(),
            'break': agents.filter(status='break').count(),
            'wrapup': agents.filter(status='wrapup').count(),
            'offline': agents.filter(status='offline').count(),
        }

        # Resumen de campañas activas
        active_campaigns = Campaign.objects.filter(status='active')

        # Llamadas del día
        calls_today = Call.objects.filter(start_time__gte=today_start)
        call_summary = {
            'total': calls_today.count(),
            'inbound': calls_today.filter(direction='inbound').count(),
            'outbound': calls_today.filter(direction='outbound').count(),
            'answered': calls_today.filter(status='completed').count(),
            'abandoned': calls_today.filter(status='abandoned').count(),
            'active_now': calls_today.filter(status__in=['initiated', 'ringing', 'answered']).count(),
        }
        answered = call_summary['answered']
        total = call_summary['total']
        call_summary['answer_rate'] = round(answered / total * 100, 1) if total > 0 else 0

        avg_talk = calls_today.filter(status='completed').aggregate(avg=Avg('talk_time'))['avg']
        call_summary['avg_talk_time'] = round(avg_talk or 0, 0)

        # Colas activas
        queue_summary = []
        for q in Queue.objects.filter(is_active=True):
            waiting = calls_today.filter(queue=q, status='ringing').count()
            queue_summary.append({
                'id': q.id,
                'name': q.name,
                'calls_waiting': waiting,
                'agents_available': agents.filter(
                    status='available',
                    queue_memberships__queue=q,
                    queue_memberships__paused=False,
                ).count(),
            })

        return Response({
            'timestamp': now.isoformat(),
            'agents': agent_summary,
            'campaigns_active': active_campaigns.count(),
            'calls': call_summary,
            'queues': queue_summary,
        })

    @action(detail=False, methods=['get'], url_path='agents')
    def agents_status(self, request):
        """Lista detallada de todos los agentes con su estado actual."""
        from apps.agents.models import Agent
        from apps.telephony.models import Call

        agents = Agent.objects.select_related('user', 'current_campaign').all()

        # Obtener llamadas activas por agente en una sola query
        active_calls = {
            c.agent_id: c
            for c in Call.objects.filter(
                agent__in=agents,
                status__in=['initiated', 'ringing', 'answered'],
            ).select_related('agent')
        }

        data = []
        for a in agents:
            active_call = active_calls.get(a.id)
            data.append({
                'id': a.id,
                'agent_id': a.agent_id,
                'name': a.user.get_full_name() or a.user.username,
                'sip_extension': a.sip_extension,
                'status': a.status,
                'current_campaign': a.current_campaign.name if a.current_campaign else None,
                'calls_today': a.calls_today,
                'talk_time_today': a.talk_time_today,
                'available_time_today': a.available_time_today,
                'break_time_today': a.break_time_today,
                'wrapup_time_today': a.wrapup_time_today,
                'session_duration': a.session_duration,
                'occupancy': a.occupancy,
                'logged_in_at': a.logged_in_at,
                'current_call_id': active_call.id if active_call else None,
                'current_call_channel': active_call.channel if active_call else None,
            })
        return Response({'agents': data, 'total': len(data)})

    @action(detail=True, methods=['post'], url_path='spy')
    def spy(self, request, pk=None):
        """
        Escuchar una llamada activa en silencio (chanspy sin susurro).
        pk = Call ID de la llamada a espiar.
        """
        from apps.telephony.models import Call
        from apps.telephony.asterisk_ami import AsteriskAMI

        try:
            call = Call.objects.get(pk=pk, status__in=['initiated', 'ringing', 'answered'])
        except Call.DoesNotExist:
            return Response({'error': 'Llamada activa no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        supervisor_extension = request.data.get('supervisor_extension')
        if not supervisor_extension:
            return Response({'error': 'supervisor_extension requerido'}, status=status.HTTP_400_BAD_REQUEST)

        ami = AsteriskAMI()
        if ami.connect():
            try:
                ami.originate(
                    channel=f'PJSIP/{supervisor_extension}',
                    context='from-spy',
                    exten='s',
                    priority=1,
                    variable={'SPY_MODE': 'listen', 'SPY_CHANNEL': call.channel or ''},
                    caller_id=f'Supervisor <{supervisor_extension}>',
                )
                ami.disconnect()
                return Response({'success': True, 'message': f'Escuchando llamada {call.call_id}'})
            except Exception as e:
                ami.disconnect()
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'error': 'No se pudo conectar a Asterisk AMI'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=True, methods=['post'], url_path='whisper')
    def whisper(self, request, pk=None):
        """Susurrar al agente durante una llamada (solo el agente escucha al supervisor)."""
        from apps.telephony.models import Call
        from apps.telephony.asterisk_ami import AsteriskAMI

        try:
            call = Call.objects.get(pk=pk, status__in=['initiated', 'ringing', 'answered'])
        except Call.DoesNotExist:
            return Response({'error': 'Llamada activa no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        supervisor_extension = request.data.get('supervisor_extension')
        if not supervisor_extension:
            return Response({'error': 'supervisor_extension requerido'}, status=status.HTTP_400_BAD_REQUEST)

        ami = AsteriskAMI()
        if ami.connect():
            try:
                ami.originate(
                    channel=f'PJSIP/{supervisor_extension}',
                    context='from-spy',
                    exten='s',
                    priority=1,
                    variable={'SPY_MODE': 'whisper', 'SPY_CHANNEL': call.channel or ''},
                    caller_id=f'Supervisor <{supervisor_extension}>',
                )
                ami.disconnect()
                return Response({'success': True, 'message': f'Susurrando al agente en llamada {call.call_id}'})
            except Exception as e:
                ami.disconnect()
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'error': 'No se pudo conectar a Asterisk AMI'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=True, methods=['post'], url_path='barge')
    def barge(self, request, pk=None):
        """Entrar a la llamada (supervisor puede hablar con ambas partes)."""
        from apps.telephony.models import Call
        from apps.telephony.asterisk_ami import AsteriskAMI

        try:
            call = Call.objects.get(pk=pk, status__in=['initiated', 'ringing', 'answered'])
        except Call.DoesNotExist:
            return Response({'error': 'Llamada activa no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        supervisor_extension = request.data.get('supervisor_extension')
        if not supervisor_extension:
            return Response({'error': 'supervisor_extension requerido'}, status=status.HTTP_400_BAD_REQUEST)

        ami = AsteriskAMI()
        if ami.connect():
            try:
                ami.originate(
                    channel=f'PJSIP/{supervisor_extension}',
                    context='from-spy',
                    exten='s',
                    priority=1,
                    variable={'SPY_MODE': 'barge', 'SPY_CHANNEL': call.channel or ''},
                    caller_id=f'Supervisor <{supervisor_extension}>',
                )
                ami.disconnect()
                return Response({'success': True, 'message': f'Unido a la llamada {call.call_id}'})
            except Exception as e:
                ami.disconnect()
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'error': 'No se pudo conectar a Asterisk AMI'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=True, methods=['post'], url_path='force_break')
    def force_break(self, request, pk=None):
        """Forzar pausa de un agente (pk = Agent ID)."""
        from apps.agents.models import Agent

        try:
            agent = Agent.objects.get(pk=pk)
        except Agent.DoesNotExist:
            return Response({'error': 'Agente no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get('reason', 'supervisor_forced')
        agent.status = 'break'
        agent.save(update_fields=['status', 'last_status_change'])
        return Response({
            'success': True,
            'agent_id': agent.agent_id,
            'new_status': 'break',
            'reason': reason,
        })

    @action(detail=True, methods=['post'], url_path='force_logout')
    def force_logout(self, request, pk=None):
        """Desconectar un agente forzosamente (pk = Agent ID)."""
        from apps.agents.models import Agent

        try:
            agent = Agent.objects.get(pk=pk)
        except Agent.DoesNotExist:
            return Response({'error': 'Agente no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        agent.logout()
        return Response({
            'success': True,
            'agent_id': agent.agent_id,
            'new_status': 'offline',
        })
