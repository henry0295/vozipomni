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

  // Configuración mejorada de iconos para evitar hydration mismatch
  icon: {
    mode: 'css',
    serverBundle: {
      collections: ['heroicons', 'lucide']
    },
    client: {
      syncLoad: true  // Cargar iconos de forma síncrona en SSR
    }
  },

  // Desactivar SSR para el layout si es necesario, pero preferimos mantener SSR activo
  ssr: true,

  // Ignorar hydration mismatches causados por cambios de estado dinámico
  experimental: {
    payloadExtraction: false,
    renderJsonPayload: false
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api',
      wsBase: process.env.NUXT_PUBLIC_WS_BASE || 'ws://localhost:8000/ws'
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

  compatibilityDate: '2024-02-09'
})
