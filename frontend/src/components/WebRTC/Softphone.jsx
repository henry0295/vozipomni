import React, { useState, useEffect, useRef } from 'react';
import JsSIP from 'jssip';
import { Phone, PhoneOff, PhoneMissed, Mic, MicOff, VolumeX, Volume2 } from 'lucide-react';

const Softphone = ({ agentExtension, sipPassword, wsServer }) => {
  const [phone, setPhone] = useState(null);
  const [session, setSession] = useState(null);
  const [callStatus, setCallStatus] = useState('idle'); // idle, connecting, ringing, incall, ending
  const [registered, setRegistered] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [callNumber, setCallNumber] = useState('');
  const [callDuration, setCallDuration] = useState(0);
  const [incomingSession, setIncomingSession] = useState(null);

  const audioRef = useRef(null);
  const durationInterval = useRef(null);

  // Configurar JsSIP
  useEffect(() => {
    if (!agentExtension || !sipPassword || !wsServer) return;

    // Configuración SIP
    const socket = new JsSIP.WebSocketInterface(wsServer);
    const configuration = {
      sockets: [socket],
      uri: `sip:${agentExtension}@asterisk`,
      password: sipPassword,
      session_timers: false,
      register: true,
      contact_uri: `sip:${agentExtension}@${window.location.hostname}`,
      display_name: `Agent ${agentExtension}`,
    };

    const userAgent = new JsSIP.UA(configuration);

    // Event listeners
    userAgent.on('registered', () => {
      console.log('✓ SIP Registered');
      setRegistered(true);
    });

    userAgent.on('unregistered', () => {
      console.log('SIP Unregistered');
      setRegistered(false);
    });

    userAgent.on('registrationFailed', (e) => {
      console.error('Registration failed:', e);
      setRegistered(false);
    });

    userAgent.on('newRTCSession', (e) => {
      const newSession = e.session;

      if (newSession.direction === 'incoming') {
        console.log('Incoming call from:', newSession.remote_identity.uri.user);
        setIncomingSession(newSession);
        setCallStatus('ringing');
        setCallNumber(newSession.remote_identity.uri.user);
        
        // Reproducir ringtone
        playRingtone();
      }

      setupSessionListeners(newSession);
    });

    userAgent.start();
    setPhone(userAgent);

    return () => {
      if (userAgent) {
        userAgent.stop();
      }
    };
  }, [agentExtension, sipPassword, wsServer]);

  // Setup session event listeners
  const setupSessionListeners = (session) => {
    session.on('progress', () => {
      console.log('Call in progress');
      setCallStatus('connecting');
    });

    session.on('accepted', () => {
      console.log('Call accepted');
      setCallStatus('incall');
      stopRingtone();
      startCallTimer();
    });

    session.on('confirmed', () => {
      console.log('Call confirmed');
      setCallStatus('incall');
      
      // Attach remote audio
      const remoteAudio = session.connection.getRemoteStreams()[0];
      if (audioRef.current && remoteAudio) {
        audioRef.current.srcObject = remoteAudio;
        audioRef.current.volume = volume;
      }
    });

    session.on('ended', () => {
      console.log('Call ended');
      endCall();
    });

    session.on('failed', (e) => {
      console.log('Call failed:', e);
      endCall();
    });

    setSession(session);
  };

  // Hacer llamada
  const makeCall = (number) => {
    if (!phone || !registered) {
      alert('SIP not registered');
      return;
    }

    const target = `sip:${number}@asterisk`;
    const options = {
      mediaConstraints: {
        audio: true,
        video: false
      },
      pcConfig: {
        iceServers: [
          { urls: ['stun:stun.l.google.com:19302'] }
        ]
      }
    };

    const outgoingSession = phone.call(target, options);
    setCallNumber(number);
    setCallStatus('connecting');
  };

  // Contestar llamada
  const answerCall = () => {
    if (!incomingSession) return;

    const options = {
      mediaConstraints: {
        audio: true,
        video: false
      }
    };

    incomingSession.answer(options);
    setIncomingSession(null);
    stopRingtone();
  };

  // Rechazar llamada
  const rejectCall = () => {
    if (incomingSession) {
      incomingSession.terminate();
      setIncomingSession(null);
      setCallStatus('idle');
      stopRingtone();
    }
  };

  // Colgar llamada
  const hangupCall = () => {
    if (session) {
      session.terminate();
    }
    endCall();
  };

  // Finalizar llamada (cleanup)
  const endCall = () => {
    setCallStatus('idle');
    setSession(null);
    setCallNumber('');
    setCallDuration(0);
    setMuted(false);
    stopCallTimer();
    stopRingtone();
    
    if (audioRef.current) {
      audioRef.current.srcObject = null;
    }
  };

  // Mute/Unmute
  const toggleMute = () => {
    if (!session) return;

    if (muted) {
      session.unmute();
      setMuted(false);
    } else {
      session.mute();
      setMuted(true);
    }
  };

  // Control de volumen
  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  // Timer de duración de llamada
  const startCallTimer = () => {
    stopCallTimer();
    durationInterval.current = setInterval(() => {
      setCallDuration(prev => prev + 1);
    }, 1000);
  };

  const stopCallTimer = () => {
    if (durationInterval.current) {
      clearInterval(durationInterval.current);
      durationInterval.current = null;
    }
  };

  // Ringtone
  const playRingtone = () => {
    // Implementar reproducción de ringtone
    console.log('Playing ringtone...');
  };

  const stopRingtone = () => {
    console.log('Stopping ringtone...');
  };

  // Formatear duración
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Dial pad
  const dialPadNumbers = [
    '1', '2', '3',
    '4', '5', '6',
    '7', '8', '9',
    '*', '0', '#'
  ];

  const handleDialPadClick = (digit) => {
    if (callStatus === 'incall' && session) {
      // Enviar DTMF
      session.sendDTMF(digit);
    } else {
      setCallNumber(prev => prev + digit);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-md">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-800">Softphone</h3>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${registered ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600">
            {registered ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      {/* Audio element */}
      <audio ref={audioRef} autoPlay />

      {/* Display */}
      <div className="bg-gray-100 rounded-lg p-4 mb-4">
        <div className="text-center">
          {callStatus !== 'idle' && (
            <div className="mb-2">
              <span className="text-sm text-gray-600">
                {callStatus === 'ringing' && 'Llamada entrante...'}
                {callStatus === 'connecting' && 'Conectando...'}
                {callStatus === 'incall' && 'En llamada'}
              </span>
            </div>
          )}
          
          <div className="text-2xl font-mono text-gray-800 mb-2">
            {callNumber || '---'}
          </div>
          
          {callStatus === 'incall' && (
            <div className="text-lg font-mono text-blue-600">
              {formatDuration(callDuration)}
            </div>
          )}
        </div>
      </div>

      {/* Call Controls */}
      {callStatus === 'ringing' && incomingSession && (
        <div className="flex space-x-2 mb-4">
          <button
            onClick={answerCall}
            className="flex-1 bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center"
          >
            <Phone className="mr-2" size={20} />
            Contestar
          </button>
          <button
            onClick={rejectCall}
            className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center"
          >
            <PhoneMissed className="mr-2" size={20} />
            Rechazar
          </button>
        </div>
      )}

      {callStatus === 'incall' && (
        <div className="flex space-x-2 mb-4">
          <button
            onClick={toggleMute}
            className={`flex-1 ${muted ? 'bg-red-500 hover:bg-red-600' : 'bg-gray-500 hover:bg-gray-600'} text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center`}
          >
            {muted ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
          
          <button
            onClick={hangupCall}
            className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center"
          >
            <PhoneOff className="mr-2" size={20} />
            Colgar
          </button>
        </div>
      )}

      {callStatus === 'idle' && callNumber && (
        <button
          onClick={() => makeCall(callNumber)}
          disabled={!registered}
          className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-300 text-white font-semibold py-3 px-4 rounded-lg mb-4 flex items-center justify-center"
        >
          <Phone className="mr-2" size={20} />
          Llamar
        </button>
      )}

      {/* Dial Pad */}
      {(callStatus === 'idle' || callStatus === 'incall') && (
        <div className="grid grid-cols-3 gap-2 mb-4">
          {dialPadNumbers.map((digit) => (
            <button
              key={digit}
              onClick={() => handleDialPadClick(digit)}
              className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-4 rounded-lg text-xl transition-colors"
            >
              {digit}
            </button>
          ))}
        </div>
      )}

      {/* Volume Control */}
      {callStatus === 'incall' && (
        <div className="flex items-center space-x-3">
          <VolumeX size={20} className="text-gray-600" />
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={volume}
            onChange={handleVolumeChange}
            className="flex-1"
          />
          <Volume2 size={20} className="text-gray-600" />
        </div>
      )}

      {/* Clear button */}
      {callStatus === 'idle' && callNumber && (
        <button
          onClick={() => setCallNumber('')}
          className="w-full text-sm text-gray-600 hover:text-gray-800 mt-2"
        >
          Limpiar
        </button>
      )}
    </div>
  );
};

export default Softphone;
