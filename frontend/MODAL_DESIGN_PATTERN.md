# Patrón de Diseño para Modales de Creación/Edición

Este documento define el patrón estándar para todos los formularios de creación y edición en VozipOmni.

## ✨ Características del Patrón

### 1. Modal Ancho con Pestañas
```vue
<UModal v-model="isModalOpen" :ui="{ width: 'sm:max-w-4xl' }">
  <UCard>
    <template #header>
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold">
          {{ editingId ? 'Editar [Recurso]' : 'Nuevo [Recurso]' }}
        </h3>
        <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="closeModal" />
      </div>
    </template>

    <UTabs :items="tabs" v-model="activeTab">
      <!-- Contenido de tabs aquí -->
    </UTabs>

    <template #footer>
      <div class="flex justify-end gap-3">
        <UButton color="gray" variant="outline" @click="closeModal" :disabled="saving">
          Cancelar
        </UButton>
        <UButton color="sky" @click="save" :loading="saving">
          {{ editingId ? 'Guardar Cambios' : 'Crear [Recurso]' }}
        </UButton>
      </div>
    </template>
  </UCard>
</UModal>
```

### 2. Organización de Tabs

**Tabs recomendadas:**
- **Información Básica** (i-heroicons-identification): Datos esenciales, nombre, descripción
- **Configuración** (i-heroicons-cog): Opciones principales del recurso
- **Avanzado** (i-heroicons-adjustments-horizontal): Configuración avanzada
- **Recursos Relacionados** (i-heroicons-link): Asociaciones con otros módulos

**Definición de tabs:**
```vue
const tabs = [
  { key: 'basica', label: 'Información Básica', icon: 'i-heroicons-identification' },
  { key: 'configuracion', label: 'Configuración', icon: 'i-heroicons-cog' },
  { key: 'avanzado', label: 'Avanzado', icon: 'i-heroicons-adjustments-horizontal' }
]
```

### 3. Alertas con Recomendaciones

Usar `UAlert` para guiar al usuario:

```vue
<UAlert 
  icon="i-heroicons-information-circle" 
  color="blue" 
  variant="subtle"
  title="Título Descriptivo"
  description="Explicación clara de la opción o recomendación."
/>
```

**Colores según contexto:**
- `blue`: Información general
- `green`: Opción recomendada
- `yellow`: Advertencia o cuidado
- `purple`: Configuración avanzada
- `red`: Crítico o peligroso

### 4. Grid Layouts Responsivos

```vue
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
  <UFormGroup label="Campo 1" required>
    <UInput v-model="form.campo1" />
  </UFormGroup>
  
  <UFormGroup label="Campo 2">
    <UInput v-model="form.campo2" />
  </UFormGroup>
</div>
```

### 5. Secciones Agrupadas con Bordes

Para agrupar conceptos relacionados:

```vue
<div class="border border-gray-200 rounded-lg p-4 space-y-4">
  <div class="flex items-center space-x-2">
    <UIcon name="i-heroicons-key" class="text-blue-500" />
    <h4 class="font-medium text-gray-800">Título de Sección</h4>
  </div>
  
  <!-- Campos de la sección -->
</div>
```

**Variantes con color de fondo:**
```vue
<div class="border border-blue-200 bg-blue-50 rounded-lg p-4 space-y-4">
  <!-- Contenido destacado -->
</div>
```

### 6. USelectMenu en lugar de USelect

Para mejor UX, usar `USelectMenu`:

```vue
<USelectMenu
  v-model="form.option"
  :options="optionsList"
  value-attribute="value"
  option-attribute="label"
/>
```

## 📋 Ejemplos Implementados

### ✅ Modales Actualizados (11 TOTAL)

#### Primera Oleada (3 modales - Commit 8ab26a4)
1. **Extensiones** (`frontend/pages/extensions/index.vue`)
   - 4 tabs: Información Básica, Autenticación, Códecs y Avanzado, Buzón de Voz
   - Auto-configuración según tipo (WebRTC vs SIP)
   - Generador de contraseñas seguras

2. **Colas** (`frontend/pages/queues/index.vue`)
   - 3 tabs: Información Básica, Tiempos y Límites, Anuncios y Música
   - Explicaciones de estrategias de distribución
   - Alertas con recomendaciones de configuración

3. **Campañas** (`frontend/pages/campaigns/index.vue`)
   - 4 tabs: Información Básica, Recursos, Programación, Configuración Avanzada
   - Alertas explicativas por tipo de campaña
   - Configuración de recursos relacionados

#### Segunda Oleada (8 modales - Commit 43ee51e)
4. **IVR** (`frontend/pages/ivr/index.vue`)
   - 4 tabs: Básica, Mensajes, Opciones de Menú, Configuración
   - Gestión dinámica de opciones del menú
   - Alertas con guías de uso

5. **Agentes** (`frontend/pages/agents/index.vue`) 
   - 3 tabs: Usuario, Configuración de Agente, Opciones
   - Validación automática de agent_id y extension
   - Auto-generación de IDs
   - Indicadores de disponibilidad en tiempo real

6. **Buzón de Voz** (`frontend/pages/voicemail/index.vue`)
   - 2 tabs: Básica, Notificaciones
   - Configuración de email y adjuntos
   - Límites de mensajes

7. **Condiciones de Horario** (`frontend/pages/time-conditions/index.vue`)
   - 3 tabs: Básica, Horarios, Destinos
   - Configuración de rangos horarios
   - Destinos por condición

8. **Rutas Entrantes** (`frontend/pages/inbound-routes/index.vue`)
   - 3 tabs: Básica, Identificación, Destino
   - Patrones DID/CID
   - Selección de destino

9. **Rutas Salientes** (`frontend/pages/outbound-routes/index.vue`)
   - 3 tabs: Básica, Patrones, Troncales
   - Configuración de dial patterns
   - Selección de trunks

10. **Destinos Personalizados** (`frontend/pages/custom-destinations/index.vue`)
    - 2 tabs: Básica, Dialplan
    - Editor de código dialplan
    - Alertas de seguridad

11. **Webhooks** (`frontend/pages/webhooks/index.vue`)
    - 3 tabs: Básica, Seguridad, Configuración
    - Headers personalizados
    - Retry logic y timeouts

#### Patrón Base
**Troncales SIP** (`frontend/pages/trunks/index.vue`) - Implementación original
   - 4 tabs: Información Básica, Autenticación, Media y Códecs, Avanzado
   - Alertas contextuales según tipo de troncal
   - Secciones bien delimitadas

### 🎉 Estado: COMPLETO

**Todos los modales de creación/edición del sistema ahora siguen el patrón profesional uniforme.**

## 🎨 Mejores Prácticas

1. **Máximo 4-5 tabs**: No sobrecargar, mantener simple
2. **Labels descriptivos**: Usar help text cuando sea necesario
3. **Validación visual**: Campos requeridos marcados claramente
4. **Responsive**: Siempre usar `grid-cols-1 md:grid-cols-2`
5. **Iconos coherentes**: Usar heroicons consistentemente
6. **Colores semánticos**: 
   - Sky/Blue para acciones principales
   - Gray para cancelar
   - Green para éxito/recomendado
   - Yellow para advertencias
   - Red para acciones destructivas

## 🚀 Cómo Aplicar el Patrón

1. Cambiar `USlideover` por `UModal` con `width: 'sm:max-w-4xl'`
2. Reorganizar campos en tabs lógicas
3. Agregar `UAlert` con recomendaciones donde aplique
4. Usar grids responsivos para campos
5. Agrupar secciones relacionadas con bordes
6. Actualizar botones del footer con estilos consistentes

## 📖 Referencias

- **Nuxt UI Documentation**: https://ui.nuxt.com/
- **Heroicons**: https://heroicons.com/
- **Ejemplo completo**: Ver `frontend/pages/trunks/index.vue`
