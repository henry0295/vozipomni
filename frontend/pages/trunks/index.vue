<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-900">Troncales SIP</h1>
      <UButton
        icon="i-heroicons-plus"
        label="Nuevo Troncal"
        color="sky"
        @click="openCreateModal"
      />
    </div>

    <!-- Estadísticas -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <StatCard
        title="Total Troncales"
        :value="trunks.length"
        icon="i-heroicons-server"
        color="blue"
      />
      <StatCard
        title="Registrados"
        :value="registeredCount"
        icon="i-heroicons-check-circle"
        color="green"
      />
      <StatCard
        title="No Registrados"
        :value="unregisteredCount"
        icon="i-heroicons-exclamation-triangle"
        color="yellow"
      />
      <StatCard
        title="Error / Inactivos"
        :value="errorCount"
        icon="i-heroicons-x-circle"
        color="red"
      />
    </div>

    <!-- Tabla de troncales -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Lista de Troncales</h3>
          <div class="flex items-center space-x-2">
            <UButton
              icon="i-heroicons-arrow-path"
              size="xs"
              color="gray"
              variant="ghost"
              :loading="loadingStatuses"
              @click="refreshStatuses"
              title="Actualizar estados"
            />
            <UInput 
              v-model="searchQuery"
              placeholder="Buscar troncal..."
              icon="i-heroicons-magnifying-glass"
              class="w-64"
            />
          </div>
        </div>
      </template>

      <UTable 
        :rows="filteredTrunks" 
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-circle-stack-20-solid', label: 'No hay troncales configurados' }"
      >
        <!-- Nombre / Proveedor -->
        <template #name-data="{ row }">
          <div>
            <div class="font-medium text-gray-900">{{ row.name }}</div>
            <div class="text-sm text-gray-500">{{ row.description || 'Sin descripción' }}</div>
          </div>
        </template>

        <!-- Host -->
        <template #host-data="{ row }">
          <div class="text-sm">
            <div class="font-mono">{{ row.host }}:{{ row.port }}</div>
            <div class="text-gray-400 text-xs uppercase">{{ row.protocol }}</div>
          </div>
        </template>

        <!-- Tipo de troncal -->
        <template #type-data="{ row }">
          <UBadge 
            :color="trunkTypeBadgeColor(row.trunk_type)"
            :label="trunkTypeLabels[row.trunk_type] || row.trunk_type"
            variant="subtle"
            size="xs"
          />
        </template>

        <!-- Estado Asterisk (real-time) -->
        <template #asterisk_status-data="{ row }">
          <div class="flex items-center space-x-2">
            <span 
              class="inline-block w-2.5 h-2.5 rounded-full"
              :class="statusDotClass(row)"
            ></span>
            <span class="text-sm" :class="statusTextClass(row)">
              {{ getAsteriskStatus(row) }}
            </span>
          </div>
        </template>

        <!-- Activo/Inactivo -->
        <template #active-data="{ row }">
          <UToggle 
            :model-value="row.is_active"
            @update:model-value="toggleTrunk(row)"
            size="sm"
          />
        </template>

        <!-- Uso de canales -->
        <template #usage-data="{ row }">
          <div class="flex items-center space-x-2">
            <div class="flex-1 bg-gray-200 rounded-full h-1.5 w-16">
              <div 
                class="bg-sky-500 h-1.5 rounded-full transition-all" 
                :style="{ width: `${Math.min(((row.calls_active || 0) / (row.max_channels || 1)) * 100, 100)}%` }"
              ></div>
            </div>
            <span class="text-xs text-gray-500 font-mono">
              {{ row.calls_active || 0 }}/{{ row.max_channels }}
            </span>
          </div>
        </template>

        <!-- Acciones -->
        <template #actions-data="{ row }">
          <div class="flex items-center space-x-1">
            <UTooltip text="Editar">
              <UButton
                icon="i-heroicons-pencil-square"
                size="xs"
                color="sky"
                variant="ghost"
                @click="editTrunk(row)"
              />
            </UTooltip>
            <UTooltip text="Probar conexión">
              <UButton
                icon="i-heroicons-signal"
                size="xs"
                color="green"
                variant="ghost"
                :loading="testingTrunkId === row.id"
                @click="testConnection(row)"
              />
            </UTooltip>
            <UTooltip text="Ver configuración PJSIP">
              <UButton
                icon="i-heroicons-code-bracket"
                size="xs"
                color="purple"
                variant="ghost"
                @click="showConfigPreview(row)"
              />
            </UTooltip>
            <UTooltip text="Eliminar">
              <UButton
                icon="i-heroicons-trash"
                size="xs"
                color="red"
                variant="ghost"
                @click="confirmDeleteTrunk(row)"
              />
            </UTooltip>
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- ============================== -->
    <!-- MODAL CREAR/EDITAR TRONCAL     -->
    <!-- ============================== -->
    <UModal v-model="showCreateModal" :ui="{ width: 'sm:max-w-4xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              {{ editingTrunkId ? 'Editar Troncal' : 'Nueva Troncal SIP' }}
            </h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="closeModal" />
          </div>
        </template>

        <!-- Tabs de secciones -->
        <UTabs :items="formTabs" v-model="activeTab">
          <!-- ===== TAB 1: INFORMACIÓN BÁSICA ===== -->
          <template #basica="{ item }">
            <div class="space-y-5 py-4">
              <!-- Tipo de Troncal -->
              <UFormGroup label="Tipo de Troncal" required help="Selecciona el escenario que mejor describe tu conexión SIP">
                <USelectMenu
                  v-model="form.trunk_type"
                  :options="typeOptions"
                  value-attribute="value"
                  option-attribute="label"
                  @update:model-value="onTrunkTypeChange"
                />
              </UFormGroup>

              <!-- Descripción del tipo seleccionado -->
              <UAlert
                :icon="typeDescriptions[form.trunk_type]?.icon || 'i-heroicons-information-circle'"
                :color="typeDescriptions[form.trunk_type]?.color || 'blue'"
                variant="subtle"
                :title="trunkTypeLabels[form.trunk_type]"
                :description="typeDescriptions[form.trunk_type]?.text || ''"
              />

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Nombre del Troncal" required help="Identificador único. Ej: vozip_nat_trunk">
                  <UInput v-model="form.name" placeholder="mi_proveedor_sip" />
                </UFormGroup>

                <UFormGroup label="Descripción">
                  <UInput v-model="form.description" placeholder="Proveedor VoIP principal" />
                </UFormGroup>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <UFormGroup label="Host / IP / FQDN" required help="IP o dominio del SIP server del proveedor">
                  <UInput v-model="form.host" placeholder="sip.proveedor.com" />
                </UFormGroup>

                <UFormGroup label="Puerto" help="Normalmente 5060">
                  <UInput v-model.number="form.port" type="number" />
                </UFormGroup>

                <UFormGroup label="Protocolo">
                  <USelectMenu
                    v-model="form.protocol"
                    :options="[{ label: 'UDP', value: 'udp' }, { label: 'TCP', value: 'tcp' }, { label: 'TLS', value: 'tls' }]"
                    value-attribute="value"
                    option-attribute="label"
                  />
                </UFormGroup>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Máx. Canales Simultáneos">
                  <UInput v-model.number="form.max_channels" type="number" min="1" />
                </UFormGroup>

                <UFormGroup label="Idioma">
                  <USelectMenu
                    v-model="form.language"
                    :options="[{ label: 'Español', value: 'es' }, { label: 'English', value: 'en' }, { label: 'Português', value: 'pt' }]"
                    value-attribute="value"
                    option-attribute="label"
                  />
                </UFormGroup>
              </div>
            </div>
          </template>

          <!-- ===== TAB 2: AUTENTICACIÓN ===== -->
          <template #autenticacion="{ item }">
            <div class="space-y-5 py-4">
              <!-- Autenticación Saliente -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-arrow-up-right" class="text-blue-500" />
                  <h4 class="font-medium text-gray-800">Autenticación Saliente (VozipOmni → Proveedor)</h4>
                </div>

                <div class="flex items-center space-x-4">
                  <UCheckbox v-model="form.sends_auth" label="Enviar autenticación" />
                  <UCheckbox v-model="form.sends_registration" label="Enviar registro (REGISTER)" />
                </div>

                <div v-if="form.sends_auth" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Usuario" :required="form.sends_auth">
                    <UInput v-model="form.outbound_auth_username" placeholder="usuario_sip" />
                  </UFormGroup>
                  <UFormGroup label="Contraseña" :required="form.sends_auth">
                    <UInput v-model="form.outbound_auth_password" type="password" placeholder="••••••••" />
                  </UFormGroup>
                </div>

                <div v-if="form.sends_auth" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="From User" help="Usuario en el campo SIP From">
                    <UInput v-model="form.from_user" placeholder="usuario_sip" />
                  </UFormGroup>
                  <UFormGroup label="From Domain" help="Dominio en el campo SIP From">
                    <UInput v-model="form.from_domain" placeholder="sip.proveedor.com" />
                  </UFormGroup>
                </div>
              </div>

              <!-- Registro SIP -->
              <div v-if="form.sends_registration" class="border border-blue-200 bg-blue-50 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-clipboard-document-check" class="text-blue-600" />
                  <h4 class="font-medium text-blue-800">Configuración de Registro</h4>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Server URI" required help="URI del servidor para registro. Ej: sip:proveedor.com">
                    <UInput v-model="form.registration_server_uri" placeholder="sip:proveedor.com" />
                  </UFormGroup>
                  <UFormGroup label="Client URI" help="URI del cliente. Ej: sip:usuario@proveedor.com">
                    <UInput v-model="form.registration_client_uri" placeholder="sip:usuario@proveedor.com" />
                  </UFormGroup>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Intervalo de reintento (seg)">
                    <UInput v-model.number="form.registration_retry_interval" type="number" />
                  </UFormGroup>
                  <UFormGroup label="Expiración registro (seg)">
                    <UInput v-model.number="form.registration_expiration" type="number" />
                  </UFormGroup>
                </div>
              </div>

              <!-- Autenticación Entrante -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-arrow-down-left" class="text-green-500" />
                  <h4 class="font-medium text-gray-800">Autenticación Entrante (Proveedor → VozipOmni)</h4>
                </div>

                <div class="flex items-center space-x-4">
                  <UCheckbox v-model="form.accepts_auth" label="Aceptar autenticación" />
                  <UCheckbox v-model="form.accepts_registrations" label="Aceptar registros" />
                </div>

                <div v-if="form.accepts_auth" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Usuario Entrante" :required="form.accepts_auth">
                    <UInput v-model="form.inbound_auth_username" placeholder="usuario_inbound" />
                  </UFormGroup>
                  <UFormGroup label="Contraseña Entrante" :required="form.accepts_auth">
                    <UInput v-model="form.inbound_auth_password" type="password" placeholder="••••••••" />
                  </UFormGroup>
                </div>
              </div>
            </div>
          </template>

          <!-- ===== TAB 3: MEDIA Y CÓDECS ===== -->
          <template #media="{ item }">
            <div class="space-y-5 py-4">
              <!-- Códecs -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Códecs y DTMF</h4>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Códecs" help="Separados por coma, en orden de preferencia">
                    <UInput v-model="form.codec" placeholder="ulaw,alaw,g729" />
                  </UFormGroup>

                  <UFormGroup label="Modo DTMF">
                    <USelectMenu
                      v-model="form.dtmf_mode"
                      :options="dtmfOptions"
                      value-attribute="value"
                      option-attribute="label"
                    />
                  </UFormGroup>
                </div>
              </div>

              <!-- RTP / NAT -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">RTP y NAT</h4>
                
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <UCheckbox v-model="form.rtp_symmetric" label="RTP Simétrico" />
                  <UCheckbox v-model="form.force_rport" label="Forzar RPORT" />
                  <UCheckbox v-model="form.rewrite_contact" label="Reescribir Contact" />
                  <UCheckbox v-model="form.direct_media" label="Media Directa" />
                </div>

                <UAlert 
                  v-if="form.trunk_type === 'nat_provider'"
                  icon="i-heroicons-light-bulb"
                  color="amber"
                  variant="subtle"
                  title="Troncal con NAT"
                  description="Para proveedores con NAT, RTP Simétrico, Forzar RPORT y Reescribir Contact deben estar activados. Puerto SIP utilizado: UDP 5162."
                />
                <UAlert 
                  v-else-if="form.trunk_type === 'corporate' || form.trunk_type === 'pbx_lan'"
                  icon="i-heroicons-light-bulb"
                  color="blue"
                  variant="subtle"
                  title="Troncal sin NAT"
                  description="Para troncales en LAN o backbone corporativo, las opciones de NAT deben estar desactivadas. Puerto SIP utilizado: UDP 5161."
                />
              </div>

              <!-- Caller ID -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Caller ID</h4>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Caller ID (número)" help="Número que se mostrará en llamadas salientes">
                    <UInput v-model="form.caller_id" placeholder="+573001234567" />
                  </UFormGroup>
                  <UFormGroup label="Nombre Caller ID">
                    <UInput v-model="form.caller_id_name" placeholder="VozipOmni" />
                  </UFormGroup>
                </div>
              </div>
            </div>
          </template>

          <!-- ===== TAB 4: DIALPLAN Y AVANZADOS ===== -->
          <template #avanzado="{ item }">
            <div class="space-y-5 py-4">
              <!-- Contexto de Dialplan -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Contexto de Dialplan</h4>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Contexto" help="Punto de entrada en el dialplan para llamadas entrantes por esta troncal">
                    <USelectMenu
                      v-model="form.context"
                      :options="contextOptions"
                      value-attribute="value"
                      option-attribute="label"
                    />
                  </UFormGroup>

                  <UFormGroup v-if="form.context === 'custom'" label="Contexto Personalizado" required>
                    <UInput v-model="form.custom_context" placeholder="mi-contexto" />
                  </UFormGroup>
                </div>

                <UAlert
                  icon="i-heroicons-information-circle"
                  color="blue"
                  variant="subtle"
                >
                  <template #description>
                    <ul class="text-sm space-y-1">
                      <li><strong>from-pstn:</strong> Llamadas desde proveedor PSTN → ruteo por DIDs/IVR</li>
                      <li><strong>from-pbx:</strong> Llamadas desde PBX LAN → permite contactar agentes directamente</li>
                      <li><strong>from-trunk:</strong> Redirección genérica al contexto from-pstn</li>
                    </ul>
                  </template>
                </UAlert>
              </div>

              <!-- Session Timers -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Session Timers</h4>
                
                <UCheckbox v-model="form.timers" label="Habilitar Session Timers" />

                <div v-if="form.timers" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Min SE (seg)" help="Mínimo intervalo de Session-Expires">
                    <UInput v-model.number="form.timers_min_se" type="number" />
                  </UFormGroup>
                  <UFormGroup label="Session Expires (seg)" help="Tiempo de expiración de la sesión">
                    <UInput v-model.number="form.timers_sess_expires" type="number" />
                  </UFormGroup>
                </div>
              </div>

              <!-- Qualify -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Monitoreo (Qualify)</h4>
                
                <UCheckbox v-model="form.qualify_enabled" label="Habilitar Qualify (OPTIONS)" />

                <div v-if="form.qualify_enabled" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Frecuencia (seg)">
                    <UInput v-model.number="form.qualify_frequency" type="number" />
                  </UFormGroup>
                  <UFormGroup label="Timeout (seg)">
                    <UInput v-model.number="form.qualify_timeout" type="number" step="0.5" />
                  </UFormGroup>
                </div>
              </div>

              <!-- Opciones Avanzadas de Identidad -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Identidad SIP</h4>

                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <UCheckbox v-model="form.trust_id_inbound" label="Trust ID Inbound" />
                  <UCheckbox v-model="form.trust_id_outbound" label="Trust ID Outbound" />
                  <UCheckbox v-model="form.send_pai" label="Enviar PAI" />
                  <UCheckbox v-model="form.send_rpid" label="Enviar RPID" />
                </div>
              </div>

              <!-- Configuración Custom -->
              <div v-if="form.trunk_type === 'custom'" class="border border-orange-200 bg-orange-50 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-code-bracket" class="text-orange-600" />
                  <h4 class="font-medium text-orange-800">Configuración PJSIP Wizard Personalizada</h4>
                </div>

                <UTextarea
                  v-model="form.pjsip_config_custom"
                  :rows="12"
                  placeholder="type=wizard
transport=trunk-nat-transport
accepts_registrations=no
sends_auth=yes
..."
                  class="font-mono text-sm"
                />
              </div>
            </div>
          </template>
        </UTabs>

        <template #footer>
          <div class="flex justify-between items-center">
            <div class="text-sm text-gray-500">
              <span v-if="form.trunk_type === 'nat_provider'">Puerto SIP: UDP 5162</span>
              <span v-else-if="form.trunk_type !== 'custom'">Puerto SIP: UDP 5161</span>
              <span v-else>Puerto personalizado</span>
            </div>
            <div class="flex space-x-2">
              <UButton color="gray" @click="closeModal">Cancelar</UButton>
              <UButton
                icon="i-heroicons-check"
                @click="saveTrunk"
                color="primary"
                :loading="saving"
              >
                {{ editingTrunkId ? 'Actualizar' : 'Crear Troncal' }}
              </UButton>
            </div>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal de Configuración PJSIP Preview -->
    <UModal v-model="showConfigModal">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Configuración PJSIP: {{ configPreviewName }}</h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="showConfigModal = false" />
          </div>
        </template>
        <pre class="bg-gray-900 text-green-400 p-4 rounded-lg text-sm font-mono overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap">{{ configPreviewContent }}</pre>
      </UCard>
    </UModal>

    <!-- Modal de confirmación para eliminar -->
    <ConfirmModal
      v-model="showDeleteModal"
      title="Eliminar Troncal"
      :message="`¿Estás seguro de eliminar la troncal '${deletingTrunk?.name}'? Esta acción no se puede deshacer.`"
      confirm-text="Eliminar"
      confirm-color="red"
      @confirm="doDeleteTrunk"
    />
  </div>
</template>

<script setup lang="ts">
import type { SipTrunk } from '~/types'

definePageMeta({
  layout: 'default',
  middleware: 'auth'
})

// ===== ESTADOS =====
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const showConfigModal = ref(false)
const showDeleteModal = ref(false)
const editingTrunkId = ref<number | null>(null)
const searchQuery = ref('')
const activeTab = ref(0)
const loadingStatuses = ref(false)
const testingTrunkId = ref<number | null>(null)
const configPreviewName = ref('')
const configPreviewContent = ref('')
const deletingTrunk = ref<SipTrunk | null>(null)

const { 
  getTrunks, createTrunk, updateTrunk, deleteTrunk: deleteTrunkApi, 
  toggleTrunkStatus, testTrunkConnection, getTrunkStatuses,
  forceRegister, previewConfig 
} = useTrunks()

const trunks = ref<SipTrunk[]>([])
const trunkStatuses = ref<Record<string, { status: string; class: string }>>({})

// ===== FORMULARIO =====
const defaultForm = () => ({
  name: '',
  description: '',
  trunk_type: 'nat_provider',
  host: '',
  port: 5060,
  protocol: 'udp',
  // Auth saliente
  sends_auth: true,
  outbound_auth_username: '',
  outbound_auth_password: '',
  from_user: '',
  from_domain: '',
  // Registro
  sends_registration: true,
  registration_server_uri: '',
  registration_client_uri: '',
  registration_retry_interval: 60,
  registration_expiration: 3600,
  // Auth entrante
  accepts_auth: false,
  accepts_registrations: false,
  inbound_auth_username: '',
  inbound_auth_password: '',
  // RTP/Media
  rtp_symmetric: true,
  force_rport: true,
  rewrite_contact: true,
  direct_media: false,
  // Codecs
  codec: 'ulaw,alaw',
  dtmf_mode: 'rfc4733',
  // Context
  context: 'from-pstn',
  custom_context: '',
  timers: true,
  timers_min_se: 90,
  timers_sess_expires: 1800,
  // Qualify
  qualify_enabled: true,
  qualify_frequency: 60,
  qualify_timeout: 3.0,
  // Canales
  max_channels: 10,
  caller_id: '',
  caller_id_name: '',
  // Avanzado
  language: 'es',
  trust_id_inbound: false,
  trust_id_outbound: false,
  send_pai: false,
  send_rpid: false,
  // Custom
  pjsip_config_custom: '',
  is_active: true,
})

const form = reactive(defaultForm())

// ===== OPCIONES =====
const typeOptions = [
  { label: 'Proveedor con NAT', value: 'nat_provider' },
  { label: 'Proveedor sin NAT', value: 'no_nat_provider' },
  { label: 'PBX en LAN', value: 'pbx_lan' },
  { label: 'Troncal Corporativa', value: 'corporate' },
  { label: 'Personalizado (Custom)', value: 'custom' }
]

const trunkTypeLabels: Record<string, string> = {
  nat_provider: 'Proveedor con NAT',
  no_nat_provider: 'Proveedor sin NAT',
  pbx_lan: 'PBX en LAN',
  corporate: 'Corporativa',
  custom: 'Personalizado'
}

const typeDescriptions: Record<string, { text: string; icon: string; color: string }> = {
  nat_provider: {
    text: 'VozipOmni detrás de NAT (cloud, LAN corporativa). Usa trunk-nat-transport (puerto UDP 5162). Requiere registro y autenticación con el proveedor SIP.',
    icon: 'i-heroicons-cloud',
    color: 'blue'
  },
  no_nat_provider: {
    text: 'VozipOmni con IP pública (VPS) conectado a proveedor SIP en Internet. Sin tratamiento NAT, puerto UDP 5161. Requiere registro y autenticación.',
    icon: 'i-heroicons-globe-alt',
    color: 'sky'
  },
  pbx_lan: {
    text: 'Conexión bidireccional con PBX IP en LAN. Autenticación en ambas direcciones, sin NAT ni registro. Puerto UDP 5161. Contexto from-pbx permite contactar agentes.',
    icon: 'i-heroicons-building-office',
    color: 'violet'
  },
  corporate: {
    text: 'Backbone privado corporativo (proveedor con conectividad dedicada). Sin autenticación, sin registro, sin NAT. Puerto UDP 5161.',
    icon: 'i-heroicons-building-library',
    color: 'emerald'
  },
  custom: {
    text: 'Configuración PJSIP Wizard manual. El administrador escribe la configuración raw en la pestaña Avanzado.',
    icon: 'i-heroicons-code-bracket',
    color: 'orange'
  }
}

const dtmfOptions = [
  { label: 'RFC4733 (Recomendado)', value: 'rfc4733' },
  { label: 'RFC2833', value: 'rfc2833' },
  { label: 'Inband', value: 'inband' },
  { label: 'SIP INFO', value: 'info' },
  { label: 'Auto', value: 'auto' }
]

const contextOptions = [
  { label: 'Desde PSTN (from-pstn)', value: 'from-pstn' },
  { label: 'Desde PBX (from-pbx)', value: 'from-pbx' },
  { label: 'Desde Troncal (from-trunk)', value: 'from-trunk' },
  { label: 'Personalizado', value: 'custom' }
]

const formTabs = [
  { label: 'Información Básica', slot: 'basica', icon: 'i-heroicons-server' },
  { label: 'Autenticación', slot: 'autenticacion', icon: 'i-heroicons-key' },
  { label: 'Media y Códecs', slot: 'media', icon: 'i-heroicons-speaker-wave' },
  { label: 'Avanzado', slot: 'avanzado', icon: 'i-heroicons-cog-6-tooth' }
]

// Columnas de la tabla
const columns = [
  { key: 'name', label: 'Nombre / Descripción' },
  { key: 'host', label: 'Host' },
  { key: 'type', label: 'Tipo' },
  { key: 'asterisk_status', label: 'Estado Asterisk' },
  { key: 'active', label: 'Activo' },
  { key: 'usage', label: 'Canales' },
  { key: 'actions', label: 'Acciones' }
]

// ===== COMPUTADAS =====
const registeredCount = computed(() => {
  return trunks.value.filter(t => {
    const s = trunkStatuses.value[String(t.id)]
    return s && s.class === 'success'
  }).length
})

const unregisteredCount = computed(() => {
  return trunks.value.filter(t => {
    const s = trunkStatuses.value[String(t.id)]
    return s && s.class === 'warning'
  }).length
})

const errorCount = computed(() => {
  return trunks.value.filter(t => {
    const s = trunkStatuses.value[String(t.id)]
    return !t.is_active || (s && s.class === 'error')
  }).length
})

const filteredTrunks = computed(() => {
  if (!searchQuery.value) return trunks.value
  const q = searchQuery.value.toLowerCase()
  return trunks.value.filter(t =>
    t.name.toLowerCase().includes(q) ||
    (t.description || '').toLowerCase().includes(q) ||
    t.host.toLowerCase().includes(q)
  )
})

// ===== FUNCIONES DE ESTADO =====
const getAsteriskStatus = (trunk: SipTrunk): string => {
  if (!trunk.is_active) return 'Inactivo'
  const s = trunkStatuses.value[String(trunk.id)]
  return s?.status || 'Consultando...'
}

const statusDotClass = (trunk: SipTrunk): string => {
  if (!trunk.is_active) return 'bg-gray-400'
  const s = trunkStatuses.value[String(trunk.id)]
  if (!s) return 'bg-gray-300 animate-pulse'
  
  const map: Record<string, string> = {
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
    gray: 'bg-gray-400'
  }
  return map[s.class] || 'bg-gray-400'
}

const statusTextClass = (trunk: SipTrunk): string => {
  if (!trunk.is_active) return 'text-gray-400'
  const s = trunkStatuses.value[String(trunk.id)]
  if (!s) return 'text-gray-400'
  
  const map: Record<string, string> = {
    success: 'text-green-700',
    warning: 'text-yellow-700',
    error: 'text-red-700',
    gray: 'text-gray-500'
  }
  return map[s.class] || 'text-gray-500'
}

const trunkTypeBadgeColor = (type: string): string => {
  const map: Record<string, string> = {
    nat_provider: 'blue',
    no_nat_provider: 'sky',
    pbx_lan: 'violet',
    corporate: 'emerald',
    custom: 'orange'
  }
  return map[type] || 'gray'
}

// ===== PRESET POR TIPO (OmniLeads) =====
const onTrunkTypeChange = (type: string) => {
  switch (type) {
    case 'nat_provider':
      Object.assign(form, {
        sends_auth: true, sends_registration: true,
        accepts_auth: false, accepts_registrations: false,
        rtp_symmetric: true, force_rport: true, rewrite_contact: true,
        direct_media: false, context: 'from-pstn', timers: true, qualify_enabled: true,
      })
      break
    case 'no_nat_provider':
      Object.assign(form, {
        sends_auth: true, sends_registration: true,
        accepts_auth: false, accepts_registrations: false,
        rtp_symmetric: true, force_rport: true, rewrite_contact: true,
        direct_media: false, context: 'from-pstn', timers: true, qualify_enabled: true,
      })
      break
    case 'pbx_lan':
      Object.assign(form, {
        sends_auth: true, sends_registration: false,
        accepts_auth: true, accepts_registrations: false,
        rtp_symmetric: false, force_rport: false, rewrite_contact: false,
        direct_media: false, context: 'from-pbx', timers: true, qualify_enabled: true,
      })
      break
    case 'corporate':
      Object.assign(form, {
        sends_auth: false, sends_registration: false,
        accepts_auth: false, accepts_registrations: false,
        rtp_symmetric: false, force_rport: false, rewrite_contact: false,
        direct_media: false, context: 'from-pstn', timers: true, qualify_enabled: true,
      })
      break
  }
}

// ===== ACCIONES =====
const openCreateModal = () => {
  Object.assign(form, defaultForm())
  editingTrunkId.value = null
  activeTab.value = 0
  showCreateModal.value = true
}

const editTrunk = (trunk: SipTrunk) => {
  Object.assign(form, {
    name: trunk.name,
    description: trunk.description || '',
    trunk_type: trunk.trunk_type,
    host: trunk.host,
    port: trunk.port,
    protocol: trunk.protocol || 'udp',
    sends_auth: trunk.sends_auth,
    outbound_auth_username: trunk.outbound_auth_username || '',
    outbound_auth_password: '',
    from_user: trunk.from_user || '',
    from_domain: trunk.from_domain || '',
    sends_registration: trunk.sends_registration,
    registration_server_uri: trunk.registration_server_uri || '',
    registration_client_uri: trunk.registration_client_uri || '',
    registration_retry_interval: trunk.registration_retry_interval || 60,
    registration_expiration: trunk.registration_expiration || 3600,
    accepts_auth: trunk.accepts_auth,
    accepts_registrations: trunk.accepts_registrations,
    inbound_auth_username: trunk.inbound_auth_username || '',
    inbound_auth_password: '',
    rtp_symmetric: trunk.rtp_symmetric,
    force_rport: trunk.force_rport,
    rewrite_contact: trunk.rewrite_contact,
    direct_media: trunk.direct_media,
    codec: trunk.codec || 'ulaw,alaw',
    dtmf_mode: trunk.dtmf_mode || 'rfc4733',
    context: trunk.context || 'from-pstn',
    custom_context: trunk.custom_context || '',
    timers: trunk.timers ?? true,
    timers_min_se: trunk.timers_min_se || 90,
    timers_sess_expires: trunk.timers_sess_expires || 1800,
    qualify_enabled: trunk.qualify_enabled ?? true,
    qualify_frequency: trunk.qualify_frequency || 60,
    qualify_timeout: trunk.qualify_timeout || 3.0,
    max_channels: trunk.max_channels || 10,
    caller_id: trunk.caller_id || '',
    caller_id_name: trunk.caller_id_name || '',
    language: trunk.language || 'es',
    trust_id_inbound: trunk.trust_id_inbound,
    trust_id_outbound: trunk.trust_id_outbound,
    send_pai: trunk.send_pai,
    send_rpid: trunk.send_rpid,
    pjsip_config_custom: trunk.pjsip_config_custom || '',
    is_active: trunk.is_active,
  })
  editingTrunkId.value = trunk.id
  activeTab.value = 0
  showCreateModal.value = true
}

const saveTrunk = async () => {
  saving.value = true
  const payload: any = { ...form }
  
  // No enviar contraseña vacía en edición
  if (editingTrunkId.value) {
    if (!payload.outbound_auth_password) delete payload.outbound_auth_password
    if (!payload.inbound_auth_password) delete payload.inbound_auth_password
  }

  try {
    if (editingTrunkId.value) {
      const result = await updateTrunk(editingTrunkId.value, payload)
      if (result.error) { console.error('Error:', result.error); return }
    } else {
      const result = await createTrunk(payload)
      if (result.error) { console.error('Error:', result.error); return }
    }
    await loadTrunks()
    closeModal()
  } finally {
    saving.value = false
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingTrunkId.value = null
  activeTab.value = 0
}

const toggleTrunk = async (trunk: SipTrunk) => {
  await toggleTrunkStatus(trunk.id)
  await loadTrunks()
}

const confirmDeleteTrunk = (trunk: SipTrunk) => {
  deletingTrunk.value = trunk
  showDeleteModal.value = true
}

const doDeleteTrunk = async () => {
  if (!deletingTrunk.value) return
  const result = await deleteTrunkApi(deletingTrunk.value.id)
  if (!result.error) await loadTrunks()
  showDeleteModal.value = false
  deletingTrunk.value = null
}

const testConnection = async (trunk: SipTrunk) => {
  testingTrunkId.value = trunk.id
  try {
    const result = await testTrunkConnection(trunk.id)
    if (result.data) {
      const d = result.data as any
      trunkStatuses.value[String(trunk.id)] = {
        status: d.status || (d.registered ? 'Registrado' : 'No Registrado'),
        class: d.available || d.registered ? 'success' : 'warning'
      }
    }
  } catch (e) {
    trunkStatuses.value[String(trunk.id)] = { status: 'Error', class: 'error' }
  } finally {
    testingTrunkId.value = null
  }
}

const showConfigPreview = async (trunk: SipTrunk) => {
  configPreviewName.value = trunk.name
  configPreviewContent.value = 'Cargando...'
  showConfigModal.value = true
  
  const result = await previewConfig(trunk.id)
  if (result.data) {
    configPreviewContent.value = (result.data as any).config || 'Sin configuración'
  } else {
    configPreviewContent.value = 'Error al obtener configuración'
  }
}

// ===== CARGA DE DATOS =====
const loadTrunks = async () => {
  loading.value = true
  const result = await getTrunks()
  trunks.value = result.data || []
  loading.value = false
  refreshStatuses()
}

const refreshStatuses = async () => {
  if (trunks.value.length === 0) return
  loadingStatuses.value = true
  try {
    const result = await getTrunkStatuses()
    if (result.data) {
      trunkStatuses.value = result.data as any
    }
  } catch (e) {
    console.error('Error cargando estados:', e)
  } finally {
    loadingStatuses.value = false
  }
}

// Auto-refresh cada 30 segundos
let statusInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  loadTrunks()
  statusInterval = setInterval(refreshStatuses, 30000)
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})

useHead({
  title: 'Troncales SIP - VozipOmni'
})
</script>