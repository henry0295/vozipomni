<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Canales digitales</h1>
        <p class="text-sm text-gray-500 mt-1">Email, chat para tu sitio web y redes sociales de Meta. WhatsApp se configura en su propia sección.</p>
      </div>
      <UButton icon="i-heroicons-chat-bubble-oval-left-ellipsis" color="gray" variant="outline" to="/settings/whatsapp">WhatsApp Business</UButton>
    </div>

    <UTabs v-model="tab" :items="tabs" />

    <!-- ═══════════════ EMAIL ═══════════════ -->
    <div v-if="tab === 0" class="space-y-4">
      <div class="flex justify-between items-center">
        <p class="text-sm text-gray-500">Cada buzón se revisa por IMAP cada minuto; las respuestas salen por SMTP en el mismo hilo.</p>
        <UButton icon="i-heroicons-plus" @click="openEmail()">Nueva cuenta</UButton>
      </div>
      <UCard>
        <UTable :rows="emails" :columns="emailColumns" :loading="loading.email" :empty-state="{ icon: 'i-heroicons-envelope', label: 'No hay cuentas de email' }">
          <template #name-data="{ row }"><p class="font-medium">{{ row.name }}</p><p class="text-xs text-gray-500">{{ row.email_address }}</p></template>
          <template #servers-data="{ row }"><p class="text-xs">IMAP {{ row.imap_host }}:{{ row.imap_port }}</p><p class="text-xs">SMTP {{ row.smtp_host }}:{{ row.smtp_port }}</p></template>
          <template #status-data="{ row }">
            <UBadge :color="row.last_error ? 'red' : (row.last_polled_at ? 'green' : 'gray')" variant="soft">
              {{ row.last_error ? 'Error' : (row.last_polled_at ? 'Conectada' : 'Sin revisar') }}
            </UBadge>
            <p v-if="row.last_error" class="text-xs text-red-500 max-w-xs truncate" :title="row.last_error">{{ row.last_error }}</p>
            <p v-else-if="row.last_polled_at" class="text-xs text-gray-400">{{ fmt(row.last_polled_at) }}</p>
          </template>
          <template #routing-data="{ row }"><RoutingSummary :row="row" /></template>
          <template #actions-data="{ row }">
            <div class="flex gap-1 justify-end">
              <UButton size="xs" color="gray" variant="outline" icon="i-heroicons-signal" :loading="busy === `et-${row.id}`" @click="testEmail(row)">Probar</UButton>
              <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-arrow-path" title="Revisar ahora" aria-label="Revisar ahora" :loading="busy === `ep-${row.id}`" @click="pollEmail(row)" />
              <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil" aria-label="Editar" @click="openEmail(row)" />
              <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" aria-label="Eliminar" @click="removeCfg('email/accounts', row, loadEmails)" />
            </div>
          </template>
        </UTable>
      </UCard>
    </div>

    <!-- ═══════════════ CHAT WEB ═══════════════ -->
    <div v-if="tab === 1" class="space-y-4">
      <div class="flex justify-between items-center">
        <p class="text-sm text-gray-500">Pega el código en tu sitio web (antes de &lt;/body&gt;). Las conversaciones llegan a la bandeja en tiempo real.</p>
        <UButton icon="i-heroicons-plus" @click="openWidget()">Nuevo widget</UButton>
      </div>
      <UCard v-for="w in widgets" :key="w.id">
        <template #header>
          <div class="flex flex-wrap items-center gap-3">
            <span class="w-4 h-4 rounded-full" :style="{ background: w.primary_color }" />
            <h3 class="font-semibold">{{ w.name }}</h3>
            <UBadge :color="w.is_active ? 'green' : 'gray'" variant="soft">{{ w.is_active ? 'Activo' : 'Inactivo' }}</UBadge>
            <UBadge color="gray" variant="soft">{{ w.open_conversations }} abiertas</UBadge>
            <div class="ml-auto flex gap-1">
              <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil" aria-label="Editar" @click="openWidget(w)" />
              <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" aria-label="Eliminar" @click="removeCfg('webchat/widgets', w, loadWidgets)" />
            </div>
          </div>
        </template>
        <div class="space-y-3">
          <UFormGroup label="Código para insertar">
            <div class="flex gap-2">
              <UTextarea :model-value="w.embed_code" readonly :rows="2" class="flex-1 font-mono text-xs" />
              <UButton icon="i-heroicons-clipboard-document" color="gray" variant="outline" aria-label="Copiar código" @click="copy(w.embed_code)" />
            </div>
          </UFormGroup>
          <div class="flex flex-wrap gap-4 text-sm text-gray-600">
            <span>Dominios: {{ w.allowed_origins ? w.allowed_origins.split('\n').filter(Boolean).join(', ') : 'cualquiera' }}</span>
            <RoutingSummary :row="w" />
            <UButton size="2xs" color="gray" variant="ghost" icon="i-heroicons-key" @click="regenerateKey(w)">Regenerar clave</UButton>
          </div>
        </div>
      </UCard>
      <UCard v-if="!loading.webchat && !widgets.length">
        <p class="text-center text-gray-500 py-6">Aún no hay widgets de chat web.</p>
      </UCard>
    </div>

    <!-- ═══════════════ MESSENGER / INSTAGRAM ═══════════════ -->
    <div v-if="tab === 2" class="space-y-4">
      <UAlert color="primary" variant="soft" icon="i-heroicons-information-circle" title="Usa la misma App de Meta de WhatsApp">
        <template #description>
          <ol class="list-decimal list-inside text-xs space-y-1 mt-1">
            <li>En la App agrega los productos <strong>Messenger</strong> e <strong>Instagram</strong> y pide los permisos <code>pages_messaging</code>, <code>pages_manage_metadata</code> e <code>instagram_manage_messages</code>.</li>
            <li>Asigna la página al Usuario del Sistema del proveedor y genera su token con esos permisos.</li>
            <li>En Messenger → Webhooks e Instagram → Webhooks usa la misma Callback URL y Verify token del proveedor, y suscribe <code>messages</code>, <code>messaging_postbacks</code>, <code>message_deliveries</code> y <code>message_reads</code>.</li>
            <li>Importa la página aquí y pulsa <strong>Suscribir</strong>. Para responder entre 24 h y 7 días Meta exige el permiso <em>Human Agent</em>.</li>
          </ol>
        </template>
      </UAlert>
      <div class="flex flex-wrap gap-2 items-center">
        <USelect v-model="discoverProvider" :options="providerOptions" class="w-64" placeholder="Proveedor (App de Meta)" />
        <UButton icon="i-heroicons-magnifying-glass" color="gray" variant="outline" :disabled="!discoverProvider" :loading="busy === 'discover'" @click="discover">Buscar páginas</UButton>
        <UButton icon="i-heroicons-plus" class="ml-auto" :disabled="!providers.length" @click="openPage()">Agregar manualmente</UButton>
      </div>
      <UCard v-if="discovered.length">
        <template #header><h3 class="font-semibold text-sm">Páginas encontradas</h3></template>
        <div class="divide-y">
          <div v-for="p in discovered" :key="p.page_id" class="py-2 flex flex-wrap items-center gap-3 text-sm">
            <span class="font-medium">{{ p.name }}</span>
            <span class="text-xs text-gray-500">ID {{ p.page_id }}</span>
            <span v-if="p.instagram_username" class="text-xs text-pink-600">@{{ p.instagram_username }}</span>
            <div class="ml-auto flex gap-2">
              <UButton size="xs" color="blue" variant="soft" :disabled="p.configured_messenger || !p.has_token" @click="importPage(p, 'messenger')">
                {{ p.configured_messenger ? 'Messenger ✓' : 'Conectar Messenger' }}
              </UButton>
              <UButton v-if="p.instagram_account_id" size="xs" color="pink" variant="soft" :disabled="p.configured_instagram || !p.has_token" @click="importPage(p, 'instagram')">
                {{ p.configured_instagram ? 'Instagram ✓' : 'Conectar Instagram' }}
              </UButton>
            </div>
          </div>
        </div>
      </UCard>
      <UCard>
        <UTable :rows="pages" :columns="pageColumns" :loading="loading.meta" :empty-state="{ icon: 'i-heroicons-chat-bubble-left-right', label: 'No hay páginas conectadas' }">
          <template #name-data="{ row }">
            <div class="flex items-center gap-2">
              <UIcon :name="channelMeta(row.platform).icon" class="w-4 h-4" :class="channelMeta(row.platform).color" />
              <div><p class="font-medium">{{ row.name }}</p><p class="text-xs text-gray-500">{{ channelMeta(row.platform).label }} · {{ row.platform === 'instagram' ? row.instagram_account_id : row.page_id }}</p></div>
            </div>
          </template>
          <template #status-data="{ row }">
            <UBadge :color="row.last_error ? 'red' : (row.subscribed ? 'green' : 'amber')" variant="soft">
              {{ row.last_error ? 'Error' : (row.subscribed ? 'Suscrita' : 'Sin suscribir') }}
            </UBadge>
            <p v-if="row.last_error" class="text-xs text-red-500 max-w-xs truncate" :title="row.last_error">{{ row.last_error }}</p>
          </template>
          <template #routing-data="{ row }"><RoutingSummary :row="row" /></template>
          <template #actions-data="{ row }">
            <div class="flex gap-1 justify-end">
              <UButton size="xs" color="gray" variant="outline" icon="i-heroicons-signal" :loading="busy === `pt-${row.id}`" @click="pageAction(row, 'test')">Probar</UButton>
              <UButton size="xs" color="gray" variant="outline" icon="i-heroicons-bell-alert" :loading="busy === `ps-${row.id}`" @click="pageAction(row, 'subscribe')">Suscribir</UButton>
              <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil" aria-label="Editar" @click="openPage(row)" />
              <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" aria-label="Eliminar" @click="removeCfg('meta/pages', row, loadPages)" />
            </div>
          </template>
        </UTable>
      </UCard>
    </div>

    <!-- ═══════════════ MODAL EMAIL ═══════════════ -->
    <UModal v-model="emailForm.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ emailForm.data.id ? 'Editar cuenta de email' : 'Nueva cuenta de email' }}</h3></template>
        <div class="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <UFormGroup label="Nombre" required><UInput v-model="emailForm.data.name" placeholder="Soporte" /></UFormGroup>
            <UFormGroup label="Dirección" required><UInput v-model="emailForm.data.email_address" type="email" placeholder="soporte@empresa.com" /></UFormGroup>
            <UFormGroup label="Nombre del remitente"><UInput v-model="emailForm.data.from_name" placeholder="Soporte Empresa" /></UFormGroup>
          </div>
          <UDivider label="Entrada (IMAP)" />
          <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
            <UFormGroup label="Servidor" required class="md:col-span-2"><UInput v-model="emailForm.data.imap_host" placeholder="imap.gmail.com" /></UFormGroup>
            <UFormGroup label="Puerto"><UInput v-model.number="emailForm.data.imap_port" type="number" /></UFormGroup>
            <UFormGroup label="Carpeta"><UInput v-model="emailForm.data.imap_folder" /></UFormGroup>
            <UFormGroup label="Usuario" required class="md:col-span-2"><UInput v-model="emailForm.data.imap_username" autocomplete="off" /></UFormGroup>
            <UFormGroup label="Contraseña" :hint="emailForm.data.id ? 'Vacío = conservar' : 'En Gmail/Outlook usa una contraseña de aplicación'" class="md:col-span-2">
              <UInput v-model="emailForm.data.imap_password" type="password" autocomplete="new-password" />
            </UFormGroup>
            <UCheckbox v-model="emailForm.data.imap_ssl" label="SSL/TLS" />
          </div>
          <UDivider label="Salida (SMTP)" />
          <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
            <UFormGroup label="Servidor" required class="md:col-span-2"><UInput v-model="emailForm.data.smtp_host" placeholder="smtp.gmail.com" /></UFormGroup>
            <UFormGroup label="Puerto"><UInput v-model.number="emailForm.data.smtp_port" type="number" /></UFormGroup>
            <div class="flex flex-col gap-2 justify-end">
              <UCheckbox v-model="emailForm.data.smtp_starttls" label="STARTTLS (587)" />
              <UCheckbox v-model="emailForm.data.smtp_ssl" label="SSL (465)" />
            </div>
            <UFormGroup label="Usuario" hint="Vacío = el mismo de IMAP" class="md:col-span-2"><UInput v-model="emailForm.data.smtp_username" autocomplete="off" /></UFormGroup>
            <UFormGroup label="Contraseña" hint="Vacío = la misma de IMAP / conservar" class="md:col-span-2">
              <UInput v-model="emailForm.data.smtp_password" type="password" autocomplete="new-password" />
            </UFormGroup>
          </div>
          <UFormGroup label="Firma"><UTextarea v-model="emailForm.data.signature" :rows="3" placeholder="Equipo de Soporte · Empresa S.A.S · +57 601 000 0000" /></UFormGroup>
          <UDivider label="Enrutamiento y horario" />
          <MessagingRoutingFields v-model="emailForm.data" :campaigns="campaignOptions" :time-conditions="timeConditionOptions" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="emailForm.open = false">Cancelar</UButton>
            <UButton :loading="emailForm.saving" :disabled="!emailForm.data.name || !emailForm.data.email_address || !emailForm.data.imap_host || !emailForm.data.smtp_host"
                     @click="saveCfg('email/accounts', emailForm, ['imap_password', 'smtp_password'], loadEmails)">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- ═══════════════ MODAL WIDGET ═══════════════ -->
    <UModal v-model="widgetForm.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ widgetForm.data.id ? 'Editar widget' : 'Nuevo widget de chat web' }}</h3></template>
        <div class="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <UFormGroup label="Nombre interno" required><UInput v-model="widgetForm.data.name" placeholder="Sitio principal" /></UFormGroup>
            <UFormGroup label="Color">
              <div class="flex gap-2 items-center"><input v-model="widgetForm.data.primary_color" type="color" class="h-9 w-12 rounded border" aria-label="Color del widget" /><UInput v-model="widgetForm.data.primary_color" class="flex-1" /></div>
            </UFormGroup>
            <UFormGroup label="Título"><UInput v-model="widgetForm.data.title" /></UFormGroup>
            <UFormGroup label="Subtítulo"><UInput v-model="widgetForm.data.subtitle" /></UFormGroup>
            <UFormGroup label="Texto de inicio" class="md:col-span-2"><UTextarea v-model="widgetForm.data.intro_text" :rows="2" /></UFormGroup>
            <UFormGroup label="Posición"><USelect v-model="widgetForm.data.position" :options="[{ label: 'Abajo a la derecha', value: 'right' }, { label: 'Abajo a la izquierda', value: 'left' }]" /></UFormGroup>
            <div class="flex flex-col gap-2 justify-end">
              <UCheckbox v-model="widgetForm.data.require_name" label="Pedir nombre" />
              <UCheckbox v-model="widgetForm.data.require_email" label="Pedir email" />
            </div>
            <UFormGroup label="Dominios permitidos" class="md:col-span-2" hint="Uno por línea, con https://. Vacío = cualquier sitio (no recomendado)">
              <UTextarea v-model="widgetForm.data.allowed_origins" :rows="2" placeholder="https://www.miempresa.com" />
            </UFormGroup>
          </div>
          <UDivider label="Enrutamiento y horario" />
          <MessagingRoutingFields v-model="widgetForm.data" :campaigns="campaignOptions" :time-conditions="timeConditionOptions" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="widgetForm.open = false">Cancelar</UButton>
            <UButton :loading="widgetForm.saving" :disabled="!widgetForm.data.name" @click="saveCfg('webchat/widgets', widgetForm, [], loadWidgets)">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- ═══════════════ MODAL PÁGINA ═══════════════ -->
    <UModal v-model="pageForm.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ pageForm.data.id ? 'Editar página' : 'Conectar página' }}</h3></template>
        <div class="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <UFormGroup label="Proveedor (App de Meta)" required><USelect v-model="pageForm.data.provider" :options="providerOptions" :disabled="!!pageForm.data.id" /></UFormGroup>
            <UFormGroup label="Plataforma" required>
              <USelect v-model="pageForm.data.platform" :disabled="!!pageForm.data.id" :options="[{ label: 'Facebook Messenger', value: 'messenger' }, { label: 'Instagram', value: 'instagram' }]" />
            </UFormGroup>
            <UFormGroup label="Nombre" required><UInput v-model="pageForm.data.name" /></UFormGroup>
            <UFormGroup label="ID de la página de Facebook" required><UInput v-model="pageForm.data.page_id" /></UFormGroup>
            <UFormGroup v-if="pageForm.data.platform === 'instagram'" label="ID de la cuenta de Instagram" required class="md:col-span-2">
              <UInput v-model="pageForm.data.instagram_account_id" />
            </UFormGroup>
            <UFormGroup label="Token de acceso de la página" class="md:col-span-2" :required="!pageForm.data.id" :hint="pageForm.data.id ? 'Vacío = conservar' : ''">
              <UTextarea v-model="pageForm.data.page_access_token" :rows="2" class="font-mono text-xs" autocomplete="off" />
            </UFormGroup>
          </div>
          <UDivider label="Enrutamiento y horario" />
          <MessagingRoutingFields v-model="pageForm.data" :campaigns="campaignOptions" :time-conditions="timeConditionOptions" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="pageForm.open = false">Cancelar</UButton>
            <UButton :loading="pageForm.saving" :disabled="!pageForm.data.provider || !pageForm.data.name || !pageForm.data.page_id"
                     @click="saveCfg('meta/pages', pageForm, ['page_access_token'], loadPages)">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { channelMeta } from '~/utils/channels'

useHead({ title: 'Canales digitales - VozipOmni' })

const http = useHttp()
const toast = useToast()

// Resumen compacto de enrutamiento para las tablas
const RoutingSummary = defineComponent({
  props: { row: { type: Object, required: true } },
  setup(p) {
    return () => h('div', { class: 'text-xs' }, [
      h('p', p.row.default_campaign_name || 'Sin campaña'),
      h('p', { class: 'text-gray-500' }, `${p.row.auto_assign ? 'Auto-asignar · máx ' + p.row.max_chats_per_agent : 'Asignación manual'}${p.row.time_condition_name ? ' · ' + p.row.time_condition_name : ''}`),
    ])
  },
})

const tabs = [
  { label: 'Email', icon: 'i-heroicons-envelope' },
  { label: 'Chat web', icon: 'i-heroicons-globe-alt' },
  { label: 'Messenger e Instagram', icon: 'i-heroicons-chat-bubble-left-right' },
]
const tab = ref(0)
const busy = ref('')
const loading = reactive({ email: false, webchat: false, meta: false })

const emails = ref<any[]>([])
const widgets = ref<any[]>([])
const pages = ref<any[]>([])
const providers = ref<any[]>([])
const discovered = ref<any[]>([])
const discoverProvider = ref('')
const campaignOptions = ref<{ label: string, value: string }[]>([])
const timeConditionOptions = ref<{ label: string, value: string }[]>([])
const providerOptions = computed(() => providers.value.map(p => ({ label: p.name, value: String(p.id) })))

const emailColumns = [
  { key: 'name', label: 'Cuenta' }, { key: 'servers', label: 'Servidores' }, { key: 'status', label: 'Estado' },
  { key: 'routing', label: 'Enrutamiento' }, { key: 'open_conversations', label: 'Abiertas' }, { key: 'actions', label: '' },
]
const pageColumns = [
  { key: 'name', label: 'Página' }, { key: 'provider_name', label: 'Proveedor' }, { key: 'status', label: 'Estado' },
  { key: 'routing', label: 'Enrutamiento' }, { key: 'open_conversations', label: 'Abiertas' }, { key: 'actions', label: '' },
]

const fmt = (v: string) => new Date(v).toLocaleString('es-CO')

const ROUTING_DEFAULTS = { default_campaign: '', auto_assign: true, max_chats_per_agent: 5, welcome_message: '', time_condition: '', after_hours_message: '', is_active: true }
const routingFrom = (r: any) => ({
  default_campaign: r?.default_campaign ? String(r.default_campaign) : '',
  auto_assign: r?.auto_assign ?? true, max_chats_per_agent: r?.max_chats_per_agent ?? 5,
  welcome_message: r?.welcome_message ?? '', time_condition: r?.time_condition ? String(r.time_condition) : '',
  after_hours_message: r?.after_hours_message ?? '', is_active: r?.is_active ?? true,
})

const emailForm = reactive({ open: false, saving: false, data: {} as any })
const widgetForm = reactive({ open: false, saving: false, data: {} as any })
const pageForm = reactive({ open: false, saving: false, data: {} as any })

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ title: 'Copiado', color: 'green', timeout: 1500 })
  } catch {
    toast.add({ title: 'Copia el texto manualmente', color: 'amber' })
  }
}

function apiError(e: any, title = 'Error') {
  const d = e?.data
  const msg = d?.errors ? d.errors.join(' · ') : (d?.details ? `${http.errorMessage(e)} — ${d.details}` : http.errorMessage(e))
  toast.add({ title, description: msg, color: 'red', timeout: 8000 })
}

async function loadEmails() {
  loading.email = true
  try { emails.value = http.results(await http.get('/messaging/email/accounts/')) } catch (e) { apiError(e) } finally { loading.email = false }
}
async function loadWidgets() {
  loading.webchat = true
  try { widgets.value = http.results(await http.get('/messaging/webchat/widgets/')) } catch (e) { apiError(e) } finally { loading.webchat = false }
}
async function loadPages() {
  loading.meta = true
  try { pages.value = http.results(await http.get('/messaging/meta/pages/')) } catch (e) { apiError(e) } finally { loading.meta = false }
}

function openEmail(r?: any) {
  emailForm.data = {
    id: r?.id ?? null, name: r?.name ?? '', email_address: r?.email_address ?? '', from_name: r?.from_name ?? '',
    signature: r?.signature ?? '', imap_host: r?.imap_host ?? '', imap_port: r?.imap_port ?? 993, imap_ssl: r?.imap_ssl ?? true,
    imap_username: r?.imap_username ?? '', imap_password: '', imap_folder: r?.imap_folder ?? 'INBOX',
    smtp_host: r?.smtp_host ?? '', smtp_port: r?.smtp_port ?? 587, smtp_starttls: r?.smtp_starttls ?? true, smtp_ssl: r?.smtp_ssl ?? false,
    smtp_username: r?.smtp_username ?? '', smtp_password: '', ...(r ? routingFrom(r) : { ...ROUTING_DEFAULTS }),
  }
  emailForm.open = true
}
function openWidget(r?: any) {
  widgetForm.data = {
    id: r?.id ?? null, name: r?.name ?? '', title: r?.title ?? '¿Hablamos?', subtitle: r?.subtitle ?? 'Te respondemos en minutos',
    intro_text: r?.intro_text ?? 'Déjanos tus datos y cuéntanos en qué te ayudamos.', primary_color: r?.primary_color ?? '#16a34a',
    position: r?.position ?? 'right', require_name: r?.require_name ?? true, require_email: r?.require_email ?? false,
    allowed_origins: r?.allowed_origins ?? '', ...(r ? routingFrom(r) : { ...ROUTING_DEFAULTS }),
  }
  widgetForm.open = true
}
function openPage(r?: any, preset?: any) {
  pageForm.data = {
    id: r?.id ?? null, provider: r ? String(r.provider) : (preset?.provider || providerOptions.value[0]?.value || ''),
    platform: r?.platform ?? preset?.platform ?? 'messenger', name: r?.name ?? preset?.name ?? '',
    page_id: r?.page_id ?? preset?.page_id ?? '', instagram_account_id: r?.instagram_account_id ?? preset?.instagram_account_id ?? '',
    page_access_token: preset?.access_token ?? '', ...(r ? routingFrom(r) : { ...ROUTING_DEFAULTS }),
  }
  pageForm.open = true
}

async function saveCfg(path: string, form: any, secrets: string[], reload: () => Promise<void>) {
  form.saving = true
  try {
    const { id, ...rest } = form.data
    const body: any = { ...rest }
    body.default_campaign = body.default_campaign ? Number(body.default_campaign) : null
    body.time_condition = body.time_condition ? Number(body.time_condition) : null
    if (body.provider) body.provider = Number(body.provider)
    for (const s of secrets) if (!body[s]) delete body[s]
    if (id) await http.patch(`/messaging/${path}/${id}/`, body)
    else await http.post(`/messaging/${path}/`, body)
    form.open = false
    toast.add({ title: 'Guardado', color: 'green' })
    await reload()
  } catch (e) { apiError(e, 'No se pudo guardar') }
  finally { form.saving = false }
}

async function removeCfg(path: string, row: any, reload: () => Promise<void>) {
  if (!confirm(`¿Eliminar "${row.name}"? Si tiene conversaciones se deshabilitará para conservar el historial.`)) return
  try {
    const r: any = await http.del(`/messaging/${path}/${row.id}/`)
    if (r?.status === 'disabled') toast.add({ title: 'Canal deshabilitado', description: r.reason, color: 'amber' })
    await reload()
  } catch (e) { apiError(e) }
}

async function testEmail(row: any) {
  busy.value = `et-${row.id}`
  try {
    await http.post(`/messaging/email/accounts/${row.id}/test/`)
    toast.add({ title: 'IMAP y SMTP correctos', color: 'green' })
  } catch (e) { apiError(e, 'La prueba falló') }
  finally { busy.value = '' }
}
async function pollEmail(row: any) {
  busy.value = `ep-${row.id}`
  try {
    const r: any = await http.post(`/messaging/email/accounts/${row.id}/poll/`)
    toast.add({ title: `${r.new_messages} correo(s) nuevo(s)`, color: 'green' })
    await loadEmails()
  } catch (e) { apiError(e, 'No se pudo revisar el buzón'); await loadEmails() }
  finally { busy.value = '' }
}
async function regenerateKey(w: any) {
  if (!confirm('El código insertado actualmente dejará de funcionar. ¿Continuar?')) return
  try {
    Object.assign(w, await http.post(`/messaging/webchat/widgets/${w.id}/regenerate-key/`))
    toast.add({ title: 'Clave regenerada: actualiza el código en tu sitio', color: 'amber' })
  } catch (e) { apiError(e) }
}
async function discover() {
  busy.value = 'discover'
  try {
    discovered.value = await http.get('/messaging/meta/pages/discover/', { provider: discoverProvider.value }) as any[]
    if (!discovered.value.length) toast.add({ title: 'El token no tiene páginas asignadas', color: 'amber' })
  } catch (e) { apiError(e, 'No se pudieron listar las páginas') }
  finally { busy.value = '' }
}
function importPage(p: any, platform: 'messenger' | 'instagram') {
  openPage(undefined, {
    provider: discoverProvider.value, platform, page_id: p.page_id, access_token: p.access_token,
    name: platform === 'instagram' && p.instagram_username ? `@${p.instagram_username}` : p.name,
    instagram_account_id: p.instagram_account_id,
  })
}
async function pageAction(row: any, action: 'test' | 'subscribe') {
  busy.value = `${action === 'test' ? 'pt' : 'ps'}-${row.id}`
  try {
    await http.post(`/messaging/meta/pages/${row.id}/${action}/`)
    toast.add({ title: action === 'test' ? 'Token válido' : 'Página suscrita', color: 'green' })
  } catch (e) { apiError(e) }
  finally { busy.value = ''; await loadPages() }
}

watch(tab, (t) => {
  if (t === 1 && !widgets.value.length) loadWidgets()
  if (t === 2 && !pages.value.length) loadPages()
})

onMounted(async () => {
  loadEmails()
  const [c, t, p] = await Promise.allSettled([
    http.get('/campaigns/'), http.get('/telephony/time-conditions/'), http.get('/messaging/whatsapp/providers/'),
  ])
  if (c.status === 'fulfilled') campaignOptions.value = http.results(c.value).map((x: any) => ({ label: x.name, value: String(x.id) }))
  if (t.status === 'fulfilled') timeConditionOptions.value = http.results(t.value).map((x: any) => ({ label: x.name, value: String(x.id) }))
  if (p.status === 'fulfilled') {
    providers.value = http.results(p.value)
    discoverProvider.value = providerOptions.value[0]?.value || ''
  }
})
</script>
