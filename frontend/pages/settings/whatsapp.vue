<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">WhatsApp Business</h1>
        <p class="text-sm text-gray-500 mt-1">
          Integración directa con la API de WhatsApp Cloud de Meta: proveedor (App de Meta) → líneas (números) → plantillas.
        </p>
      </div>
      <UButton icon="i-heroicons-book-open" color="gray" variant="outline" @click="tab = 3">Guía de configuración</UButton>
    </div>

    <UTabs v-model="tab" :items="tabs" />

    <!-- ═══════════════ PROVEEDORES ═══════════════ -->
    <div v-if="tab === 0" class="space-y-4">
      <div class="flex justify-between items-center">
        <p class="text-sm text-gray-500">Un proveedor es una App de Meta con su token de Usuario del Sistema. Puede tener varias líneas.</p>
        <UButton icon="i-heroicons-plus" @click="openProvider()">Nuevo proveedor</UButton>
      </div>

      <div v-if="loadingProviders" class="py-10 text-center text-gray-400">Cargando…</div>
      <UCard v-else-if="!providers.length">
        <div class="py-8 text-center space-y-3">
          <UIcon name="i-heroicons-chat-bubble-oval-left-ellipsis" class="w-12 h-12 text-gray-300 mx-auto" />
          <p class="text-gray-500">Aún no hay proveedores. Crea uno con los datos de tu App de Meta.</p>
          <UButton @click="openProvider()">Crear proveedor</UButton>
        </div>
      </UCard>

      <UCard v-for="p in providers" :key="p.id">
        <template #header>
          <div class="flex flex-wrap items-center gap-3">
            <UIcon name="i-heroicons-building-office-2" class="w-5 h-5 text-green-600" />
            <h3 class="font-semibold">{{ p.name }}</h3>
            <UBadge color="gray" variant="soft">App ID {{ p.app_id }}</UBadge>
            <UBadge :color="p.is_active ? 'green' : 'gray'" variant="soft">{{ p.is_active ? 'Activo' : 'Inactivo' }}</UBadge>
            <UBadge :color="p.webhook_verified ? 'green' : 'amber'" variant="soft">
              {{ p.webhook_verified ? 'Webhook verificado' : 'Webhook sin verificar' }}
            </UBadge>
            <div class="ml-auto flex gap-1">
              <UButton size="xs" icon="i-heroicons-signal" color="gray" variant="outline" :loading="busy === `ptest-${p.id}`" @click="testProvider(p)">Probar token</UButton>
              <UButton size="xs" icon="i-heroicons-pencil" color="gray" variant="ghost" @click="openProvider(p)" />
              <UButton size="xs" icon="i-heroicons-trash" color="red" variant="ghost" @click="removeProvider(p)" />
            </div>
          </div>
        </template>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="space-y-3">
            <UFormGroup label="Callback URL (Webhook)" hint="Pégala en Meta → WhatsApp → Configuración">
              <div class="flex gap-2">
                <UInput :model-value="p.webhook_url" readonly class="flex-1 font-mono text-xs" />
                <UButton icon="i-heroicons-clipboard-document" color="gray" variant="outline" @click="copy(p.webhook_url)" />
              </div>
            </UFormGroup>
            <UFormGroup label="Token de verificación (Verify token)">
              <div class="flex gap-2">
                <UInput :model-value="p.verify_token" readonly class="flex-1 font-mono text-xs" />
                <UButton icon="i-heroicons-clipboard-document" color="gray" variant="outline" @click="copy(p.verify_token)" />
                <UButton icon="i-heroicons-arrow-path" color="gray" variant="outline" title="Regenerar" :loading="busy === `regen-${p.id}`" @click="regenerateToken(p)" />
              </div>
            </UFormGroup>
            <UAlert v-if="p.webhook_url && !p.webhook_url.startsWith('https://')" color="amber" variant="soft" icon="i-heroicons-exclamation-triangle"
                    description="Meta solo acepta URLs HTTPS con certificado válido. Configura PUBLIC_BASE_URL con tu dominio público." />
            <UAlert v-else-if="isIpUrl(p.webhook_url)" color="amber" variant="soft" icon="i-heroicons-exclamation-triangle"
                    description="La URL usa una IP. Meta exige un dominio público con certificado SSL válido (no autofirmado). Define PUBLIC_BASE_URL=https://tu-dominio en el .env." />
          </div>
          <div class="text-sm space-y-2">
            <div class="flex justify-between"><span class="text-gray-500">Token de acceso</span>
              <span>{{ p.has_access_token ? `Configurado ${p.access_token_hint}` : 'No configurado' }}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">App Secret (firma)</span>
              <UBadge :color="p.has_app_secret ? 'green' : 'amber'" variant="soft" size="xs">{{ p.has_app_secret ? 'Configurado' : 'Sin configurar (no se valida la firma)' }}</UBadge></div>
            <div class="flex justify-between"><span class="text-gray-500">Versión Graph API</span><span>{{ p.api_version }}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">Business ID</span><span>{{ p.business_id || '—' }}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">Líneas</span><span>{{ p.lines_count }}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">Último evento recibido</span><span>{{ fmtDateTime(p.last_webhook_at) }}</span></div>
            <UAlert v-if="p.last_error" color="red" variant="soft" :description="p.last_error" />
          </div>
        </div>
      </UCard>
    </div>

    <!-- ═══════════════ LÍNEAS ═══════════════ -->
    <div v-if="tab === 1" class="space-y-4">
      <div class="flex justify-between items-center">
        <p class="text-sm text-gray-500">Cada línea es un número de WhatsApp Business (Phone Number ID) dentro de una cuenta (WABA).</p>
        <UButton icon="i-heroicons-plus" :disabled="!providers.length" @click="openLine()">Nueva línea</UButton>
      </div>
      <UAlert v-if="!providers.length" color="amber" variant="soft" icon="i-heroicons-information-circle"
              description="Primero crea un proveedor en la pestaña Proveedores." />

      <UCard>
        <UTable :rows="lines" :columns="lineColumns" :loading="loadingLines"
                :empty-state="{ icon: 'i-heroicons-device-phone-mobile', label: 'No hay líneas configuradas' }">
          <template #name-data="{ row }">
            <div>
              <p class="font-medium">{{ row.name }}</p>
              <p class="text-xs text-gray-500">{{ row.provider_name }}</p>
            </div>
          </template>
          <template #number-data="{ row }">
            <div>
              <p>{{ row.display_phone_number || '—' }}</p>
              <p class="text-xs text-gray-500">{{ row.verified_name || `ID ${row.phone_number_id}` }}</p>
            </div>
          </template>
          <template #status-data="{ row }">
            <UBadge :color="lineStatusColor(row.status)" variant="soft">{{ lineStatusLabel(row.status) }}</UBadge>
            <p v-if="row.status_detail" class="text-xs text-red-500 mt-1 max-w-xs truncate" :title="row.status_detail">{{ row.status_detail }}</p>
          </template>
          <template #quality_rating-data="{ row }">
            <UBadge v-if="row.quality_rating" :color="qualityColor(row.quality_rating)" variant="soft">{{ row.quality_rating }}</UBadge>
            <span v-else class="text-gray-400">—</span>
          </template>
          <template #webhook_subscribed-data="{ row }">
            <UBadge :color="row.webhook_subscribed ? 'green' : 'amber'" variant="soft">{{ row.webhook_subscribed ? 'Suscrita' : 'No suscrita' }}</UBadge>
          </template>
          <template #routing-data="{ row }">
            <div class="text-xs">
              <p>{{ row.default_campaign_name || 'Sin campaña' }}</p>
              <p class="text-gray-500">{{ row.auto_assign ? `Auto-asignar · máx ${row.max_chats_per_agent}` : 'Asignación manual' }}</p>
            </div>
          </template>
          <template #actions-data="{ row }">
            <div class="flex gap-1 justify-end">
              <UDropdown :items="lineActions(row)">
                <UButton size="xs" color="gray" variant="outline" trailing-icon="i-heroicons-chevron-down"
                         :loading="busy.startsWith('line-') && busy.endsWith(`-${row.id}`)">Acciones</UButton>
              </UDropdown>
              <UButton size="xs" icon="i-heroicons-pencil" color="gray" variant="ghost" @click="openLine(row)" />
              <UButton size="xs" icon="i-heroicons-trash" color="red" variant="ghost" @click="removeLine(row)" />
            </div>
          </template>
        </UTable>
      </UCard>
    </div>

    <!-- ═══════════════ PLANTILLAS ═══════════════ -->
    <div v-if="tab === 2" class="space-y-4">
      <div class="flex flex-wrap gap-2 items-center">
        <USelect v-model="tplLine" :options="[{ label: 'Todas las líneas', value: '' }, ...lineOptions]" class="w-64" @change="loadTemplates" />
        <USelect v-model="tplStatus" :options="[{ label: 'Todos los estados', value: '' }, { label: 'Aprobadas', value: 'APPROVED' }, { label: 'Pendientes', value: 'PENDING' }, { label: 'Rechazadas', value: 'REJECTED' }]" class="w-48" @change="loadTemplates" />
        <div class="ml-auto flex gap-2">
          <UButton icon="i-heroicons-arrow-path" color="gray" variant="outline" :disabled="!tplLine" :loading="busy === `line-sync-${tplLine}`"
                   title="Selecciona una línea" @click="syncTemplates(lines.find(l => String(l.id) === tplLine))">Sincronizar con Meta</UButton>
          <UButton icon="i-heroicons-plus" :disabled="!lines.length" @click="openTemplate()">Nueva plantilla</UButton>
        </div>
      </div>
      <UAlert color="primary" variant="soft" icon="i-heroicons-information-circle"
              description="Fuera de la ventana de 24 h desde el último mensaje del cliente, WhatsApp solo permite enviar plantillas aprobadas por Meta. Las plantillas nuevas quedan en PENDING hasta su revisión." />

      <UCard>
        <UTable :rows="templates" :columns="tplColumns" :loading="loadingTemplates"
                :empty-state="{ icon: 'i-heroicons-document-text', label: 'No hay plantillas. Sincroniza una línea o crea una nueva.' }">
          <template #name-data="{ row }">
            <div>
              <p class="font-mono text-sm">{{ row.name }}</p>
              <p class="text-xs text-gray-500">{{ row.line_name }} · {{ row.language }}</p>
            </div>
          </template>
          <template #category-data="{ row }"><UBadge color="gray" variant="soft">{{ row.category }}</UBadge></template>
          <template #status-data="{ row }">
            <UBadge :color="tplStatusColor(row.status)" variant="soft">{{ row.status || '—' }}</UBadge>
            <p v-if="row.rejected_reason && row.rejected_reason !== 'NONE'" class="text-xs text-red-500 mt-1">{{ row.rejected_reason }}</p>
          </template>
          <template #body_text-data="{ row }">
            <p class="text-sm whitespace-pre-line max-w-md line-clamp-3">{{ row.body_text }}</p>
            <p v-if="row.body_param_count" class="text-xs text-gray-500 mt-1">{{ row.body_param_count }} variable(s)</p>
          </template>
          <template #actions-data="{ row }">
            <UButton size="xs" icon="i-heroicons-trash" color="red" variant="ghost" @click="removeTemplate(row)" />
          </template>
        </UTable>
      </UCard>
    </div>

    <!-- ═══════════════ GUÍA ═══════════════ -->
    <div v-if="tab === 3" class="space-y-4">
      <UAlert color="amber" variant="soft" icon="i-heroicons-lock-closed" title="Requisitos"
              description="Meta solo entrega webhooks a una URL HTTPS pública con certificado SSL válido (Let's Encrypt u otro). Una IP privada o un certificado autofirmado no funcionan. Define PUBLIC_BASE_URL=https://tu-dominio en el .env del servidor para que la URL mostrada sea la correcta." />
      <UCard v-for="(step, i) in guide" :key="i">
        <div class="flex gap-4">
          <div class="flex-shrink-0 w-8 h-8 rounded-full bg-green-100 text-green-700 font-bold flex items-center justify-center">{{ i + 1 }}</div>
          <div class="space-y-1">
            <h3 class="font-semibold">{{ step.title }}</h3>
            <ul class="list-disc list-inside text-sm text-gray-600 space-y-1">
              <li v-for="(line, j) in step.items" :key="j">{{ line }}</li>
            </ul>
            <a v-if="step.link" :href="step.link" target="_blank" rel="noopener noreferrer" class="text-sm text-sky-600 hover:underline inline-flex items-center gap-1">
              {{ step.linkLabel }} <UIcon name="i-heroicons-arrow-top-right-on-square" class="w-4 h-4" />
            </a>
          </div>
        </div>
      </UCard>
    </div>

    <!-- ═══════════════ MODAL PROVEEDOR ═══════════════ -->
    <UModal v-model="pForm.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ pForm.id ? 'Editar proveedor' : 'Nuevo proveedor (App de Meta)' }}</h3></template>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <UFormGroup label="Nombre" required class="md:col-span-2">
            <UInput v-model="pForm.name" placeholder="Ej: Meta - Empresa principal" />
          </UFormGroup>
          <UFormGroup label="App ID" required hint="developers.facebook.com → Tu app">
            <UInput v-model="pForm.app_id" placeholder="123456789012345" />
          </UFormGroup>
          <UFormGroup label="Versión Graph API">
            <UInput v-model="pForm.api_version" placeholder="v21.0" />
          </UFormGroup>
          <UFormGroup label="Token de acceso (Usuario del Sistema)" :required="!pForm.id" class="md:col-span-2"
                      :hint="pForm.id ? 'Déjalo vacío para conservar el actual' : 'Permanente, con whatsapp_business_messaging y whatsapp_business_management'">
            <UTextarea v-model="pForm.access_token" :rows="3" placeholder="EAAG..." class="font-mono text-xs" autocomplete="off" />
          </UFormGroup>
          <UFormGroup label="App Secret" :hint="pForm.id ? 'Vacío = conservar' : 'Configuración → Básica. Se usa para validar la firma del webhook'">
            <UInput v-model="pForm.app_secret" type="password" autocomplete="new-password" />
          </UFormGroup>
          <UFormGroup label="Business Manager ID (opcional)">
            <UInput v-model="pForm.business_id" />
          </UFormGroup>
          <div class="md:col-span-2"><UCheckbox v-model="pForm.is_active" label="Activo" /></div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="pForm.open = false">Cancelar</UButton>
            <UButton :loading="pForm.saving" :disabled="!pForm.name.trim() || !pForm.app_id.trim()" @click="saveProvider">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- ═══════════════ MODAL LÍNEA ═══════════════ -->
    <UModal v-model="lForm.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ lForm.id ? 'Editar línea' : 'Nueva línea de WhatsApp' }}</h3></template>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <UFormGroup label="Proveedor" required>
            <USelect v-model="lForm.provider" :options="providerOptions" :disabled="!!lForm.id" />
          </UFormGroup>
          <UFormGroup label="Nombre" required>
            <UInput v-model="lForm.name" placeholder="Ej: Ventas" />
          </UFormGroup>
          <UFormGroup label="WhatsApp Business Account ID (WABA)" required class="md:col-span-2" hint="Meta → WhatsApp → Configuración de la API">
            <div class="flex gap-2">
              <UInput v-model="lForm.waba_id" placeholder="102290129340398" class="flex-1" />
              <UButton color="gray" variant="outline" icon="i-heroicons-magnifying-glass" :disabled="!lForm.provider || !lForm.waba_id"
                       :loading="lForm.searching" @click="searchNumbers">Buscar números</UButton>
            </div>
          </UFormGroup>
          <div v-if="lForm.numbers.length" class="md:col-span-2 space-y-1">
            <p class="text-xs text-gray-500">Selecciona el número:</p>
            <button v-for="n in lForm.numbers" :key="n.id" type="button"
                    class="w-full text-left px-3 py-2 rounded border text-sm hover:bg-green-50"
                    :class="lForm.phone_number_id === n.id ? 'border-green-500 bg-green-50' : 'border-gray-200'"
                    @click="pickNumber(n)">
              <span class="font-medium">{{ n.display_phone_number }}</span>
              <span class="text-gray-500"> · {{ n.verified_name }} · ID {{ n.id }}</span>
              <UBadge v-if="n.quality_rating" size="xs" :color="qualityColor(n.quality_rating)" variant="soft" class="ml-2">{{ n.quality_rating }}</UBadge>
            </button>
          </div>
          <UFormGroup label="Phone Number ID" required class="md:col-span-2" hint="Identificador del número (no es el teléfono)">
            <UInput v-model="lForm.phone_number_id" placeholder="106540352242922" />
          </UFormGroup>
          <UFormGroup label="Campaña por defecto" hint="Las conversaciones nuevas quedan asociadas a esta campaña">
            <USelect v-model="lForm.default_campaign" :options="[{ label: 'Ninguna', value: '' }, ...campaignOptions]" />
          </UFormGroup>
          <UFormGroup label="Máx. chats simultáneos por agente">
            <UInput v-model.number="lForm.max_chats_per_agent" type="number" min="1" max="50" />
          </UFormGroup>
          <div class="md:col-span-2 flex gap-6">
            <UCheckbox v-model="lForm.auto_assign" label="Asignar automáticamente al agente disponible con menos chats" />
            <UCheckbox v-model="lForm.is_active" label="Activa" />
          </div>
          <UFormGroup label="Mensaje de bienvenida (opcional)" class="md:col-span-2" hint="Se envía automáticamente al primer mensaje de una conversación nueva">
            <UTextarea v-model="lForm.welcome_message" :rows="2" placeholder="¡Hola! Gracias por escribirnos, en un momento te atendemos." />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="lForm.open = false">Cancelar</UButton>
            <UButton :loading="lForm.saving" :disabled="!lForm.provider || !lForm.name.trim() || !lForm.waba_id || !lForm.phone_number_id" @click="saveLine">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- ═══════════════ MODAL MENSAJE DE PRUEBA ═══════════════ -->
    <UModal v-model="testForm.open">
      <UCard>
        <template #header><h3 class="font-semibold">Enviar mensaje de prueba · {{ testForm.line?.name }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Número destino" required hint="Formato internacional sin +, ej: 573001234567">
            <UInput v-model="testForm.to" placeholder="573001234567" />
          </UFormGroup>
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Plantilla"><UInput v-model="testForm.template_name" /></UFormGroup>
            <UFormGroup label="Idioma"><UInput v-model="testForm.language" /></UFormGroup>
          </div>
          <p class="text-xs text-gray-500">"hello_world" (en_US) viene aprobada por defecto en todas las cuentas nuevas. En números de prueba, el destino debe estar en la lista de destinatarios permitidos.</p>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="testForm.open = false">Cerrar</UButton>
            <UButton icon="i-heroicons-paper-airplane" :loading="testForm.sending" :disabled="!testForm.to" @click="sendTest">Enviar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- ═══════════════ MODAL PLANTILLA ═══════════════ -->
    <UModal v-model="tForm.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">Nueva plantilla de mensaje</h3></template>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="space-y-3">
            <UFormGroup label="Línea" required>
              <USelect v-model="tForm.line" :options="lineOptions" />
            </UFormGroup>
            <UFormGroup label="Nombre" required hint="Minúsculas, números y _">
              <UInput v-model="tForm.name" placeholder="confirmacion_cita" />
            </UFormGroup>
            <div class="grid grid-cols-2 gap-3">
              <UFormGroup label="Categoría">
                <USelect v-model="tForm.category" :options="[{ label: 'Utilidad', value: 'UTILITY' }, { label: 'Marketing', value: 'MARKETING' }, { label: 'Autenticación', value: 'AUTHENTICATION' }]" />
              </UFormGroup>
              <UFormGroup label="Idioma">
                <USelect v-model="tForm.language" :options="languages" />
              </UFormGroup>
            </div>
            <UFormGroup label="Encabezado (opcional)">
              <UInput v-model="tForm.header_text" maxlength="60" />
            </UFormGroup>
            <UFormGroup label="Cuerpo" required hint="Usa {{1}}, {{2}}… para variables">
              <UTextarea v-model="tForm.body_text" :rows="5" maxlength="1024" placeholder="Hola {{1}}, tu cita es el {{2}}." />
            </UFormGroup>
            <div v-if="bodyParamCount" class="space-y-2">
              <p class="text-xs text-gray-500">Ejemplos de las variables (Meta los exige para revisar la plantilla):</p>
              <UInput v-for="i in bodyParamCount" :key="i" v-model="tForm.body_examples[i - 1]" :placeholder="`Ejemplo para {{${i}}}`" size="sm" />
            </div>
            <UFormGroup label="Pie (opcional)">
              <UInput v-model="tForm.footer_text" maxlength="60" />
            </UFormGroup>
          </div>
          <div>
            <p class="text-xs text-gray-500 mb-2">Vista previa</p>
            <div class="rounded-lg p-4 bg-[#e5ddd5] min-h-[200px]">
              <div class="bg-white rounded-lg shadow p-3 max-w-[90%] space-y-1">
                <p v-if="tForm.header_text" class="font-semibold text-sm">{{ tForm.header_text }}</p>
                <p class="text-sm whitespace-pre-line">{{ previewBody || 'Escribe el cuerpo del mensaje…' }}</p>
                <p v-if="tForm.footer_text" class="text-xs text-gray-400">{{ tForm.footer_text }}</p>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="tForm.open = false">Cancelar</UButton>
            <UButton :loading="tForm.saving" :disabled="!tForm.line || !tForm.name || !tForm.body_text.trim()" @click="saveTemplate">Enviar a revisión</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
useHead({ title: 'WhatsApp Business - VozipOmni' })

const http = useHttp()
const toast = useToast()

const tabs = [
  { label: 'Proveedores', icon: 'i-heroicons-building-office-2' },
  { label: 'Líneas', icon: 'i-heroicons-device-phone-mobile' },
  { label: 'Plantillas', icon: 'i-heroicons-document-text' },
  { label: 'Guía', icon: 'i-heroicons-book-open' },
]
const tab = ref(0)
const busy = ref('')

// ── Datos ─────────────────────────────────────────────────────────────────
const providers = ref<any[]>([])
const lines = ref<any[]>([])
const templates = ref<any[]>([])
const campaignOptions = ref<{ label: string, value: string }[]>([])
const loadingProviders = ref(false)
const loadingLines = ref(false)
const loadingTemplates = ref(false)
const tplLine = ref('')
const tplStatus = ref('')

const providerOptions = computed(() => providers.value.map(p => ({ label: p.name, value: String(p.id) })))
const lineOptions = computed(() => lines.value.map(l => ({
  label: `${l.name}${l.display_phone_number ? ' · ' + l.display_phone_number : ''}`, value: String(l.id),
})))

const lineColumns = [
  { key: 'name', label: 'Línea' },
  { key: 'number', label: 'Número' },
  { key: 'status', label: 'Estado' },
  { key: 'quality_rating', label: 'Calidad' },
  { key: 'webhook_subscribed', label: 'Webhook' },
  { key: 'routing', label: 'Enrutamiento' },
  { key: 'open_conversations', label: 'Chats abiertos' },
  { key: 'templates_count', label: 'Plantillas' },
  { key: 'actions', label: '' },
]
const tplColumns = [
  { key: 'name', label: 'Nombre' },
  { key: 'category', label: 'Categoría' },
  { key: 'status', label: 'Estado' },
  { key: 'body_text', label: 'Contenido' },
  { key: 'actions', label: '' },
]
const languages = [
  { label: 'Español', value: 'es' },
  { label: 'Español (Colombia)', value: 'es_CO' },
  { label: 'Español (México)', value: 'es_MX' },
  { label: 'Español (España)', value: 'es_ES' },
  { label: 'Inglés (EE. UU.)', value: 'en_US' },
  { label: 'Portugués (Brasil)', value: 'pt_BR' },
]

// ── Helpers ───────────────────────────────────────────────────────────────
const fmtDateTime = (v?: string) => v ? new Date(v).toLocaleString('es-CO') : 'Nunca'
const isIpUrl = (u?: string) => !!u && /^https?:\/\/\d{1,3}(\.\d{1,3}){3}/.test(u)
const lineStatusLabel = (s: string) => ({ pending: 'Pendiente', connected: 'Conectada', error: 'Error', disabled: 'Deshabilitada' } as any)[s] || s
const lineStatusColor = (s: string) => ({ pending: 'gray', connected: 'green', error: 'red', disabled: 'gray' } as any)[s] || 'gray'
const qualityColor = (q: string) => ({ GREEN: 'green', YELLOW: 'amber', RED: 'red' } as any)[String(q).toUpperCase()] || 'gray'
const tplStatusColor = (s: string) => ({ APPROVED: 'green', PENDING: 'amber', REJECTED: 'red', PAUSED: 'orange', DISABLED: 'gray' } as any)[String(s).toUpperCase()] || 'gray'

async function copy(text: string) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      ta.remove()
    }
    toast.add({ title: 'Copiado', color: 'green', timeout: 1500 })
  } catch {
    toast.add({ title: 'No se pudo copiar', color: 'red' })
  }
}

function apiError(e: any, title = 'Error') {
  const d = e?.data
  const desc = d?.details ? `${http.errorMessage(e)} — ${d.details}` : http.errorMessage(e)
  toast.add({ title, description: desc, color: 'red', timeout: 8000 })
}

// ── Carga ─────────────────────────────────────────────────────────────────
async function loadProviders() {
  loadingProviders.value = true
  try { providers.value = http.results(await http.get('/messaging/whatsapp/providers/')) }
  catch (e) { apiError(e, 'Error cargando proveedores') }
  finally { loadingProviders.value = false }
}
async function loadLines() {
  loadingLines.value = true
  try { lines.value = http.results(await http.get('/messaging/whatsapp/lines/')) }
  catch (e) { apiError(e, 'Error cargando líneas') }
  finally { loadingLines.value = false }
}
async function loadTemplates() {
  loadingTemplates.value = true
  try {
    const q: any = {}
    if (tplLine.value) q.line = tplLine.value
    if (tplStatus.value) q.status = tplStatus.value
    templates.value = http.results(await http.get('/messaging/whatsapp/templates/', q))
  } catch (e) { apiError(e, 'Error cargando plantillas') }
  finally { loadingTemplates.value = false }
}
async function loadCampaigns() {
  try {
    campaignOptions.value = http.results(await http.get('/campaigns/'))
      .map((c: any) => ({ label: c.name, value: String(c.id) }))
  } catch { /* opcional */ }
}

watch(tab, (t) => { if (t === 2) loadTemplates() })

// ── Proveedores ───────────────────────────────────────────────────────────
const pForm = reactive({
  open: false, saving: false, id: null as number | null,
  name: '', app_id: '', api_version: 'v21.0', access_token: '', app_secret: '', business_id: '', is_active: true,
})

function openProvider(p?: any) {
  Object.assign(pForm, {
    open: true, saving: false, id: p?.id ?? null,
    name: p?.name ?? '', app_id: p?.app_id ?? '', api_version: p?.api_version ?? 'v21.0',
    access_token: '', app_secret: '', business_id: p?.business_id ?? '', is_active: p?.is_active ?? true,
  })
}

async function saveProvider() {
  pForm.saving = true
  try {
    const body: any = {
      name: pForm.name.trim(), app_id: pForm.app_id.trim(), api_version: pForm.api_version.trim() || 'v21.0',
      business_id: pForm.business_id.trim(), is_active: pForm.is_active,
    }
    if (pForm.access_token.trim()) body.access_token = pForm.access_token.trim()
    if (pForm.app_secret.trim()) body.app_secret = pForm.app_secret.trim()
    if (pForm.id) await http.patch(`/messaging/whatsapp/providers/${pForm.id}/`, body)
    else await http.post('/messaging/whatsapp/providers/', body)
    toast.add({ title: 'Proveedor guardado', description: 'Copia la Callback URL y el Verify token en Meta.', color: 'green' })
    pForm.open = false
    await loadProviders()
  } catch (e) { apiError(e) }
  finally { pForm.saving = false }
}

async function testProvider(p: any) {
  busy.value = `ptest-${p.id}`
  try {
    const r: any = await http.post(`/messaging/whatsapp/providers/${p.id}/test/`)
    toast.add({ title: 'Conexión correcta', description: r.message, color: 'green' })
    await loadProviders()
  } catch (e) { apiError(e, 'El token no es válido') ; await loadProviders() }
  finally { busy.value = '' }
}

async function regenerateToken(p: any) {
  if (!confirm('Se generará un nuevo Verify token. Deberás actualizarlo en Meta y volver a verificar el webhook. ¿Continuar?')) return
  busy.value = `regen-${p.id}`
  try {
    const updated: any = await http.post(`/messaging/whatsapp/providers/${p.id}/regenerate-verify-token/`)
    Object.assign(p, updated)
    toast.add({ title: 'Token regenerado', color: 'green' })
  } catch (e) { apiError(e) }
  finally { busy.value = '' }
}

async function removeProvider(p: any) {
  if (!confirm(`¿Eliminar el proveedor "${p.name}"?`)) return
  try {
    await http.del(`/messaging/whatsapp/providers/${p.id}/`)
    await loadProviders()
  } catch (e) { apiError(e, 'No se pudo eliminar') }
}

// ── Líneas ────────────────────────────────────────────────────────────────
const lForm = reactive({
  open: false, saving: false, searching: false, id: null as number | null,
  provider: '', name: '', waba_id: '', phone_number_id: '',
  default_campaign: '', auto_assign: true, max_chats_per_agent: 5, welcome_message: '', is_active: true,
  numbers: [] as any[],
})

function openLine(l?: any) {
  Object.assign(lForm, {
    open: true, saving: false, searching: false, id: l?.id ?? null,
    provider: l ? String(l.provider) : (providers.value[0] ? String(providers.value[0].id) : ''),
    name: l?.name ?? '', waba_id: l?.waba_id ?? '', phone_number_id: l?.phone_number_id ?? '',
    default_campaign: l?.default_campaign ? String(l.default_campaign) : '',
    auto_assign: l?.auto_assign ?? true, max_chats_per_agent: l?.max_chats_per_agent ?? 5,
    welcome_message: l?.welcome_message ?? '', is_active: l?.is_active ?? true,
    numbers: [],
  })
}

async function searchNumbers() {
  lForm.searching = true
  lForm.numbers = []
  try {
    const nums: any = await http.get(`/messaging/whatsapp/providers/${lForm.provider}/phone-numbers/`, { waba_id: lForm.waba_id.trim() })
    lForm.numbers = Array.isArray(nums) ? nums : []
    if (!lForm.numbers.length) toast.add({ title: 'La cuenta no tiene números registrados', color: 'amber' })
    else if (lForm.numbers.length === 1 && !lForm.phone_number_id) lForm.phone_number_id = lForm.numbers[0].id
  } catch (e) { apiError(e, 'No se pudieron consultar los números') }
  finally { lForm.searching = false }
}

function pickNumber(n: any) {
  lForm.phone_number_id = n.id
  if (!lForm.name) lForm.name = n.verified_name || n.display_phone_number || ''
}

async function saveLine() {
  lForm.saving = true
  try {
    const body: any = {
      name: lForm.name.trim(), waba_id: lForm.waba_id.trim(), phone_number_id: String(lForm.phone_number_id).trim(),
      default_campaign: lForm.default_campaign ? Number(lForm.default_campaign) : null,
      auto_assign: lForm.auto_assign, max_chats_per_agent: Number(lForm.max_chats_per_agent) || 5,
      welcome_message: lForm.welcome_message, is_active: lForm.is_active,
    }
    let line: any
    if (lForm.id) line = await http.patch(`/messaging/whatsapp/lines/${lForm.id}/`, body)
    else line = await http.post('/messaging/whatsapp/lines/', { ...body, provider: Number(lForm.provider) })
    lForm.open = false
    toast.add({ title: 'Línea guardada', color: 'green' })
    // Al crear: validar número y suscribir webhook automáticamente
    if (!lForm.id && line?.id) {
      await testLine(line, true)
      await subscribeLine(line, true)
    }
    await loadLines()
  } catch (e) { apiError(e) }
  finally { lForm.saving = false }
}

function lineActions(row: any) {
  return [[
    { label: 'Verificar número', icon: 'i-heroicons-signal', click: () => testLine(row) },
    { label: 'Suscribir webhook', icon: 'i-heroicons-bell-alert', click: () => subscribeLine(row) },
    { label: 'Sincronizar plantillas', icon: 'i-heroicons-arrow-path', click: () => syncTemplates(row) },
    { label: 'Enviar mensaje de prueba', icon: 'i-heroicons-paper-airplane', click: () => openTest(row) },
  ]]
}

async function testLine(row: any, silent = false) {
  busy.value = `line-test-${row.id}`
  try {
    const r: any = await http.post(`/messaging/whatsapp/lines/${row.id}/test/`)
    if (!silent) toast.add({ title: 'Número verificado', description: `${r.phone?.display_phone_number || ''} · ${r.phone?.verified_name || ''}`, color: 'green' })
  } catch (e) { apiError(e, 'No se pudo verificar el número') }
  finally { busy.value = ''; if (!silent) await loadLines() }
}

async function subscribeLine(row: any, silent = false) {
  busy.value = `line-sub-${row.id}`
  try {
    const r: any = await http.post(`/messaging/whatsapp/lines/${row.id}/subscribe/`)
    if (!silent) toast.add({ title: 'Webhook suscrito', description: r.message, color: 'green' })
  } catch (e) { apiError(e, 'No se pudo suscribir el webhook') }
  finally { busy.value = ''; if (!silent) await loadLines() }
}

async function syncTemplates(row: any) {
  if (!row) return
  busy.value = `line-sync-${row.id}`
  try {
    const r: any = await http.post(`/messaging/whatsapp/lines/${row.id}/sync-templates/`)
    toast.add({ title: 'Plantillas sincronizadas', description: `${r.total} en Meta · ${r.created} nuevas · ${r.updated} actualizadas · ${r.removed} eliminadas`, color: 'green' })
    await Promise.all([loadLines(), tab.value === 2 ? loadTemplates() : Promise.resolve()])
  } catch (e) { apiError(e, 'No se pudieron sincronizar') }
  finally { busy.value = '' }
}

async function removeLine(row: any) {
  if (!confirm(`¿Eliminar la línea "${row.name}"? Si tiene conversaciones se deshabilitará para conservar el historial.`)) return
  try {
    const r: any = await http.del(`/messaging/whatsapp/lines/${row.id}/`)
    if (r?.status === 'disabled') toast.add({ title: 'Línea deshabilitada', description: r.reason, color: 'amber' })
    await loadLines()
  } catch (e) { apiError(e, 'No se pudo eliminar') }
}

const testForm = reactive({ open: false, sending: false, line: null as any, to: '', template_name: 'hello_world', language: 'en_US' })
function openTest(row: any) {
  Object.assign(testForm, { open: true, sending: false, line: row, to: '', template_name: 'hello_world', language: 'en_US' })
}
async function sendTest() {
  testForm.sending = true
  try {
    await http.post(`/messaging/whatsapp/lines/${testForm.line.id}/send-test/`, {
      to: testForm.to, template_name: testForm.template_name, language: testForm.language,
    })
    toast.add({ title: 'Mensaje enviado', description: 'Revisa el WhatsApp del número destino.', color: 'green' })
    testForm.open = false
  } catch (e) { apiError(e, 'No se pudo enviar') }
  finally { testForm.sending = false }
}

// ── Plantillas ────────────────────────────────────────────────────────────
const tForm = reactive({
  open: false, saving: false, line: '', name: '', category: 'UTILITY', language: 'es',
  header_text: '', body_text: '', footer_text: '', body_examples: [] as string[],
})

// Meta solo acepta nombres en minúsculas, números y guion bajo
watch(() => tForm.name, (v) => {
  const clean = String(v || '').toLowerCase().replace(/[^a-z0-9_]/g, '_')
  if (clean !== v) tForm.name = clean
})

const bodyParamCount = computed(() => new Set(tForm.body_text.match(/\{\{(\d+)\}\}/g) || []).size)
const previewBody = computed(() =>
  tForm.body_text.replace(/\{\{(\d+)\}\}/g, (m, n) => tForm.body_examples[Number(n) - 1] || m))

function openTemplate() {
  Object.assign(tForm, {
    open: true, saving: false, line: tplLine.value || (lines.value[0] ? String(lines.value[0].id) : ''),
    name: '', category: 'UTILITY', language: 'es', header_text: '', body_text: '', footer_text: '', body_examples: [],
  })
}

async function saveTemplate() {
  tForm.saving = true
  try {
    await http.post('/messaging/whatsapp/templates/', {
      line: Number(tForm.line), name: tForm.name, language: tForm.language, category: tForm.category,
      header_text: tForm.header_text, body_text: tForm.body_text, footer_text: tForm.footer_text,
      body_examples: tForm.body_examples.slice(0, bodyParamCount.value),
    })
    toast.add({ title: 'Plantilla enviada a Meta', description: 'Quedará en PENDING hasta que Meta la apruebe.', color: 'green' })
    tForm.open = false
    await loadTemplates()
  } catch (e) { apiError(e, 'Meta rechazó la plantilla') }
  finally { tForm.saving = false }
}

async function removeTemplate(row: any) {
  if (!confirm(`¿Eliminar la plantilla "${row.name}"? También se eliminará en Meta.`)) return
  try {
    await http.del(`/messaging/whatsapp/templates/${row.id}/`)
    await loadTemplates()
  } catch (e) { apiError(e, 'No se pudo eliminar') }
}

// ── Guía (basada en el flujo de OmniLeads / Meta Cloud API) ───────────────
const guide = [
  {
    title: 'Cuenta de Meta Business verificada',
    items: [
      'Crea o usa una cuenta en business.facebook.com (Business Manager).',
      'Completa la verificación del negocio (Configuración del negocio → Centro de seguridad) para superar los límites de prueba.',
    ],
    link: 'https://business.facebook.com/settings', linkLabel: 'Abrir configuración del negocio',
  },
  {
    title: 'App de Meta con el producto WhatsApp',
    items: [
      'En developers.facebook.com → Mis apps → Crear app → tipo "Negocios" y asóciala a tu Business Manager.',
      'Agrega el producto "WhatsApp". Meta crea una cuenta de WhatsApp Business (WABA) y un número de prueba.',
      'Copia el App ID (arriba en el panel) y el App Secret (Configuración → Básica). Ambos van en el proveedor.',
    ],
    link: 'https://developers.facebook.com/apps', linkLabel: 'Ir a Meta for Developers',
  },
  {
    title: 'Número de teléfono',
    items: [
      'WhatsApp → Configuración de la API → "Agregar número de teléfono". El número no debe estar activo en la app de WhatsApp.',
      'Verifica el número con el código SMS/llamada y registra el nombre visible.',
      'Anota el WhatsApp Business Account ID y el Phone Number ID (o usa "Buscar números" al crear la línea).',
    ],
  },
  {
    title: 'Token permanente (Usuario del Sistema)',
    items: [
      'Business Manager → Usuarios → Usuarios del sistema → Agregar (rol Administrador).',
      'Asigna activos: la App (control total) y la cuenta de WhatsApp (control total).',
      'Genera un token sin caducidad con los permisos whatsapp_business_messaging y whatsapp_business_management.',
      'Pega el token en el proveedor y usa "Probar token".',
    ],
    link: 'https://business.facebook.com/settings/system-users', linkLabel: 'Usuarios del sistema',
  },
  {
    title: 'Webhook',
    items: [
      'WhatsApp → Configuración → Webhook → Editar.',
      'URL de devolución de llamada: la Callback URL del proveedor. Token de verificación: el Verify token del proveedor.',
      'Al guardar, Meta llama a la URL y el proveedor pasa a "Webhook verificado".',
      'En "Campos del webhook" suscribe el campo "messages".',
      'En cada línea usa "Suscribir webhook" (se hace automáticamente al crearla).',
    ],
  },
  {
    title: 'Plantillas y prueba',
    items: [
      'Sincroniza las plantillas de la línea o crea nuevas desde la pestaña Plantillas (Meta las revisa en minutos u horas).',
      'Usa "Enviar mensaje de prueba" con hello_world para validar el envío.',
      'Responde desde tu teléfono: el chat aparecerá en la Bandeja omnicanal y en el panel del agente.',
    ],
  },
]

onMounted(() => {
  loadProviders()
  loadLines()
  loadCampaigns()
})
</script>
