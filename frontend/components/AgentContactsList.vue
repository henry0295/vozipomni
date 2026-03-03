<template>
  <div class="contacts-list-panel">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-heroicons-user-group" />
            Contactos de Campaña
          </h3>
          <UBadge v-if="selectedCampaign" color="blue">
            {{ filteredContacts.length }} contactos
          </UBadge>
        </div>

        <!-- Búsqueda y filtros -->
        <div class="space-y-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por nombre, teléfono o email..."
            icon="i-heroicons-magnifying-glass"
            size="md"
          />
          
          <div class="flex gap-2">
            <USelectMenu
              v-model="statusFilter"
              :options="statusOptions"
              placeholder="Estado"
              size="sm"
            />
            <UButton
              color="gray"
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-path"
              @click="refreshContacts"
            >
              Actualizar
            </UButton>
          </div>
        </div>
      </template>

      <!-- Lista de contactos -->
      <div v-if="filteredContacts.length > 0" class="contacts-scroll">
        <div
          v-for="contact in paginatedContacts"
          :key="contact.id"
          class="contact-card"
          :class="{ 'selected': contact.id === selectedContactId }"
          @click="selectContact(contact)"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <!-- Nombre y teléfono -->
              <div class="flex items-center gap-2 mb-2">
                <UAvatar
                  :alt="contact.name"
                  size="sm"
                />
                <div>
                  <h4 class="font-semibold text-gray-800">{{ contact.name }}</h4>
                  <p class="text-sm text-gray-600">
                    <UIcon name="i-heroicons-phone" class="inline h-3 w-3" />
                    {{ contact.phone }}
                  </p>
                </div>
              </div>

              <!-- Información adicional -->
              <div class="grid grid-cols-2 gap-2 text-xs mb-2">
                <div v-if="contact.email">
                  <p class="text-gray-500">Email</p>
                  <p class="text-gray-700 truncate">{{ contact.email }}</p>
                </div>
                <div v-if="contact.company">
                  <p class="text-gray-500">Empresa</p>
                  <p class="text-gray-700">{{ contact.company }}</p>
                </div>
              </div>

              <!-- Estado y última llamada -->
              <div class="flex items-center justify-between">
                <UBadge :color="getStatusColor(contact.status)" size="xs">
                  {{ getStatusLabel(contact.status) }}
                </UBadge>
                <span v-if="contact.last_call_date" class="text-xs text-gray-500">
                  Última llamada: {{ formatDate(contact.last_call_date) }}
                </span>
              </div>

              <!-- Última disposición -->
              <div v-if="contact.last_disposition" class="mt-2 p-2 bg-gray-50 rounded text-xs">
                <p class="font-medium text-gray-700">{{ contact.last_disposition }}</p>
                <p v-if="contact.last_notes" class="text-gray-600 mt-1">{{ contact.last_notes }}</p>
              </div>
            </div>

            <!-- Acciones rápidas -->
            <div class="flex flex-col gap-1 ml-2">
              <UButton
                color="green"
                variant="soft"
                size="xs"
                icon="i-heroicons-phone"
                :disabled="!canCall"
                @click.stop="callContact(contact)"
              >
                Llamar
              </UButton>
              <UButton
                v-if="contact.whatsapp"
                color="blue"
                variant="soft"
                size="xs"
                icon="i-heroicons-chat-bubble-left-right"
                @click.stop="openWhatsApp(contact)"
              >
                WhatsApp
              </UButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Sin contactos -->
      <div v-else class="text-center py-8 text-gray-500">
        <UIcon name="i-heroicons-user-group" class="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>{{ searchQuery ? 'No se encontraron contactos' : 'No hay contactos disponibles' }}</p>
      </div>

      <!-- Paginación -->
      <template #footer>
        <div v-if="totalPages > 1" class="flex items-center justify-between">
          <p class="text-sm text-gray-600">
            Mostrando {{ startIndex + 1 }}-{{ endIndex }} de {{ filteredContacts.length }}
          </p>
          <div class="flex gap-1">
            <UButton
              size="xs"
              color="gray"
              variant="ghost"
              icon="i-heroicons-chevron-left"
              :disabled="currentPage === 1"
              @click="currentPage--"
            />
            <span class="text-sm text-gray-600 px-2">{{ currentPage }} / {{ totalPages }}</span>
            <UButton
              size="xs"
              color="gray"
              variant="ghost"
              icon="i-heroicons-chevron-right"
              :disabled="currentPage === totalPages"
              @click="currentPage++"
            />
          </div>
        </div>
      </template>
    </UCard>

    <!-- Modal de detalle del contacto -->
    <UModal v-model="showDetailModal">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Detalle del Contacto</h3>
        </template>

        <div v-if="selectedContact" class="space-y-4">
          <!-- Información básica -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-sm text-gray-600">Nombre</p>
              <p class="font-semibold">{{ selectedContact.name }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Teléfono</p>
              <p class="font-semibold">{{ selectedContact.phone }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Email</p>
              <p class="font-semibold">{{ selectedContact.email || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Empresa</p>
              <p class="font-semibold">{{ selectedContact.company || 'N/A' }}</p>
            </div>
          </div>

          <!-- Historial de llamadas -->
          <div class="border-t pt-4">
            <p class="text-sm font-medium text-gray-700 mb-3">Historial de Llamadas</p>
            <div class="space-y-2 max-h-64 overflow-y-auto">
              <div
                v-for="call in selectedContact.call_history"
                :key="call.id"
                class="p-3 bg-gray-50 rounded-lg"
              >
                <div class="flex justify-between items-start mb-2">
                  <div>
                    <p class="text-sm font-medium">{{ formatDateTime(call.date) }}</p>
                    <p class="text-xs text-gray-600">Duración: {{ call.duration }}</p>
                  </div>
                  <UBadge :color="call.success ? 'green' : 'gray'" size="xs">
                    {{ call.disposition }}
                  </UBadge>
                </div>
                <p v-if="call.notes" class="text-sm text-gray-700">{{ call.notes }}</p>
              </div>
              <p v-if="!selectedContact.call_history?.length" class="text-sm text-gray-500 text-center py-4">
                Sin historial de llamadas
              </p>
            </div>
          </div>

          <!-- Campos personalizados -->
          <div v-if="selectedContact.custom_fields" class="border-t pt-4">
            <p class="text-sm font-medium text-gray-700 mb-3">Información Adicional</p>
            <div class="grid grid-cols-2 gap-3">
              <div v-for="(value, key) in selectedContact.custom_fields" :key="key">
                <p class="text-xs text-gray-600">{{ formatFieldName(key) }}</p>
                <p class="text-sm font-medium">{{ value }}</p>
              </div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-between">
            <UButton
              color="gray"
              variant="ghost"
              @click="showDetailModal = false"
            >
              Cerrar
            </UButton>
            <div class="flex gap-2">
              <UButton
                color="green"
                icon="i-heroicons-phone"
                :disabled="!canCall"
                @click="callContact(selectedContact)"
              >
                Llamar
              </UButton>
            </div>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useAgentStore } from '~/stores/agent'

interface Contact {
  id: number
  name: string
  phone: string
  email?: string
  company?: string
  status: 'pending' | 'contacted' | 'callback' | 'not_interested' | 'sale'
  last_call_date?: string
  last_disposition?: string
  last_notes?: string
  call_history?: any[]
  custom_fields?: Record<string, any>
  whatsapp?: boolean
}

// Props
interface Props {
  campaignId?: number
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  callContact: [contact: Contact]
  openWhatsApp: [contact: Contact]
}>()

const agentStore = useAgentStore()

// State
const contacts = ref<Contact[]>([])
const searchQuery = ref('')
const statusFilter = ref<string | null>(null)
const selectedContactId = ref<number | null>(null)
const currentPage = ref(1)
const pageSize = 10
const showDetailModal = ref(false)
const isLoading = ref(false)

// Opciones de filtro
const statusOptions = [
  { value: null, label: 'Todos' },
  { value: 'pending', label: 'Pendiente' },
  { value: 'contacted', label: 'Contactado' },
  { value: 'callback', label: 'Callback' },
  { value: 'not_interested', label: 'No Interesado' },
  { value: 'sale', label: 'Venta' }
]

// Computed
const selectedCampaign = computed(() => props.campaignId)

const canCall = computed(() => {
  return agentStore.isLoggedIn && agentStore.status === 'available'
})

const filteredContacts = computed(() => {
  let result = contacts.value

  // Filtrar por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(c =>
      c.name.toLowerCase().includes(query) ||
      c.phone.includes(query) ||
      c.email?.toLowerCase().includes(query)
    )
  }

  // Filtrar por estado
  if (statusFilter.value) {
    result = result.filter(c => c.status === statusFilter.value)
  }

  return result
})

const totalPages = computed(() => Math.ceil(filteredContacts.value.length / pageSize))
const startIndex = computed(() => (currentPage.value - 1) * pageSize)
const endIndex = computed(() => Math.min(startIndex.value + pageSize, filteredContacts.value.length))

const paginatedContacts = computed(() => {
  return filteredContacts.value.slice(startIndex.value, endIndex.value)
})

const selectedContact = computed(() => {
  return contacts.value.find(c => c.id === selectedContactId.value)
})

// Methods
const loadContacts = async () => {
  if (!props.campaignId) return

  isLoading.value = true
  try {
    // Cargar contactos de la campaña
    // const { getContacts } = useContacts()
    // const result = await getContacts({ campaign_id: props.campaignId })
    
    // Mock data
    contacts.value = Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      name: `Cliente ${i + 1}`,
      phone: `300${String(i + 1).padStart(7, '0')}`,
      email: `cliente${i + 1}@example.com`,
      company: i % 3 === 0 ? `Empresa ${i + 1}` : undefined,
      status: ['pending', 'contacted', 'callback', 'not_interested', 'sale'][i % 5] as any,
      last_call_date: i % 2 === 0 ? new Date(Date.now() - i * 86400000).toISOString() : undefined,
      last_disposition: i % 2 === 0 ? ['Contactado', 'No contesta', 'Callback'][i % 3] : undefined,
      last_notes: i % 2 === 0 ? 'Cliente interesado en el producto' : undefined,
      whatsapp: i % 2 === 0,
      call_history: []
    }))
  } catch (err) {
    console.error('Error loading contacts:', err)
  } finally {
    isLoading.value = false
  }
}

const refreshContacts = () => {
  loadContacts()
}

const selectContact = (contact: Contact) => {
  selectedContactId.value = contact.id
  showDetailModal.value = true
}

const callContact = (contact: Contact) => {
  if (!canCall.value) return
  emit('callContact', contact)
  showDetailModal.value = false
}

const openWhatsApp = (contact: Contact) => {
  emit('openWhatsApp', contact)
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    pending: 'yellow',
    contacted: 'blue',
    callback: 'purple',
    not_interested: 'red',
    sale: 'green'
  }
  return colors[status] || 'gray'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: 'Pendiente',
    contacted: 'Contactado',
    callback: 'Callback',
    not_interested: 'No Interesado',
    sale: 'Venta'
  }
  return labels[status] || status
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const formatDateTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('es-CO', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatFieldName = (key: string) => {
  return key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

// Watch
watch(() => props.campaignId, (newId) => {
  if (newId) {
    currentPage.value = 1
    loadContacts()
  }
}, { immediate: true })

watch(searchQuery, () => {
  currentPage.value = 1
})

watch(statusFilter, () => {
  currentPage.value = 1
})

// Lifecycle
onMounted(() => {
  if (props.campaignId) {
    loadContacts()
  }
})
</script>

<style scoped>
.contacts-scroll {
  @apply max-h-[600px] overflow-y-auto space-y-2;
}

.contact-card {
  @apply p-3 rounded-lg border border-gray-200 cursor-pointer transition-all hover:border-blue-300 hover:shadow-sm;
}

.contact-card.selected {
  @apply border-blue-500 bg-blue-50;
}
</style>
