"""
Prometheus metrics for VoziPOmni
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)

# ============= CAMPAIGN METRICS =============

campaign_calls_total = Counter(
    'vozipomni_campaign_calls_total',
    'Total calls made by campaign',
    ['campaign_id', 'campaign_name', 'status']
)

campaign_calls_duration_seconds = Histogram(
    'vozipomni_campaign_call_duration_seconds',
    'Call duration in seconds',
    ['campaign_id', 'campaign_name', 'direction', 'disposition'],
    buckets=(5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

campaign_active = Gauge(
    'vozipomni_campaigns_active',
    'Number of active campaigns',
    ['campaign_type', 'dialer_type']
)

campaign_contacts_total = Gauge(
    'vozipomni_campaign_contacts_total',
    'Total contacts in campaign',
    ['campaign_id', 'campaign_name']
)

campaign_contacts_contacted = Gauge(
    'vozipomni_campaign_contacts_contacted',
    'Contacts already contacted',
    ['campaign_id', 'campaign_name']
)

campaign_success_rate = Gauge(
    'vozipomni_campaign_success_rate',
    'Campaign success rate (0-100)',
    ['campaign_id', 'campaign_name']
)

# ============= AGENT METRICS =============

agents_total = Gauge(
    'vozipomni_agents_total',
    'Total number of agents',
    ['status']
)

agents_logged_in = Gauge(
    'vozipomni_agents_logged_in',
    'Number of logged in agents'
)

agent_calls_total = Counter(
    'vozipomni_agent_calls_total',
    'Total calls handled by agent',
    ['agent_id', 'agent_name', 'status']
)

agent_talk_time_seconds = Histogram(
    'vozipomni_agent_talk_time_seconds',
    'Agent talk time in seconds',
    ['agent_id', 'agent_name'],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600)
)

agent_occupancy_percent = Gauge(
    'vozipomni_agent_occupancy_percent',
    'Agent occupancy percentage',
    ['agent_id', 'agent_name']
)

agent_status_changes_total = Counter(
    'vozipomni_agent_status_changes_total',
    'Total agent status changes',
    ['agent_id', 'from_status', 'to_status']
)

# ============= CALL METRICS =============

calls_total = Counter(
    'vozipomni_calls_total',
    'Total calls',
    ['direction', 'status']
)

calls_active = Gauge(
    'vozipomni_calls_active',
    'Currently active calls',
    ['direction']
)

call_wait_time_seconds = Histogram(
    'vozipomni_call_wait_time_seconds',
    'Call wait time in queue',
    ['queue_name'],
    buckets=(5, 10, 20, 30, 60, 120, 300, 600)
)

call_talk_time_seconds = Histogram(
    'vozipomni_call_talk_time_seconds',
    'Call talk time',
    ['direction', 'disposition'],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600)
)

calls_abandoned_total = Counter(
    'vozipomni_calls_abandoned_total',
    'Total abandoned calls',
    ['queue_name', 'reason']
)

# ============= QUEUE METRICS =============

queue_calls_waiting = Gauge(
    'vozipomni_queue_calls_waiting',
    'Calls waiting in queue',
    ['queue_name']
)

queue_agents_available = Gauge(
    'vozipomni_queue_agents_available',
    'Available agents in queue',
    ['queue_name']
)

queue_agents_busy = Gauge(
    'vozipomni_queue_agents_busy',
    'Busy agents in queue',
    ['queue_name']
)

queue_service_level_percent = Gauge(
    'vozipomni_queue_service_level_percent',
    'Queue service level percentage',
    ['queue_name']
)

queue_avg_wait_time_seconds = Gauge(
    'vozipomni_queue_avg_wait_time_seconds',
    'Average wait time in queue',
    ['queue_name']
)

# ============= TRUNK METRICS =============

trunk_calls_active = Gauge(
    'vozipomni_trunk_calls_active',
    'Active calls on trunk',
    ['trunk_name', 'trunk_type']
)

trunk_registered = Gauge(
    'vozipomni_trunk_registered',
    'Trunk registration status (1=registered, 0=not registered)',
    ['trunk_name']
)

trunk_calls_total = Counter(
    'vozipomni_trunk_calls_total',
    'Total calls through trunk',
    ['trunk_name', 'status']
)

# ============= SYSTEM METRICS =============

system_info = Info(
    'vozipomni_system',
    'System information'
)

ami_connection_status = Gauge(
    'vozipomni_ami_connection_status',
    'AMI connection status (1=connected, 0=disconnected)'
)

redis_connection_status = Gauge(
    'vozipomni_redis_connection_status',
    'Redis connection status (1=connected, 0=disconnected)'
)

database_connection_status = Gauge(
    'vozipomni_database_connection_status',
    'Database connection status (1=connected, 0=disconnected)'
)

celery_tasks_total = Counter(
    'vozipomni_celery_tasks_total',
    'Total Celery tasks executed',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'vozipomni_celery_task_duration_seconds',
    'Celery task execution time',
    ['task_name'],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 300)
)

# ============= DIALER METRICS =============

dialer_predictive_ratio = Gauge(
    'vozipomni_dialer_predictive_ratio',
    'Current predictive dialer ratio',
    ['campaign_id']
)

dialer_abandon_rate = Gauge(
    'vozipomni_dialer_abandon_rate',
    'Current abandon rate',
    ['campaign_id']
)

dialer_calls_originated_total = Counter(
    'vozipomni_dialer_calls_originated_total',
    'Total calls originated by dialer',
    ['campaign_id', 'campaign_type']
)

dialer_errors_total = Counter(
    'vozipomni_dialer_errors_total',
    'Total dialer errors',
    ['campaign_id', 'error_type']
)


# ============= HELPER FUNCTIONS =============

def record_call_metrics(call):
    """Record metrics for a completed call"""
    try:
        # Total calls
        calls_total.labels(
            direction=call.direction,
            status=call.status
        ).inc()
        
        # Call duration
        if call.talk_time > 0:
            call_talk_time_seconds.labels(
                direction=call.direction,
                disposition=call.disposition.code if call.disposition else 'none'
            ).observe(call.talk_time)
        
        # Wait time
        if call.wait_time > 0 and call.queue:
            call_wait_time_seconds.labels(
                queue_name=call.queue.name
            ).observe(call.wait_time)
        
        # Campaign metrics
        if call.campaign:
            campaign_calls_total.labels(
                campaign_id=str(call.campaign.id),
                campaign_name=call.campaign.name,
                status=call.status
            ).inc()
            
            if call.talk_time > 0:
                campaign_calls_duration_seconds.labels(
                    campaign_id=str(call.campaign.id),
                    campaign_name=call.campaign.name,
                    direction=call.direction,
                    disposition=call.disposition.code if call.disposition else 'none'
                ).observe(call.talk_time)
        
        # Agent metrics
        if call.agent:
            agent_calls_total.labels(
                agent_id=call.agent.agent_id,
                agent_name=str(call.agent.user),
                status=call.status
            ).inc()
            
            if call.talk_time > 0:
                agent_talk_time_seconds.labels(
                    agent_id=call.agent.agent_id,
                    agent_name=str(call.agent.user)
                ).observe(call.talk_time)
        
    except Exception as e:
        logger.error(f"Error recording call metrics: {e}")


def update_agent_metrics():
    """Update agent metrics (called periodically)"""
    try:
        from apps.agents.models import Agent
        
        # Count by status
        for status_code, status_name in Agent.STATUS_CHOICES:
            count = Agent.objects.filter(status=status_code).count()
            agents_total.labels(status=status_code).set(count)
        
        # Logged in agents
        logged_in = Agent.objects.exclude(status='offline').count()
        agents_logged_in.set(logged_in)
        
        # Individual agent metrics
        for agent in Agent.objects.exclude(status='offline'):
            agent_occupancy_percent.labels(
                agent_id=agent.agent_id,
                agent_name=str(agent.user)
            ).set(agent.occupancy)
        
    except Exception as e:
        logger.error(f"Error updating agent metrics: {e}")


def update_queue_metrics():
    """Update queue metrics (called periodically)"""
    try:
        from apps.queues.models import Queue
        
        for queue in Queue.objects.filter(is_active=True):
            stats = getattr(queue, 'stats', None)
            if stats:
                queue_calls_waiting.labels(queue_name=queue.name).set(stats.calls_waiting)
                queue_agents_available.labels(queue_name=queue.name).set(stats.agents_available)
                queue_agents_busy.labels(queue_name=queue.name).set(stats.agents_busy)
                queue_service_level_percent.labels(queue_name=queue.name).set(stats.service_level_percentage)
                queue_avg_wait_time_seconds.labels(queue_name=queue.name).set(stats.avg_wait_time)
        
    except Exception as e:
        logger.error(f"Error updating queue metrics: {e}")


def update_campaign_metrics():
    """Update campaign metrics (called periodically)"""
    try:
        from apps.campaigns.models import Campaign
        
        # Active campaigns by type
        for campaign_type, _ in Campaign.CAMPAIGN_TYPES:
            for dialer_type, _ in Campaign.DIALER_TYPES:
                count = Campaign.objects.filter(
                    status='active',
                    campaign_type=campaign_type,
                    dialer_type=dialer_type
                ).count()
                campaign_active.labels(
                    campaign_type=campaign_type,
                    dialer_type=dialer_type or 'none'
                ).set(count)
        
        # Individual campaign metrics
        for campaign in Campaign.objects.filter(status='active'):
            campaign_contacts_total.labels(
                campaign_id=str(campaign.id),
                campaign_name=campaign.name
            ).set(campaign.total_contacts)
            
            campaign_contacts_contacted.labels(
                campaign_id=str(campaign.id),
                campaign_name=campaign.name
            ).set(campaign.contacted)
            
            campaign_success_rate.labels(
                campaign_id=str(campaign.id),
                campaign_name=campaign.name
            ).set(campaign.success_rate)
        
    except Exception as e:
        logger.error(f"Error updating campaign metrics: {e}")


def update_trunk_metrics():
    """Update trunk metrics (called periodically)"""
    try:
        from apps.telephony.models import SIPTrunk
        
        for trunk in SIPTrunk.objects.filter(is_active=True):
            trunk_registered.labels(trunk_name=trunk.name).set(
                1 if trunk.is_registered else 0
            )
            
            trunk_calls_active.labels(
                trunk_name=trunk.name,
                trunk_type=trunk.trunk_type
            ).set(trunk.calls_active)
        
    except Exception as e:
        logger.error(f"Error updating trunk metrics: {e}")


def update_system_metrics():
    """Update system health metrics"""
    try:
        from django.db import connection
        from django.core.cache import cache
        
        # Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            database_connection_status.set(1)
        except:
            database_connection_status.set(0)
        
        # Redis
        try:
            cache.set('health_check', 'ok', 10)
            redis_connection_status.set(1)
        except:
            redis_connection_status.set(0)
        
        # AMI (check from cache)
        ami_health = cache.get('asterisk_health', {})
        ami_connection_status.set(
            1 if ami_health.get('status') == 'connected' else 0
        )
        
    except Exception as e:
        logger.error(f"Error updating system metrics: {e}")


def update_all_metrics():
    """Update all metrics (called by periodic task)"""
    update_agent_metrics()
    update_queue_metrics()
    update_campaign_metrics()
    update_trunk_metrics()
    update_system_metrics()
