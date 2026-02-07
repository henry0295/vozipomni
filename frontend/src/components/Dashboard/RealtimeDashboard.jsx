import React, { useState, useEffect, useRef } from 'react';
import { 
  Phone, PhoneCall, PhoneOff, Users, Activity, 
  TrendingUp, Clock, CheckCircle, XCircle 
} from 'lucide-react';

const RealtimeDashboard = ({ wsUrl }) => {
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState({
    calls_today: 0,
    calls_answered: 0,
    calls_abandoned: 0,
    calls_active: 0,
    agents_ready: 0,
    agents_in_call: 0,
    agents_acw: 0,
    agents_paused: 0,
    avg_talk_time: 0,
    service_level: 0
  });
  const [agents, setAgents] = useState([]);
  const [queues, setQueues] = useState([]);
  const [activeCalls, setActiveCalls] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);
  
  const ws = useRef(null);

  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [wsUrl]);

  const connectWebSocket = () => {
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('✓ Dashboard WebSocket connected');
      setConnected(true);
      
      // Solicitar datos iniciales
      socket.send(JSON.stringify({ action: 'refresh_stats' }));
      socket.send(JSON.stringify({ action: 'refresh_agents' }));
      socket.send(JSON.stringify({ action: 'refresh_queues' }));
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    socket.onclose = () => {
      console.log('Dashboard WebSocket closed');
      setConnected(false);
      
      // Reconectar después de 3 segundos
      setTimeout(connectWebSocket, 3000);
    };

    ws.current = socket;
  };

  const handleMessage = (data) => {
    const { type } = data;

    switch (type) {
      case 'initial_data':
        setStats(data.stats);
        setAgents(data.agents);
        setQueues(data.queues);
        setActiveCalls(data.active_calls);
        break;

      case 'stats_update':
        setStats(data.data);
        break;

      case 'agents_update':
        setAgents(data.data);
        break;

      case 'queues_update':
        setQueues(data.data);
        break;

      case 'asterisk.event':
        handleAsteriskEvent(data);
        break;

      default:
        console.log('Unknown message type:', type);
    }
  };

  const handleAsteriskEvent = (event) => {
    const { event_type, data } = event;

    // Agregar al log de eventos recientes
    addRecentEvent(event_type, data);

    // Actualizar datos según el tipo de evento
    if (event_type === 'call.hangup') {
      // Remover de llamadas activas
      setActiveCalls(prev => prev.filter(call => call.channel !== data.channel));
    } else if (event_type === 'call.new_channel') {
      // Agregar nueva llamada activa
      setActiveCalls(prev => [...prev, {
        channel: data.channel,
        caller_id: data.caller_id,
        state: data.state
      }]);
    } else if (event_type.startswith('agent.')) {
      // Actualizar lista de agentes
      refreshAgents();
    }
  };

  const addRecentEvent = (type, data) => {
    const event = {
      id: Date.now(),
      type,
      data,
      timestamp: new Date()
    };

    setRecentEvents(prev => [event, ...prev].slice(0, 20)); // Mantener solo los últimos 20
  };

  const refreshStats = () => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ action: 'refresh_stats' }));
    }
  };

  const refreshAgents = () => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ action: 'refresh_agents' }));
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const getStatusColor = (status) => {
    const colors = {
      'ready': 'text-green-600 bg-green-100',
      'in_call': 'text-blue-600 bg-blue-100',
      'acw': 'text-yellow-600 bg-yellow-100',
      'paused': 'text-orange-600 bg-orange-100',
      'offline': 'text-gray-600 bg-gray-100'
    };
    return colors[status] || 'text-gray-600 bg-gray-100';
  };

  const getStatusLabel = (status) => {
    const labels = {
      'ready': 'Listo',
      'in_call': 'En Llamada',
      'acw': 'ACW',
      'paused': 'Pausado',
      'offline': 'Desconectado'
    };
    return labels[status] || status;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Dashboard en Tiempo Real</h1>
        <div className="flex items-center space-x-3">
          <div className={`flex items-center px-4 py-2 rounded-lg ${connected ? 'bg-green-100' : 'bg-red-100'}`}>
            <div className={`w-3 h-3 rounded-full mr-2 ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className={`text-sm font-medium ${connected ? 'text-green-800' : 'text-red-800'}`}>
              {connected ? 'Conectado' : 'Desconectado'}
            </span>
          </div>
          <button
            onClick={refreshStats}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            Actualizar
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* Llamadas Hoy */}
        <StatCard
          icon={<Phone size={24} />}
          title="Llamadas Hoy"
          value={stats.calls_today}
          color="blue"
        />

        {/* Llamadas Contestadas */}
        <StatCard
          icon={<CheckCircle size={24} />}
          title="Contestadas"
          value={stats.calls_answered}
          subtitle={`${stats.calls_today > 0 ? ((stats.calls_answered / stats.calls_today) * 100).toFixed(1) : 0}%`}
          color="green"
        />

        {/* Llamadas Abandonadas */}
        <StatCard
          icon={<XCircle size={24} />}
          title="Abandonadas"
          value={stats.calls_abandoned}
          subtitle={`${stats.calls_today > 0 ? ((stats.calls_abandoned / stats.calls_today) * 100).toFixed(1) : 0}%`}
          color="red"
        />

        {/* Nivel de Servicio */}
        <StatCard
          icon={<TrendingUp size={24} />}
          title="Nivel de Servicio"
          value={`${stats.service_level}%`}
          subtitle="< 20s"
          color="purple"
        />
      </div>

      {/* Agentes y Llamadas Activas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Agentes por Estado */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <Users className="mr-2" size={20} />
            Agentes ({agents.length})
          </h2>
          
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-green-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{stats.agents_ready}</div>
              <div className="text-sm text-gray-600">Listos</div>
            </div>
            <div className="bg-blue-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{stats.agents_in_call}</div>
              <div className="text-sm text-gray-600">En Llamada</div>
            </div>
            <div className="bg-yellow-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">{stats.agents_acw}</div>
              <div className="text-sm text-gray-600">ACW</div>
            </div>
            <div className="bg-orange-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">{stats.agents_paused}</div>
              <div className="text-sm text-gray-600">Pausados</div>
            </div>
          </div>

          {/* Lista de Agentes */}
          <div className="max-h-64 overflow-y-auto">
            {agents.map(agent => (
              <div key={agent.id} className="flex items-center justify-between py-2 border-b last:border-b-0">
                <div>
                  <div className="font-medium text-gray-800">{agent.name}</div>
                  <div className="text-sm text-gray-500">Ext. {agent.extension}</div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="text-right text-sm mr-2">
                    <div className="text-gray-600">{agent.calls_today} llamadas</div>
                    <div className="text-gray-500">{formatDuration(agent.avg_talk_time)}</div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(agent.status)}`}>
                    {getStatusLabel(agent.status)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Llamadas Activas */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <PhoneCall className="mr-2" size={20} />
            Llamadas Activas ({activeCalls.length})
          </h2>
          
          <div className="max-h-96 overflow-y-auto">
            {activeCalls.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No hay llamadas activas
              </div>
            ) : (
              activeCalls.map(call => (
                <div key={call.id} className="bg-gray-50 p-4 rounded-lg mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-medium text-gray-800">{call.caller_id}</div>
                    <div className="text-sm text-blue-600 font-mono">{call.duration}</div>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <div className="text-gray-600">
                      {call.agent || 'En cola...'}
                    </div>
                    <Activity className="text-green-500 animate-pulse" size={16} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Colas */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Colas ACD</h2>
        
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-4 text-gray-600">Cola</th>
                <th className="text-left py-2 px-4 text-gray-600">Estrategia</th>
                <th className="text-center py-2 px-4 text-gray-600">Agentes</th>
                <th className="text-center py-2 px-4 text-gray-600">En Espera</th>
                <th className="text-center py-2 px-4 text-gray-600">Contestadas</th>
                <th className="text-center py-2 px-4 text-gray-600">Abandonadas</th>
                <th className="text-right py-2 px-4 text-gray-600">Tiempo Espera</th>
              </tr>
            </thead>
            <tbody>
              {queues.map(queue => (
                <tr key={queue.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{queue.name}</td>
                  <td className="py-3 px-4 text-gray-600">{queue.strategy}</td>
                  <td className="py-3 px-4 text-center">{queue.members_count}</td>
                  <td className="py-3 px-4 text-center">
                    <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-sm">
                      {queue.calls_waiting}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center text-green-600">{queue.calls_answered}</td>
                  <td className="py-3 px-4 text-center text-red-600">{queue.calls_abandoned}</td>
                  <td className="py-3 px-4 text-right text-gray-600">
                    {formatDuration(queue.avg_hold_time)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Eventos Recientes */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <Clock className="mr-2" size={20} />
          Eventos Recientes
        </h2>
        
        <div className="max-h-64 overflow-y-auto space-y-2">
          {recentEvents.map(event => (
            <div key={event.id} className="flex items-start space-x-3 text-sm">
              <div className="text-gray-500 w-20">
                {event.timestamp.toLocaleTimeString()}
              </div>
              <div className="flex-1">
                <span className="font-medium text-gray-700">{event.type}</span>
                <span className="text-gray-500 ml-2">
                  {JSON.stringify(event.data).substring(0, 100)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Componente de tarjeta de estadística
const StatCard = ({ icon, title, value, subtitle, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    yellow: 'bg-yellow-50 text-yellow-600'
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className={`inline-flex p-3 rounded-lg mb-4 ${colorClasses[color]}`}>
        {icon}
      </div>
      <div className="text-3xl font-bold text-gray-800 mb-1">{value}</div>
      <div className="text-sm text-gray-600">{title}</div>
      {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
    </div>
  );
};

export default RealtimeDashboard;
