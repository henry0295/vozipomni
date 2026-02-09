# Generated migration for SIPTrunk model expansion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0001_initial'),  # Ajustar al número de migración anterior
    ]

    operations = [
        # Agregar nuevos campos al modelo SIPTrunk
        migrations.AddField(
            model_name='siptrunk',
            name='description',
            field=models.TextField(blank=True, verbose_name='Descripción'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='trunk_type',
            field=models.CharField(
                choices=[
                    ('nat_provider', 'Proveedor con NAT'),
                    ('no_nat_provider', 'Proveedor sin NAT'),
                    ('pbx_lan', 'PBX en LAN'),
                    ('corporate', 'Troncal Corporativa'),
                    ('custom', 'Personalizado')
                ],
                default='nat_provider',
                max_length=20,
                verbose_name='Tipo de Troncal'
            ),
        ),
        
        # Renombrar campos existentes
        migrations.RenameField(
            model_name='siptrunk',
            old_name='username',
            new_name='outbound_auth_username',
        ),
        migrations.RenameField(
            model_name='siptrunk',
            old_name='password',
            new_name='outbound_auth_password',
        ),
        
        # Modificar campo protocol
        migrations.AddField(
            model_name='siptrunk',
            name='protocol',
            field=models.CharField(
                choices=[('udp', 'UDP'), ('tcp', 'TCP'), ('tls', 'TLS')],
                default='udp',
                max_length=10,
                verbose_name='Protocolo'
            ),
        ),
        
        # Campos de autenticación entrante
        migrations.AddField(
            model_name='siptrunk',
            name='inbound_auth_username',
            field=models.CharField(blank=True, max_length=100, verbose_name='Usuario Entrante'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='inbound_auth_password',
            field=models.CharField(blank=True, max_length=100, verbose_name='Contraseña Entrante'),
        ),
        
        # Campos de From User/Domain
        migrations.AddField(
            model_name='siptrunk',
            name='from_user',
            field=models.CharField(blank=True, max_length=100, verbose_name='From User'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='from_domain',
            field=models.CharField(blank=True, max_length=200, verbose_name='From Domain'),
        ),
        
        # Campos de Registro
        migrations.AddField(
            model_name='siptrunk',
            name='sends_registration',
            field=models.BooleanField(default=True, verbose_name='Enviar Registro'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='registration_server_uri',
            field=models.CharField(
                blank=True,
                help_text='Ej: sip:proveedor.com o sip:proveedor.com:5060',
                max_length=200,
                verbose_name='Server URI para Registro'
            ),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='registration_client_uri',
            field=models.CharField(
                blank=True,
                help_text='Ej: sip:usuario@proveedor.com',
                max_length=200,
                verbose_name='Client URI para Registro'
            ),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='registration_retry_interval',
            field=models.IntegerField(default=60, verbose_name='Intervalo de Reintento (seg)'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='registration_expiration',
            field=models.IntegerField(default=3600, verbose_name='Expiración Registro (seg)'),
        ),
        
        # Campos de comportamiento SIP
        migrations.AddField(
            model_name='siptrunk',
            name='sends_auth',
            field=models.BooleanField(default=True, verbose_name='Enviar Autenticación'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='accepts_auth',
            field=models.BooleanField(default=False, verbose_name='Aceptar Autenticación'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='accepts_registrations',
            field=models.BooleanField(default=False, verbose_name='Aceptar Registros'),
        ),
        
        # Campos RTP/Media
        migrations.AddField(
            model_name='siptrunk',
            name='rtp_symmetric',
            field=models.BooleanField(default=True, verbose_name='RTP Simétrico'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='force_rport',
            field=models.BooleanField(default=True, verbose_name='Forzar RPORT'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='rewrite_contact',
            field=models.BooleanField(default=True, verbose_name='Reescribir Contact'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='direct_media',
            field=models.BooleanField(default=False, verbose_name='Media Directa'),
        ),
        
        # Modificar campo dtmf_mode
        migrations.AlterField(
            model_name='siptrunk',
            name='dtmf_mode',
            field=models.CharField(
                choices=[
                    ('rfc4733', 'RFC4733 (Recomendado)'),
                    ('rfc2833', 'RFC2833'),
                    ('inband', 'Inband'),
                    ('info', 'SIP INFO'),
                    ('auto', 'Auto')
                ],
                default='rfc4733',
                max_length=20,
                verbose_name='Modo DTMF'
            ),
        ),
        
        # Campos de Context
        migrations.AddField(
            model_name='siptrunk',
            name='context',
            field=models.CharField(
                choices=[
                    ('from-pstn', 'Desde PSTN'),
                    ('from-pbx', 'Desde PBX'),
                    ('from-trunk', 'Desde Troncal'),
                    ('custom', 'Personalizado')
                ],
                default='from-pstn',
                max_length=50,
                verbose_name='Contexto Dialplan'
            ),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='custom_context',
            field=models.CharField(blank=True, max_length=50, verbose_name='Contexto Personalizado'),
        ),
        
        # Campos de Timers
        migrations.AddField(
            model_name='siptrunk',
            name='timers',
            field=models.BooleanField(default=True, verbose_name='Session Timers'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='timers_min_se',
            field=models.IntegerField(default=90, verbose_name='Min SE (seg)'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='timers_sess_expires',
            field=models.IntegerField(default=1800, verbose_name='Session Expires (seg)'),
        ),
        
        # Campos de Qualify
        migrations.AddField(
            model_name='siptrunk',
            name='qualify_enabled',
            field=models.BooleanField(default=True, verbose_name='Habilitar Qualify'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='qualify_frequency',
            field=models.IntegerField(default=60, verbose_name='Frecuencia Qualify (seg)'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='qualify_timeout',
            field=models.FloatField(default=3.0, verbose_name='Timeout Qualify (seg)'),
        ),
        
        # Campos de Caller ID
        migrations.AddField(
            model_name='siptrunk',
            name='caller_id',
            field=models.CharField(blank=True, max_length=50, verbose_name='Caller ID'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='caller_id_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Nombre Caller ID'),
        ),
        
        # Campos de NAT
        migrations.AddField(
            model_name='siptrunk',
            name='local_net',
            field=models.CharField(
                blank=True,
                help_text='Ej: 192.168.0.0/16, 10.0.0.0/8',
                max_length=100,
                verbose_name='Red Local'
            ),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='external_media_address',
            field=models.CharField(
                blank=True,
                help_text='IP pública para RTP cuando está detrás de NAT',
                max_length=100,
                verbose_name='IP Externa Media'
            ),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='external_signaling_address',
            field=models.CharField(
                blank=True,
                help_text='IP pública para SIP cuando está detrás de NAT',
                max_length=100,
                verbose_name='IP Externa Señalización'
            ),
        ),
        
        # Campos de opciones avanzadas
        migrations.AddField(
            model_name='siptrunk',
            name='language',
            field=models.CharField(default='es', max_length=10, verbose_name='Idioma'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='trust_id_inbound',
            field=models.BooleanField(default=False, verbose_name='Confiar en ID Entrante'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='trust_id_outbound',
            field=models.BooleanField(default=False, verbose_name='Confiar en ID Saliente'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='send_pai',
            field=models.BooleanField(default=False, verbose_name='Enviar P-Asserted-Identity'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='send_rpid',
            field=models.BooleanField(default=False, verbose_name='Enviar Remote-Party-ID'),
        ),
        
        # Campos de estado
        migrations.AddField(
            model_name='siptrunk',
            name='last_registration_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Última Registro'),
        ),
        
        # Campos de estadísticas
        migrations.AddField(
            model_name='siptrunk',
            name='calls_successful',
            field=models.IntegerField(default=0, verbose_name='Llamadas exitosas'),
        ),
        migrations.AddField(
            model_name='siptrunk',
            name='calls_failed',
            field=models.IntegerField(default=0, verbose_name='Llamadas fallidas'),
        ),
        
        # Configuración personalizada
        migrations.AddField(
            model_name='siptrunk',
            name='pjsip_config_custom',
            field=models.TextField(
                blank=True,
                help_text='Solo para tipo "Personalizado". Configuración PJSIP Wizard raw.',
                verbose_name='Configuración PJSIP Personalizada'
            ),
        ),
        
        # Modificar campo codec
        migrations.AlterField(
            model_name='siptrunk',
            name='codec',
            field=models.CharField(
                default='ulaw,alaw,g729',
                help_text='Separados por coma',
                max_length=100,
                verbose_name='Códecs'
            ),
        ),
    ]
