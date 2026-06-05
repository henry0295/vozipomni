// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  
  modules: [
    '@nuxt/ui',
    '@pinia/nuxt',
    '@vueuse/nuxt'
  ],

  css: ['~/assets/css/main.css'],

  colorMode: {
    preference: 'light'
  },

  ui: {
    icons: ['heroicons', 'lucide']
  },

  // Iconos: incluir en el bundle para evitar requests HTTP en producción
  icon: {
    serverBundle: 'local',
    clientBundle: {
      scan: true,
      // Iconos usados por Nuxt UI internamente que no son detectados por el scanner
      // (loading spinners, paginación, selects, etc.)
      icons: [
        'heroicons:arrow-path-20-solid',
        'heroicons:chevron-left-20-solid',
        'heroicons:chevron-right-20-solid',
        'heroicons:chevron-up-down-20-solid',
        'heroicons:check-20-solid',
        'heroicons:x-mark-20-solid',
        'heroicons:magnifying-glass-20-solid',
        'heroicons:ellipsis-horizontal-20-solid',
        'heroicons:information-circle-20-solid',
      ],
    },
    // Nunca intentar cargar iconos por HTTP desde el servidor de producción
    fallbackToApi: false,
  },

  // Desactivar SSR para el layout si es necesario, pero preferimos mantener SSR activo
  ssr: false,

  experimental: {
    payloadExtraction: false,
    renderJsonPayload: false
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api',
      wsBase: process.env.NUXT_PUBLIC_WS_BASE || 'ws://localhost:8000/ws',
      // TURN/STUN para WebRTC — requerido cuando el agente está detrás de NAT estricta
      turnServer: process.env.NUXT_PUBLIC_TURN_SERVER || '',    // ej: 190.159.139.176
      turnUser: process.env.NUXT_PUBLIC_TURN_USER || 'vozipomni',
      turnPassword: process.env.NUXT_PUBLIC_TURN_PASSWORD || 'vozipomni2026'
    }
  },

  app: {
    head: {
      title: 'VozipOmni - Contact Center',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Sistema de Contact Center profesional' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
      ]
    }
  },

  typescript: {
    strict: true,
    shim: false
  },

  // Mejorar build performance y SSR
  nitro: {
    prerender: {
      crawlLinks: false
    }
  },

  compatibilityDate: '2024-02-09',

  // Registrar plugins
  plugins: [
    '~/plugins/api.ts'
  ]
})
