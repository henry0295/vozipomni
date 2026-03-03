<template>
  <div class="whatsapp-panel">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-heroicons-chat-bubble-left-right" class="text-green-600" />
            WhatsApp
          </h3>
          <div class="flex items-center gap-2">
            <UBadge v-if="unreadCount > 0" color="red">
              {{ unreadCount }} sin leer
            </UBadge>
            <UBadge :color="connectionStatus === 'connected' ? 'green' : 'gray'" size="sm">
              {{ connectionStatus === 'connected' ? 'Conectado' : 'Desconectado' }}
            </UBadge>
          </div>
        </div>
      </template>

      <div class="whatsapp-container">
        <!-- Lista de conversaciones -->
        <div v-if="!selectedConversation" class="conversations-list">
          <div class="mb-3">
            <UInput
              v-model="searchConversations"
              placeholder="Buscar conversaciones..."
              icon="i-heroicons-magnifying-glass"
              size="sm"
            />
          </div>

          <!-- Tabs de filtro -->
          <div class="flex gap-2 mb-3 border-b">
            <button
              v-for="tab in conversationTabs"
              :key="tab.value"
              class="tab-button"
              :class="{ 'active': activeTab === tab.value }"
              @click="activeTab = tab.value"
            >
              {{ tab.label }}
              <UBadge v-if="tab.count > 0" size="xs" :color="tab.value === 'unread' ? 'red' : 'gray'">
                {{ tab.count }}
              </UBadge>
            </button>
          </div>

          <!-- Conversaciones -->
          <div class="conversations-scroll">
            <div
              v-for="conv in filteredConversations"
              :key="conv.id"
              class="conversation-item"
              :class="{ 'unread': conv.unread_count > 0 }"
              @click="selectConversation(conv)"
            >
              <UAvatar
                :alt="conv.contact_name"
                size="md"
                class="flex-shrink-0"
              />
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between mb-1">
                  <p class="font-semibold text-gray-800 truncate">{{ conv.contact_name }}</p>
                  <span class="text-xs text-gray-500">{{ formatTime(conv.last_message_time) }}</span>
                </div>
                <p class="text-sm text-gray-600 truncate">{{ conv.last_message }}</p>
                <div class="flex items-center gap-2 mt-1">
                  <UBadge v-if="conv.campaign" size="xs" color="blue">
                    {{ conv.campaign }}
                  </UBadge>
                  <UBadge v-if="conv.unread_count > 0" size="xs" color="red">
                    {{ conv.unread_count }}
                  </UBadge>
                </div>
              </div>
            </div>

            <p v-if="filteredConversations.length === 0" class="text-center text-gray-500 py-8">
              No hay conversaciones
            </p>
          </div>
        </div>

        <!-- Chat activo -->
        <div v-else class="chat-view">
          <!-- Header del chat -->
          <div class="chat-header">
            <div class="flex items-center gap-3">
              <UButton
                icon="i-heroicons-arrow-left"
                color="gray"
                variant="ghost"
                size="sm"
                @click="selectedConversation = null"
              />
              <UAvatar
                :alt="selectedConversation.contact_name"
                size="md"
              />
              <div>
                <p class="font-semibold">{{ selectedConversation.contact_name }}</p>
                <p class="text-xs text-gray-600">{{ selectedConversation.contact_phone }}</p>
              </div>
            </div>
            <div class="flex gap-2">
              <UButton
                icon="i-heroicons-phone"
                color="green"
                variant="soft"
                size="sm"
                @click="callContact"
              >
                Llamar
              </UButton>
              <UButton
                icon="i-heroicons-information-circle"
                color="gray"
                variant="ghost"
                size="sm"
                @click="showContactInfo = !showContactInfo"
              />
            </div>
          </div>

          <!-- Mensajes -->
          <div class="messages-container" ref="messagesContainer">
            <div
              v-for="message in currentMessages"
              :key="message.id"
              class="message-wrapper"
              :class="message.direction"
            >
              <div class="message-bubble" :class="message.direction">
                <!-- Mensaje de texto -->
                <p v-if="message.type === 'text'" class="message-text">{{ message.content }}</p>

                <!-- Imagen -->
                <div v-else-if="message.type === 'image'" class="message-media">
                  <img :src="message.media_url" :alt="message.caption" class="rounded-lg max-w-xs" />
                  <p v-if="message.caption" class="mt-2 text-sm">{{ message.caption }}</p>
                </div>

                <!-- Audio -->
                <div v-else-if="message.type === 'audio'" class="message-media">
                  <audio controls class="w-full">
                    <source :src="message.media_url" />
                  </audio>
                </div>

                <!-- Documento -->
                <div v-else-if="message.type === 'document'" class="message-media">
                  <div class="flex items-center gap-2 p-2 bg-gray-100 rounded">
                    <UIcon name="i-heroicons-document" class="h-6 w-6" />
                    <div class="flex-1">
                      <p class="text-sm font-medium">{{ message.filename }}</p>
                      <p class="text-xs text-gray-600">{{ message.filesize }}</p>
                    </div>
                    <UButton
                      icon="i-heroicons-arrow-down-tray"
                      color="gray"
                      variant="ghost"
                      size="xs"
                      @click="downloadFile(message.media_url)"
                    />
                  </div>
                </div>

                <!-- Metadata -->
                <div class="message-meta">
                  <span class="text-xs opacity-75">{{ formatMessageTime(message.timestamp) }}</span>
                  <UIcon
                    v-if="message.direction === 'outgoing' && message.status === 'sent'"
                    name="i-heroicons-check"
                    class="h-3 w-3 opacity-75"
                  />
                  <UIcon
                    v-if="message.direction === 'outgoing' && message.status === 'delivered'"
                    name="i-heroicons-check-badge"
                    class="h-3 w-3 opacity-75"
                  />
                  <UIcon
                    v-if="message.direction === 'outgoing' && message.status === 'read'"
                    name="i-heroicons-check-badge"
                    class="h-3 w-3 text-blue-500"
                  />
                </div>
              </div>
            </div>

            <!-- Indicador de escritura -->
            <div v-if="isTyping" class="message-wrapper incoming">
              <div class="message-bubble incoming">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Input de mensaje -->
          <div class="message-input-container">
            <UButton
              icon="i-heroicons-paper-clip"
              color="gray"
              variant="ghost"
              @click="showAttachmentMenu = !showAttachmentMenu"
            />

            <!-- Menu de archivos adjuntos -->
            <div v-if="showAttachmentMenu" class="attachment-menu">
              <UButton
                block
                variant="soft"
                color="gray"
                icon="i-heroicons-photo"
                @click="attachImage"
              >
                Imagen
              </UButton>
              <UButton
                block
                variant="soft"
                color="gray"
                icon="i-heroicons-document"
                @click="attachDocument"
              >
                Documento
              </UButton>
            </div>

            <UTextarea
              v-model="messageText"
              :rows="2"
              placeholder="Escribe un mensaje..."
              class="flex-1"
              @keyup.enter.exact="sendMessage"
            />

            <!-- Plantillas rápidas -->
            <UButton
              icon="i-heroicons-clipboard-document-list"
              color="gray"
              variant="ghost"
              @click="showTemplates = !showTemplates"
            />

            <UButton
              icon="i-heroicons-paper-airplane"
              color="green"
              :disabled="!messageText.trim()"
              @click="sendMessage"
            />
          </div>

          <!-- Menu de plantillas -->
          <div v-if="showTemplates" class="templates-menu">
            <p class="text-sm font-medium mb-2">Plantillas Rápidas</p>
            <div class="space-y-1">
              <button
                v-for="template in messageTemplates"
                :key="template.id"
                class="template-button"
                @click="useTemplate(template)"
              >
                {{ template.name }}
              </button>
            </div>
          </div>
        </div>

        <!-- Panel de información del contacto -->
        <div v-if="showContactInfo && selectedConversation" class="contact-info-panel">
          <h4 class="font-semibold mb-3">Información del Contacto</h4>
          <div class="space-y-3">
            <div>
              <p class="text-sm text-gray-600">Nombre</p>
              <p class="font-medium">{{ selectedConversation.contact_name }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Teléfono</p>
              <p class="font-medium">{{ selectedConversation.contact_phone }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Email</p>
              <p class="font-medium">{{ selectedConversation.contact_email || 'N/A' }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Campaña</p>
              <p class="font-medium">{{ selectedConversation.campaign || 'N/A' }}</p>
            </div>
          </div>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

interface Conversation {
  id: number
  contact_name: string
  contact_phone: string
  contact_email?: string
  campaign?: string
  last_message: string
  last_message_time: string
  unread_count: number
  status: 'active' | 'closed'
}

interface Message {
  id: number
  direction: 'incoming' | 'outgoing'
  type: 'text' | 'image' | 'audio' | 'document'
  content?: string
  media_url?: string
  caption?: string
  filename?: string
  filesize?: string
  timestamp: string
  status?: 'sent' | 'delivered' | 'read'
}

// State
const conversations = ref<Conversation[]>([])
const selectedConversation = ref<Conversation | null>(null)
const currentMessages = ref<Message[]>([])
const messageText = ref('')
const searchConversations = ref('')
const activeTab = ref('all')
const isTyping = ref(false)
const showContactInfo = ref(false)
const showAttachmentMenu = ref(false)
const showTemplates = ref(false)
const messagesContainer = ref<HTMLElement>()
const connectionStatus = ref<'connected' | 'disconnected'>('connected')

// Tabs
const conversationTabs = computed(() => [
  { value: 'all', label: 'Todas', count: conversations.value.length },
  { value: 'unread', label: 'Sin leer', count: conversations.value.filter(c => c.unread_count > 0).length },
  { value: 'active', label: 'Activas', count: conversations.value.filter(c => c.status === 'active').length }
])

// Plantillas de mensajes
const messageTemplates = ref([
  { id: 1, name: 'Saludo', text: 'Hola, ¿en qué puedo ayudarte hoy?' },
  { id: 2, name: 'Información', text: 'Gracias por tu consulta. Te comparto la información solicitada:' },
  { id: 3, name: 'Despedida', text: 'Muchas gracias por tu tiempo. ¡Que tengas un excelente día!' },
  { id: 4, name: 'Callback', text: 'Te contactaré nuevamente en el horario acordado.' }
])

// Computed
const unreadCount = computed(() => {
  return conversations.value.reduce((sum, conv) => sum + conv.unread_count, 0)
})

const filteredConversations = computed(() => {
  let result = conversations.value

  // Filtrar por tab
  if (activeTab.value === 'unread') {
    result = result.filter(c => c.unread_count > 0)
  } else if (activeTab.value === 'active') {
    result = result.filter(c => c.status === 'active')
  }

  // Filtrar por búsqueda
  if (searchConversations.value) {
    const query = searchConversations.value.toLowerCase()
    result = result.filter(c =>
      c.contact_name.toLowerCase().includes(query) ||
      c.contact_phone.includes(query)
    )
  }

  return result
})

// Methods
const selectConversation = async (conv: Conversation) => {
  selectedConversation.value = conv
  await loadMessages(conv.id)
  
  // Marcar como leído
  conv.unread_count = 0
  
  // Scroll al final
  nextTick(() => {
    scrollToBottom()
  })
}

const loadMessages = async (conversationId: number) => {
  // Mock messages
  currentMessages.value = [
    {
      id: 1,
      direction: 'incoming',
      type: 'text',
      content: 'Hola, me interesa información sobre sus productos',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      status: 'read'
    },
    {
      id: 2,
      direction: 'outgoing',
      type: 'text',
      content: 'Buenos días, con gusto te ayudo. ¿Qué producto te interesa?',
      timestamp: new Date(Date.now() - 3000000).toISOString(),
      status: 'read'
    },
    {
      id: 3,
      direction: 'incoming',
      type: 'text',
      content: 'Me gustaría saber más sobre el plan empresarial',
      timestamp: new Date(Date.now() - 2400000).toISOString(),
      status: 'read'
    }
  ]
}

const sendMessage = async () => {
  if (!messageText.value.trim() || !selectedConversation.value) return

  const newMessage: Message = {
    id: Date.now(),
    direction: 'outgoing',
    type: 'text',
    content: messageText.value,
    timestamp: new Date().toISOString(),
    status: 'sent'
  }

  currentMessages.value.push(newMessage)
  messageText.value = ''

  // Scroll al final
  nextTick(() => {
    scrollToBottom()
  })

  // Simular envío
  setTimeout(() => {
    newMessage.status = 'delivered'
  }, 1000)

  setTimeout(() => {
    newMessage.status = 'read'
  }, 2000)
}

const useTemplate = (template: any) => {
  messageText.value = template.text
  showTemplates.value = false
}

const attachImage = () => {
  // Implementar adjuntar imagen
  showAttachmentMenu.value = false
}

const attachDocument = () => {
  // Implementar adjuntar documento
  showAttachmentMenu.value = false
}

const downloadFile = (url: string) => {
  window.open(url, '_blank')
}

const callContact = () => {
  // Emit evento para llamar
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 86400000) {
    return date.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit' })
}

const formatMessageTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
}

// Mock data de conversaciones
conversations.value = [
  {
    id: 1,
    contact_name: 'Juan Pérez',
    contact_phone: '+573001234567',
    campaign: 'Ventas Enero',
    last_message: 'Gracias por la información',
    last_message_time: new Date(Date.now() - 1800000).toISOString(),
    unread_count: 2,
    status: 'active'
  }
]
</script>

<style scoped>
.whatsapp-container {
  @apply min-h-[600px] flex gap-2;
}

.conversations-list {
  @apply flex-1;
}

.conversations-scroll {
  @apply space-y-2 max-h-[500px] overflow-y-auto;
}

.conversation-item {
  @apply flex items-start gap-3 p-3 rounded-lg border border-gray-200 cursor-pointer transition-all hover:bg-gray-50;
}

.conversation-item.unread {
  @apply bg-blue-50 border-blue-200;
}

.tab-button {
  @apply px-3 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent hover:text-gray-900 hover:border-gray-300 transition-colors flex items-center gap-2;
}

.tab-button.active {
  @apply text-blue-600 border-blue-600;
}

.chat-view {
  @apply flex-1 flex flex-col;
}

.chat-header {
  @apply flex items-center justify-between p-4 border-b border-gray-200;
}

.messages-container {
  @apply flex-1 p-4 space-y-3 overflow-y-auto max-h-[450px];
}

.message-wrapper {
  @apply flex;
}

.message-wrapper.incoming {
  @apply justify-start;
}

.message-wrapper.outgoing {
  @apply justify-end;
}

.message-bubble {
  @apply max-w-[70%] rounded-lg p-3;
}

.message-bubble.incoming {
  @apply bg-white border border-gray-200;
}

.message-bubble.outgoing {
  @apply bg-green-100 text-gray-800;
}

.message-text {
  @apply text-sm whitespace-pre-wrap;
}

.message-meta {
  @apply flex items-center gap-1 justify-end mt-1;
}

.message-input-container {
  @apply flex items-end gap-2 p-4 border-t border-gray-200 relative;
}

.typing-indicator {
  @apply flex gap-1;
}

.typing-indicator span {
  @apply w-2 h-2 bg-gray-400 rounded-full animate-bounce;
  animation-delay: calc(var(--i) * 0.1s);
}

.typing-indicator span:nth-child(1) { --i: 0; }
.typing-indicator span:nth-child(2) { --i: 1; animation-delay: 0.1s; }
.typing-indicator span:nth-child(3) { --i: 2; animation-delay: 0.2s; }

.attachment-menu, .templates-menu {
  @apply absolute bottom-full left-0 mb-2 p-2 bg-white border border-gray-200 rounded-lg shadow-lg space-y-1 z-10;
}

.template-button {
  @apply w-full text-left px-3 py-2 text-sm rounded hover:bg-gray-100 transition-colors;
}

.contact-info-panel {
  @apply w-64 p-4 border-l border-gray-200;
}
</style>
