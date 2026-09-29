<template>
  <div class="space-y-6">
    <!-- ═══════════════ CABECERA ═══════════════ -->
    <section class="wa-hero rounded-2xl p-6 text-white relative overflow-hidden">
      <div class="wa-hero-pattern" aria-hidden="true" />
      <div class="relative flex flex-wrap items-start justify-between gap-6">
        <div class="flex items-start gap-4">
          <div class="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center ring-1 ring-white/25">
            <UIcon name="i-heroicons-chat-bubble-oval-left-ellipsis" class="w-8 h-8" />
          </div>
          <div>
            <p class="text-xs uppercase tracking-widest text-emerald-100/80">VozipOmni · Canal WhatsApp</p>
            <h1 class="text-2xl font-bold leading-tight">WhatsApp Business</h1>
            <p class="text-sm text-emerald-50/90 mt-1 max-w-xl">
              Conecta tus números directamente con la Cloud API de Meta, sin intermediarios. Tus agentes atienden desde la bandeja omnicanal.
            </p>
          </div>
        </div>
        <div class="flex gap-2">
          <UButton icon="i-heroicons-book-open" color="white" variant="ghost" class="text-white hover:bg-white/10" @click="tab = 3">Guía</UButton>
          <UButton icon="i-heroicons-plus" color="white" @click="providers.length ? openLine() : openProvider()">
            {{ providers.length ? 'Agregar número' : 'Conectar App de Meta' }}
          </UButton>
        </div>
      </div>

      <div class="relative grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
        <div v-for="s in heroStats" :key="s.label" class="rounded-xl bg-white/10 ring-1 ring-white/15 px-4 py-3">
          <p class="text-[11px] uppercase tracking-wide text-emerald-100/80">{{ s.label }}</p>
          <p class="text-2xl font-bold mt-0.5">{{ s.value }}</p>
          <p v-if="s.hint" class="text-[11px] text-emerald-50/70 truncate">{{ s.hint }}</p>
        </div>
      </div>
    </section>

    <!-- ═══════════════ ESTADO DE LA CONEXIÓN ═══════════════ -->
    <section class="rounded-2xl border border-gray-200 bg-white p-5">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 class="font-semibold text-gray-900">Estado de la conexión</h2>
          <p class="text-xs text-gray-500">{{ setupDone }} de {{ setupSteps.length }} pasos completados</p>
        </div>
        <div class="w-48 h-2 rounded-full bg-gray-100 overflow-hidden" role="progressbar" :aria-valuenow="setupPct" aria-valuemin="0" aria-valuemax="100">
          <div class="h-full rounded-full bg-emerald-500 transition-all" :style="{ width: `${setupPct}%` }" />
        </div>
      </div>
      <ol class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
        <li v-for="(s, i) in setupSteps" :key="s.key">
          <button type="button" class="w-full text-left rounded-xl border px-3 py-3 transition-colors h-full"
                  :class="s.done ? 'border-emerald-200 bg-emerald-50/60 hover:bg-emerald-50' : (s.current ? 'border-amber-300 bg-amber-50/60 hover:bg-amber-50' : 'border-gray-200 hover:bg-gray-50')"
                  @click="s.go()">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                    :class="s.done ? 'bg-emerald-500 text-white' : (s.current ? 'bg-amber-400 text-white' : 'bg-gray-200 text-gray-600')">
                <UIcon v-if="s.done" name="i-heroicons-check" class="w-4 h-4" />
                <template v-else>{{ i + 1 }}</template>
              </span>
              <span class="text-sm font-medium text-gray-900">{{ s.title }}</span>
            </div>
            <p class="text-[11px] text-gray-500 mt-1.5 leading-snug">{{ s.done ? s.doneText : s.todo }}</p>
          </button>
        </li>
      </ol>
    </section>

    <!-- ═══════════════ NAVEGACIÓN ═══════════════ -->
    <nav class="flex flex-wrap gap-2 border-b border-gray-200" aria-label="Secciones de WhatsApp">
      <button v-for="(t, i) in tabs" :key="t.label" type="button"
              class="relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors -mb-px border-b-2"
              :class="tab === i ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'"
              :aria-current="tab === i ? 'page' : undefined" @click="tab = i">
        <UIcon :name="t.icon" class="w-4 h-4" />
        {{ t.label }}
        <span v-if="t.count !== undefined" class="text-[11px] rounded-full px-1.5 py-0.5"
              :class="tab === i ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'">{{ t.count }}</span>
      </button>
    </nav>

    <!-- ═══════════════ PROVEEDORES ═══════════════ -->
    <div v-if="tab === 0" class="space-y-4">
      <div class="flex flex-wrap justify-between items-center gap-3">
        <p class="text-sm text-gray-500">Cada conexión es una App de Meta con su token permanente. Una App puede tener varios números.</p>
        <UButton v-if="providers.length" icon="i-heroicons-plus" color="emerald" variant="soft" @click="openProvider()">Otra App de Meta</UButton>
      </div>

      <div v-if="loadingProviders" class="grid gap-4">
        <div v-for="i in 2" :key="i" class="h-40 rounded-2xl bg-gray-100 animate-pulse" />
      </div>

      <!-- Estado vacío -->
      <div v-else-if="!providers.length" class="rounded-2xl border-2 border-dashed border-emerald-200 bg-emerald-50/40 p-10">
        <div class="max-w-2xl mx-auto text-center space-y-4">
          <div class="mx-auto w-16 h-16 rounded-2xl bg-emerald-100 flex items-center justify-center">
            <UIcon name="i-heroicons-link" class="w-8 h-8 text-emerald-600" />
          </div>
          <h3 class="text-lg font-semibold text-gray-900">Conecta tu App de Meta</h3>
          <p class="text-sm text-gray-600">Necesitas tres datos de <strong>developers.facebook.com</strong>. Si aún no los tienes, la guía te lleva paso a paso.</p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
            <div v-for="r in requirements" :key="r.title" class="rounded-xl bg-white border border-emerald-100 p-3">
              <UIcon :name="r.icon" class="w-5 h-5 text-emerald-600" />
              <p class="text-sm font-medium mt-1">{{ r.title }}</p>
              <p class="text-xs text-gray-500">{{ r.text }}</p>
            </div>
          </div>
          <div class="flex justify-center gap-2 pt-2">
            <UButton color="emerald" icon="i-heroicons-plus" @click="openProvider()">Conectar App de Meta</UButton>
            <UButton color="gray" variant="ghost" icon="i-heroicons-book-open" @click="tab = 3">Ver guía</UButton>
          </div>
        </div>
      </div>

      <!-- Conexiones -->
      <article v-for="p in providers" :key="p.id" class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <header class="flex flex-wrap items-center gap-3 px-5 py-4 border-b border-gray-100">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center"
               :class="providerHealth(p).ok ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'">
            <UIcon name="i-heroicons-cube-transparent" class="w-5 h-5" />
          </div>
          <div class="min-w-0">
            <h3 class="font-semibold text-gray-900 truncate">{{ p.name }}</h3>
            <p class="text-xs text-gray-500 font-mono">App {{ p.app_id }} · Graph {{ p.api_version }}</p>
          </div>
          <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
                :class="providerHealth(p).ok ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'">
            <span class="w-2 h-2 rounded-full" :class="providerHealth(p).ok ? 'bg-emerald-500' : 'bg-amber-500'" />
            {{ providerHealth(p).label }}
          </span>
          <div class="ml-auto flex gap-1">
            <UButton size="xs" icon="i-heroicons-signal" color="gray" variant="outline" :loading="busy === `ptest-${p.id}`" @click="testProvider(p)">Probar token</UButton>
            <UButton size="xs" icon="i-heroicons-shield-check" color="gray" variant="outline" :loading="busy === `wcheck-${p.id}`" @click="checkWebhook(p)">Probar webhook</UButton>
            <UButton size="xs" icon="i-heroicons-pencil" color="gray" variant="ghost" aria-label="Editar conexión" @click="openProvider(p)" />
            <UButton size="xs" icon="i-heroicons-trash" color="red" variant="ghost" aria-label="Eliminar conexión" @click="removeProvider(p)" />
          </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-5">
          <!-- Datos para pegar en Meta -->
          <div class="lg:col-span-3 p-5 space-y-3 lg:border-r border-gray-100">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Pega esto en Meta → WhatsApp → Configuración → Webhook</p>
            <div class="rounded-xl bg-gray-900 text-gray-100 p-3 space-y-2">
              <div class="flex items-center gap-2">
                <span class="text-[10px] uppercase tracking-wide text-gray-400 w-24 flex-shrink-0">Callback URL</span>
                <code class="flex-1 text-xs break-all text-emerald-300">{{ p.webhook_url }}</code>
                <UButton size="2xs" color="gray" variant="ghost" icon="i-heroicons-clipboard-document" class="text-gray-300 hover:text-white"
                         aria-label="Copiar Callback URL" @click="copy(p.webhook_url)" />
              </div>
              <div class="flex items-center gap-2">
                <span class="text-[10px] uppercase tracking-wide text-gray-400 w-24 flex-shrink-0">Verify token</span>
                <code class="flex-1 text-xs break-all text-emerald-300">{{ p.verify_token }}</code>
                <UButton size="2xs" color="gray" variant="ghost" icon="i-heroicons-clipboard-document" class="text-gray-300 hover:text-white"
                         aria-label="Copiar verify token" @click="copy(p.verify_token)" />
                <UButton size="2xs" color="gray" variant="ghost" icon="i-heroicons-arrow-path" class="text-gray-300 hover:text-white"
                         aria-label="Regenerar verify token" :loading="busy === `regen-${p.id}`" @click="regenerateToken(p)" />
              </div>
              <div class="flex items-center gap-2">
                <span class="text-[10px] uppercase tracking-wide text-gray-400 w-24 flex-shrink-0">Campo</span>
                <code class="flex-1 text-xs text-emerald-300">messages</code>
              </div>
            </div>
            <div v-if="p.webhook_url && (!p.webhook_url.startsWith('https://') || isIpUrl(p.webhook_url))"
                 class="flex gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
              <UIcon name="i-heroicons-exclamation-triangle" class="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>Meta solo entrega mensajes a un <strong>dominio público con HTTPS y certificado válido</strong>. Esta URL usa
                {{ p.webhook_url.startsWith('https://') ? 'una IP' : 'HTTP' }}: define <code>PUBLIC_BASE_URL=https://tu-dominio</code> en el <code>.env</code> del servidor.</span>
            </div>
            <div v-if="p.last_error" class="flex gap-2 rounded-xl bg-red-50 border border-red-200 p-3 text-xs text-red-700">
              <UIcon name="i-heroicons-x-circle" class="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{{ p.last_error }}</span>
            </div>
          </div>

          <!-- Checklist de la conexión -->
          <dl class="lg:col-span-2 p-5 space-y-2.5 text-sm bg-gray-50/60">
            <div v-for="c in providerChecks(p)" :key="c.label" class="flex items-start gap-2">
              <UIcon :name="c.ok ? 'i-heroicons-check-circle' : 'i-heroicons-exclamation-circle'"
                     class="w-5 h-5 flex-shrink-0" :class="c.ok ? 'text-emerald-500' : 'text-amber-500'" />
              <div class="min-w-0">
                <dt class="font-medium text-gray-800">{{ c.label }}</dt>
                <dd class="text-xs text-gray-500">{{ c.detail }}</dd>
              </div>
            </div>
          </dl>
        </div>
      </article>
    </div>

    <!-- ═══════════════ LÍNEAS ═══════════════ -->
    <div v-if="tab === 1" class="space-y-4">
      <div class="flex flex-wrap justify-between items-center gap-3">
        <p class="text-sm text-gray-500">Cada número de WhatsApp Business se conecta con su Phone Number ID y su cuenta (WABA).</p>
        <UButton icon="i-heroicons-plus" color="emerald" :disabled="!providers.length" @click="openLine()">Agregar número</UButton>
      </div>
      <div v-if="!providers.length" class="flex gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
        <UIcon name="i-heroicons-information-circle" class="w-5 h-5 flex-shrink-0" />
        Primero conecta tu App de Meta en la sección <button type="button" class="underline font-medium" @click="tab = 0">Conexión</button>.
      </div>

      <div v-if="loadingLines" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="h-56 rounded-2xl bg-gray-100 animate-pulse" />
      </div>
      <div v-else-if="providers.length && !lines.length" class="rounded-2xl border-2 border-dashed border-gray-200 p-10 text-center space-y-3">
        <UIcon name="i-heroicons-device-phone-mobile" class="w-10 h-10 text-gray-300 mx-auto" />
        <p class="text-gray-500 text-sm">Todavía no hay números conectados.</p>
        <UButton color="emerald" icon="i-heroicons-plus" @click="openLine()">Agregar el primer número</UButton>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <article v-for="row in lines" :key="row.id" class="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col"
                 :class="{ 'opacity-70': !row.is_active }">
          <div class="wa-line-head px-5 py-4 text-white relative">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="text-xs text-emerald-100/90 truncate">{{ row.name }} · {{ row.provider_name }}</p>
                <p class="text-xl font-semibold tracking-wide mt-0.5">{{ row.display_phone_number || 'Sin verificar' }}</p>
                <p class="text-xs text-emerald-50/80 truncate flex items-center gap-1">
                  <UIcon v-if="row.verified_name" name="i-heroicons-check-badge" class="w-3.5 h-3.5" />
                  {{ row.verified_name || `ID ${row.phone_number_id}` }}
                </p>
              </div>
              <span class="rounded-full bg-white/15 px-2 py-0.5 text-[11px] font-medium whitespace-nowrap">{{ lineStatusLabel(row.status) }}</span>
            </div>
          </div>

          <div class="px-5 py-4 space-y-3 flex-1">
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="rounded-lg bg-gray-50 py-2">
                <p class="text-lg font-bold text-gray-900">{{ row.open_conversations }}</p>
                <p class="text-[10px] uppercase text-gray-500">Chats abiertos</p>
              </div>
              <div class="rounded-lg bg-gray-50 py-2">
                <p class="text-lg font-bold text-gray-900">{{ row.templates_count }}</p>
                <p class="text-[10px] uppercase text-gray-500">Plantillas</p>
              </div>
              <div class="rounded-lg bg-gray-50 py-2" :title="'Calidad del número según Meta'">
                <p class="flex items-center justify-center gap-1 h-7">
                  <span class="w-2.5 h-2.5 rounded-full" :class="qualityDot(row.quality_rating)" />
                  <span class="text-sm font-semibold text-gray-800">{{ qualityLabel(row.quality_rating) }}</span>
                </p>
                <p class="text-[10px] uppercase text-gray-500">Calidad</p>
              </div>
            </div>

            <ul class="space-y-1.5 text-xs">
              <li class="flex items-center gap-2">
                <UIcon :name="row.webhook_subscribed ? 'i-heroicons-check-circle' : 'i-heroicons-exclamation-circle'"
                       class="w-4 h-4" :class="row.webhook_subscribed ? 'text-emerald-500' : 'text-amber-500'" />
                {{ row.webhook_subscribed ? 'Recibe mensajes (webhook suscrito)' : 'Aún no recibe mensajes: suscribe el webhook' }}
              </li>
              <li class="flex items-center gap-2 text-gray-600">
                <UIcon name="i-heroicons-arrows-right-left" class="w-4 h-4 text-gray-400" />
                {{ row.auto_assign ? `Asignación automática · máx ${row.max_chats_per_agent} por agente` : 'Asignación manual' }}
              </li>
              <li class="flex items-center gap-2 text-gray-600">
                <UIcon name="i-heroicons-megaphone" class="w-4 h-4 text-gray-400" />
                {{ row.default_campaign_name || 'Sin campaña asociada' }}
              </li>
              <li class="flex items-center gap-2 text-gray-600">
                <UIcon name="i-heroicons-clock" class="w-4 h-4 text-gray-400" />
                {{ row.time_condition_name ? `Horario: ${row.time_condition_name}` : 'Atención 24/7' }}
              </li>
            </ul>
            <p v-if="row.status_detail" class="text-xs text-red-600 bg-red-50 rounded-lg px-2 py-1.5">{{ row.status_detail }}</p>
          </div>

          <footer class="border-t border-gray-100 px-3 py-2 flex items-center gap-1">
            <UTooltip v-for="a in lineQuickActions" :key="a.key" :text="a.label">
              <UButton size="xs" color="gray" variant="ghost" :icon="a.icon" :aria-label="a.label"
                       :loading="busy === `line-${a.key}-${row.id}`" @click="a.run(row)" />
            </UTooltip>
            <div class="ml-auto flex gap-1">
              <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil-square" @click="openLine(row)">Editar</UButton>
              <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" aria-label="Eliminar número" @click="removeLine(row)" />
            </div>
          </footer>
        </article>
      </div>
    </div>

    <!-- ═══════════════ PLANTILLAS ═══════════════ -->
    <div v-if="tab === 2" class="space-y-4">
      <div class="flex flex-wrap gap-2 items-center">
        <USelect v-model="tplLine" :options="[{ label: 'Todas las líneas', value: '' }, ...lineOptions]" class="w-64" @change="loadTemplates" />
        <USelect v-model="tplStatus" :options="[{ label: 'Todos los estados', value: '' }, { label: 'Aprobadas', value: 'APPROVED' }, { label: 'Pendientes', value: 'PENDING' }, { label: 'Rechazadas', value: 'REJECTED' }]" class="w-48" @change="loadTemplates" />
        <div class="ml-auto flex gap-2">
          <UButton icon="i-heroicons-arrow-path" color="gray" variant="outline" :disabled="!tplLine" :loading="busy === `line-sync-${tplLine}`"
                   :title="tplLine ? 'Traer plantillas desde Meta' : 'Selecciona un número'" @click="syncTemplates(lines.find(l => String(l.id) === tplLine))">Sincronizar con Meta</UButton>
          <UButton icon="i-heroicons-plus" color="emerald" :disabled="!lines.length" @click="openTemplate()">Nueva plantilla</UButton>
        </div>
      </div>
      <p class="text-xs text-gray-500 flex items-center gap-1.5">
        <UIcon name="i-heroicons-information-circle" class="w-4 h-4" />
        Pasadas 24 h desde el último mensaje del cliente solo se pueden enviar plantillas aprobadas. Las nuevas quedan en revisión de Meta (minutos u horas).
      </p>

      <div v-if="loadingTemplates" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="h-48 rounded-2xl bg-gray-100 animate-pulse" />
      </div>
      <div v-else-if="!templates.length" class="rounded-2xl border-2 border-dashed border-gray-200 p-10 text-center space-y-3">
        <UIcon name="i-heroicons-document-text" class="w-10 h-10 text-gray-300 mx-auto" />
        <p class="text-gray-500 text-sm">No hay plantillas. Sincroniza un número con Meta o crea una nueva.</p>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <article v-for="row in templates" :key="row.id" class="rounded-2xl border border-gray-200 bg-white overflow-hidden flex flex-col">
          <header class="px-4 py-3 flex items-start gap-2 border-b border-gray-100">
            <div class="min-w-0 flex-1">
              <p class="font-mono text-sm text-gray-900 truncate">{{ row.name }}</p>
              <p class="text-xs text-gray-500">{{ row.line_name }} · {{ row.language }} · {{ categoryLabel(row.category) }}</p>
            </div>
            <span class="rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap" :class="tplStatusClass(row.status)">
              {{ tplStatusLabel(row.status) }}
            </span>
          </header>
          <div class="wa-wallpaper flex-1 p-4">
            <div class="wa-bubble">
              <p v-if="row.header_text" class="font-semibold text-sm mb-1">{{ row.header_text }}</p>
              <p class="text-sm whitespace-pre-line line-clamp-6">{{ row.body_text || '—' }}</p>
              <p class="text-[10px] text-gray-400 text-right mt-1">{{ row.body_param_count ? `${row.body_param_count} variable(s)` : 'Sin variables' }}</p>
            </div>
          </div>
          <footer class="px-4 py-2 flex items-center justify-between border-t border-gray-100">
            <p v-if="row.rejected_reason && row.rejected_reason !== 'NONE'" class="text-xs text-red-600 truncate" :title="row.rejected_reason">{{ row.rejected_reason }}</p>
            <span v-else class="text-[11px] text-gray-400">Actualizada {{ fmtDateTime(row.updated_at) }}</span>
            <UButton size="xs" icon="i-heroicons-trash" color="red" variant="ghost" aria-label="Eliminar plantilla" @click="removeTemplate(row)" />
          </footer>
        </article>
      </div>
    </div>

    <!-- ═══════════════ GUÍA ═══════════════ -->
    <div v-if="tab === 3" class="space-y-4">
      <!-- Webhook de ESTA instalación -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <header class="flex flex-wrap items-center gap-3 px-5 py-4 border-b border-gray-100">
          <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
            <UIcon name="i-heroicons-globe-alt" class="w-5 h-5" />
          </div>
          <div class="min-w-0 flex-1">
            <h2 class="font-semibold text-gray-900">Webhook de este servidor</h2>
            <p class="text-xs text-gray-500">Esto es lo que debes pegar en Meta → WhatsApp → Configuración → Webhook</p>
          </div>
          <span v-if="webhookInfo" class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
                :class="webhookInfo.public_ready ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'">
            <span class="w-2 h-2 rounded-full" :class="webhookInfo.public_ready ? 'bg-emerald-500' : 'bg-amber-500'" />
            {{ webhookInfo.public_ready ? 'Dirección pública válida' : 'No alcanzable por Meta' }}
          </span>
        </header>

        <div class="p-5 space-y-4">
          <div v-if="!webhookInfo" class="h-24 rounded-xl bg-gray-100 animate-pulse" />
          <template v-else>
            <!-- Con conexiones: URL exacta por App -->
            <div v-for="p in webhookInfo.providers" :key="p.id" class="rounded-xl bg-gray-900 text-gray-100 p-4 space-y-2">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm font-semibold text-white">{{ p.name }} <span class="text-xs font-normal text-gray-400 font-mono">· App {{ p.app_id }}</span></p>
                <span class="text-[11px]" :class="p.webhook_verified ? 'text-emerald-300' : 'text-amber-300'">
                  {{ p.webhook_verified ? '✓ Verificado por Meta' : 'Pendiente de verificar en Meta' }}
                </span>
              </div>
              <div v-for="f in [
                { label: 'URL de devolución de llamada', value: p.webhook_url },
                { label: 'Token de verificación', value: p.verify_token },
                { label: 'Campo a suscribir', value: 'messages' },
              ]" :key="f.label" class="flex items-center gap-2">
                <span class="text-[10px] uppercase tracking-wide text-gray-400 w-44 flex-shrink-0">{{ f.label }}</span>
                <code class="flex-1 text-xs break-all text-emerald-300">{{ f.value }}</code>
                <UButton size="2xs" color="gray" variant="ghost" icon="i-heroicons-clipboard-document" class="text-gray-300 hover:text-white"
                         :aria-label="`Copiar ${f.label}`" @click="copy(f.value)" />
              </div>
              <div class="flex flex-wrap items-center gap-2 pt-1">
                <UButton size="xs" color="white" variant="solid" icon="i-heroicons-shield-check" :loading="busy === `wcheck-${p.id}`" @click="checkWebhook(p)">
                  Probar que Meta pueda llegar
                </UButton>
                <p v-if="webhookChecks[p.id]" class="text-xs" :class="webhookChecks[p.id].ok ? 'text-emerald-300' : 'text-red-300'">
                  {{ webhookChecks[p.id].message }}
                </p>
              </div>
            </div>

            <!-- Sin conexiones: plantilla de la URL -->
            <div v-if="!webhookInfo.providers.length" class="rounded-xl bg-gray-900 text-gray-100 p-4 space-y-2">
              <p class="text-[10px] uppercase tracking-wide text-gray-400">URL de devolución de llamada</p>
              <code class="block text-xs break-all text-emerald-300">{{ webhookInfo.url_template }}</code>
              <p class="text-xs text-gray-400"><code class="text-amber-300">{APP_ID}</code> se reemplaza por el ID de tu App de Meta. El token de verificación se genera al conectar la App.</p>
              <UButton size="xs" color="white" icon="i-heroicons-plus" @click="openProvider()">Conectar App de Meta para obtener la URL completa</UButton>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div class="rounded-xl border border-gray-200 p-3">
                <p class="text-gray-500">Dominio usado</p>
                <p class="font-mono font-medium text-gray-900 break-all">{{ webhookInfo.base_url || '—' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 p-3">
                <p class="text-gray-500">Origen</p>
                <p class="font-medium text-gray-900">{{ webhookInfo.source === 'PUBLIC_BASE_URL' ? 'PUBLIC_BASE_URL del .env' : 'Dirección con la que abriste la web' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 p-3">
                <p class="text-gray-500">HTTPS / dominio público</p>
                <p class="font-medium" :class="webhookInfo.public_ready ? 'text-emerald-700' : 'text-amber-700'">
                  {{ webhookInfo.is_https ? 'HTTPS' : 'Sin HTTPS' }} · {{ webhookInfo.is_ip ? 'IP' : 'Dominio' }}{{ webhookInfo.is_private ? ' privado' : '' }}
                </p>
              </div>
            </div>

            <div v-if="webhookInfo.issues.length" class="flex gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-900">
              <UIcon name="i-heroicons-exclamation-triangle" class="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div class="space-y-1">
                <p v-for="i in webhookInfo.issues" :key="i">{{ i }}</p>
                <p>Solución: publica el servidor con un dominio (ej. <code>omni.tuempresa.com</code>) apuntando a su IP pública, instala un certificado válido
                  (Let's Encrypt), abre el puerto 443 y define <code>PUBLIC_BASE_URL=https://omni.tuempresa.com</code> en el <code>.env</code>. Luego redespliega.</p>
              </div>
            </div>
          </template>
        </div>
      </section>

      <!-- Cómo funciona por instalación -->
      <section class="rounded-2xl border border-gray-200 bg-white p-5">
        <h2 class="font-semibold text-gray-900 flex items-center gap-2">
          <UIcon name="i-heroicons-server-stack" class="w-5 h-5 text-emerald-600" /> ¿Cómo funcionan los webhooks en cada instalación?
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 text-sm text-gray-600">
          <div v-for="w in webhookFaq" :key="w.title" class="flex gap-3">
            <UIcon :name="w.icon" class="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <p class="font-medium text-gray-900">{{ w.title }}</p>
              <p class="text-xs mt-0.5 leading-relaxed">{{ w.text }}</p>
            </div>
          </div>
        </div>
      </section>
      <ol class="relative border-l-2 border-emerald-100 ml-4 space-y-6">
        <li v-for="(step, i) in guide" :key="i" class="pl-8 relative">
          <span class="absolute -left-[17px] top-0 w-8 h-8 rounded-full bg-emerald-600 text-white text-sm font-bold flex items-center justify-center ring-4 ring-white">{{ i + 1 }}</span>
          <div class="rounded-2xl border border-gray-200 bg-white p-4">
            <h3 class="font-semibold text-gray-900">{{ step.title }}</h3>
            <ul class="mt-2 space-y-1.5 text-sm text-gray-600">
              <li v-for="(line, j) in step.items" :key="j" class="flex gap-2">
                <UIcon name="i-heroicons-chevron-right" class="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>{{ line }}</span>
              </li>
            </ul>
            <a v-if="step.link" :href="step.link" target="_blank" rel="noopener noreferrer"
               class="mt-3 text-sm text-emerald-700 hover:underline inline-flex items-center gap-1 font-medium">
              {{ step.linkLabel }} <UIcon name="i-heroicons-arrow-top-right-on-square" class="w-4 h-4" />
            </a>
          </div>
        </li>
      </ol>
    </div>

    <!-- ═══════════════ MODAL PROVEEDOR ═══════════════ -->
    <UModal v-model="pForm.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ pForm.id ? 'Editar conexión' : 'Conectar App de Meta' }}</h3></template>
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
          <UFormGroup label="Horario de atención" hint="Condiciones horarias de telefonía">
            <USelect v-model="lForm.time_condition" :options="[{ label: 'Siempre abierto', value: '' }, ...timeConditionOptions]" />
          </UFormGroup>
          <div class="flex items-end"><NuxtLink to="/time-conditions" class="text-xs text-sky-600 hover:underline">Gestionar horarios →</NuxtLink></div>
          <UFormGroup v-if="lForm.time_condition" label="Mensaje fuera de horario" class="md:col-span-2" hint="Máximo una vez cada 4 h por conversación">
            <UTextarea v-model="lForm.after_hours_message" :rows="2" placeholder="Gracias por escribirnos. Atendemos de lunes a viernes de 8:00 a 18:00; te responderemos apenas abramos." />
          </UFormGroup>
          <UFormGroup label="Palabras de baja (opt-out)" hint="Separadas por coma">
            <UInput v-model="lForm.opt_out_keywords" placeholder="BAJA,STOP,CANCELAR" />
          </UFormGroup>
          <UFormGroup label="Palabras de alta (opt-in)" hint="Separadas por coma">
            <UInput v-model="lForm.opt_in_keywords" placeholder="ALTA,SUSCRIBIR" />
          </UFormGroup>
          <UFormGroup label="Respuesta a la baja" class="md:col-span-2"><UInput v-model="lForm.opt_out_reply" /></UFormGroup>
          <UFormGroup label="Respuesta al alta" class="md:col-span-2"><UInput v-model="lForm.opt_in_reply" /></UFormGroup>
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

const tabs = computed(() => [
  { label: 'Conexión', icon: 'i-heroicons-link', count: providers.value.length },
  { label: 'Números', icon: 'i-heroicons-device-phone-mobile', count: lines.value.length },
  { label: 'Plantillas', icon: 'i-heroicons-document-text', count: templates.value.length },
  { label: 'Guía', icon: 'i-heroicons-book-open', count: undefined as number | undefined },
])
const tab = ref(0)
const busy = ref('')

// ── Resumen y estado de la conexión ───────────────────────────────────────
const approvedTemplates = computed(() => templates.value.filter(t => String(t.status).toUpperCase() === 'APPROVED').length)
const connectedLines = computed(() => lines.value.filter(l => l.status === 'connected' && l.is_active))
const lastEvent = computed(() => providers.value.map(p => p.last_webhook_at).filter(Boolean).sort().pop() || null)

const heroStats = computed(() => [
  { label: 'Números activos', value: `${connectedLines.value.length}/${lines.value.length}`, hint: lines.value.length ? '' : 'Sin números aún' },
  { label: 'Chats abiertos', value: lines.value.reduce((n, l) => n + (l.open_conversations || 0), 0), hint: '' },
  { label: 'Plantillas aprobadas', value: approvedTemplates.value, hint: templates.value.length ? `de ${templates.value.length}` : '' },
  { label: 'Último mensaje de Meta', value: lastEvent.value ? relTime(lastEvent.value) : '—', hint: lastEvent.value ? fmtDateTime(lastEvent.value) : 'Aún no llegan eventos' },
])

const setupSteps = computed(() => {
  const p = providers.value
  const steps = [
    { key: 'app', title: 'App de Meta', done: p.length > 0, todo: 'Conecta tu App con su token', doneText: `${p.length} conectada(s)`, go: () => { tab.value = 0; if (!p.length) openProvider() } },
    { key: 'token', title: 'Token válido', done: p.some(x => x.has_access_token && !x.last_error), todo: 'Usa "Probar token"', doneText: 'Token funcionando', go: () => { tab.value = 0 } },
    { key: 'webhook', title: 'Webhook', done: p.some(x => x.webhook_verified), todo: 'Pega la URL y el token en Meta', doneText: 'Verificado por Meta', go: () => { tab.value = 0 } },
    { key: 'number', title: 'Número', done: connectedLines.value.length > 0, todo: 'Agrega y verifica un número', doneText: `${connectedLines.value.length} conectado(s)`, go: () => { tab.value = 1; if (!lines.value.length && p.length) openLine() } },
    { key: 'subscribe', title: 'Recepción', done: lines.value.some(l => l.webhook_subscribed), todo: 'Suscribe el número al webhook', doneText: 'Recibiendo mensajes', go: () => { tab.value = 1 } },
    { key: 'templates', title: 'Plantillas', done: approvedTemplates.value > 0, todo: 'Sincroniza o crea plantillas', doneText: `${approvedTemplates.value} aprobada(s)`, go: () => { tab.value = 2 } },
  ]
  const firstPending = steps.findIndex(s => !s.done)
  return steps.map((s, i) => ({ ...s, current: i === firstPending }))
})
const setupDone = computed(() => setupSteps.value.filter(s => s.done).length)
const setupPct = computed(() => Math.round(setupDone.value / setupSteps.value.length * 100))

const requirements = [
  { icon: 'i-heroicons-identification', title: 'App ID', text: 'Panel de tu App en Meta for Developers' },
  { icon: 'i-heroicons-key', title: 'Token permanente', text: 'Usuario del Sistema con permisos de WhatsApp' },
  { icon: 'i-heroicons-lock-closed', title: 'App Secret', text: 'Configuración → Básica (valida la firma)' },
]

function providerChecks(p: any) {
  return [
    { label: 'Token de acceso', ok: p.has_access_token && !p.last_error,
      detail: p.has_access_token ? `Guardado cifrado ${p.access_token_hint}` : 'Falta el token del Usuario del Sistema' },
    { label: 'Firma de seguridad', ok: p.has_app_secret,
      detail: p.has_app_secret ? 'Se valida X-Hub-Signature-256 en cada evento' : 'Agrega el App Secret para validar que los eventos vienen de Meta' },
    { label: 'Webhook', ok: p.webhook_verified,
      detail: p.webhook_verified ? `Verificado · último evento ${fmtDateTime(p.last_webhook_at)}` : 'Meta aún no ha verificado la URL' },
    { label: 'Números', ok: p.lines_count > 0, detail: p.lines_count ? `${p.lines_count} número(s) en esta App` : 'Agrega el primer número' },
  ]
}
function providerHealth(p: any) {
  if (!p.is_active) return { ok: false, label: 'Inactiva' }
  if (p.last_error) return { ok: false, label: 'Con errores' }
  if (!p.webhook_verified) return { ok: false, label: 'Falta verificar webhook' }
  return { ok: true, label: 'Operativa' }
}

const lineQuickActions = [
  { key: 'test', label: 'Verificar número en Meta', icon: 'i-heroicons-signal', run: (r: any) => testLine(r) },
  { key: 'sub', label: 'Suscribir webhook', icon: 'i-heroicons-bell-alert', run: (r: any) => subscribeLine(r) },
  { key: 'sync', label: 'Sincronizar plantillas', icon: 'i-heroicons-arrow-path', run: (r: any) => syncTemplates(r) },
  { key: 'send', label: 'Enviar mensaje de prueba', icon: 'i-heroicons-paper-airplane', run: (r: any) => openTest(r) },
]

const qualityDot = (q: string) => ({ GREEN: 'bg-emerald-500', YELLOW: 'bg-amber-400', RED: 'bg-red-500' } as any)[String(q || '').toUpperCase()] || 'bg-gray-300'
const qualityLabel = (q: string) => ({ GREEN: 'Alta', YELLOW: 'Media', RED: 'Baja' } as any)[String(q || '').toUpperCase()] || '—'
const categoryLabel = (c: string) => ({ MARKETING: 'Marketing', UTILITY: 'Utilidad', AUTHENTICATION: 'Autenticación' } as any)[String(c || '').toUpperCase()] || c || '—'
const tplStatusLabel = (s: string) => ({ APPROVED: 'Aprobada', PENDING: 'En revisión', REJECTED: 'Rechazada', PAUSED: 'Pausada', DISABLED: 'Deshabilitada', DELETED: 'Eliminada en Meta' } as any)[String(s || '').toUpperCase()] || s || '—'
const tplStatusClass = (s: string) => ({
  APPROVED: 'bg-emerald-50 text-emerald-700', PENDING: 'bg-amber-50 text-amber-700', REJECTED: 'bg-red-50 text-red-700',
  PAUSED: 'bg-orange-50 text-orange-700',
} as any)[String(s || '').toUpperCase()] || 'bg-gray-100 text-gray-600'
const relTime = (v: string) => {
  const diff = Date.now() - new Date(v).getTime()
  if (diff < 60000) return 'ahora'
  if (diff < 3600000) return `hace ${Math.floor(diff / 60000)} min`
  if (diff < 86400000) return `hace ${Math.floor(diff / 3600000)} h`
  return `hace ${Math.floor(diff / 86400000)} d`
}

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
const timeConditionOptions = ref<{ label: string, value: string }[]>([])
async function loadCampaigns() {
  try {
    campaignOptions.value = http.results(await http.get('/campaigns/'))
      .map((c: any) => ({ label: c.name, value: String(c.id) }))
  } catch { /* opcional */ }
  try {
    timeConditionOptions.value = http.results(await http.get('/telephony/time-conditions/'))
      .map((t: any) => ({ label: t.name, value: String(t.id) }))
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
    loadWebhookInfo()
    toast.add({ title: 'Token regenerado', description: 'Actualízalo también en Meta.', color: 'green' })
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
  time_condition: '', after_hours_message: '',
  opt_out_keywords: 'BAJA,STOP,CANCELAR', opt_in_keywords: 'ALTA,SUSCRIBIR', opt_out_reply: '', opt_in_reply: '',
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
    time_condition: l?.time_condition ? String(l.time_condition) : '', after_hours_message: l?.after_hours_message ?? '',
    opt_out_keywords: l?.opt_out_keywords ?? 'BAJA,STOP,CANCELAR', opt_in_keywords: l?.opt_in_keywords ?? 'ALTA,SUSCRIBIR',
    opt_out_reply: l?.opt_out_reply ?? 'Listo, no volverás a recibir mensajes promocionales. Escribe ALTA para suscribirte de nuevo.',
    opt_in_reply: l?.opt_in_reply ?? '¡Gracias! Quedaste suscrito a nuestras novedades.',
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
      time_condition: lForm.time_condition ? Number(lForm.time_condition) : null,
      after_hours_message: lForm.after_hours_message,
      opt_out_keywords: lForm.opt_out_keywords, opt_in_keywords: lForm.opt_in_keywords,
      opt_out_reply: lForm.opt_out_reply, opt_in_reply: lForm.opt_in_reply,
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
// ── Webhook de esta instalación ───────────────────────────────────────────
const webhookInfo = ref<any>(null)
const webhookChecks = reactive<Record<number, { ok: boolean, message: string }>>({})

async function loadWebhookInfo() {
  try { webhookInfo.value = await http.get('/messaging/whatsapp/providers/webhook-info/') }
  catch (e) { apiError(e, 'No se pudo obtener la URL del webhook') }
}

async function checkWebhook(p: any) {
  busy.value = `wcheck-${p.id}`
  try {
    const r: any = await http.post(`/messaging/whatsapp/providers/${p.id}/check-webhook/`)
    webhookChecks[p.id] = { ok: r.ok, message: r.message }
    toast.add({ title: r.ok ? 'Webhook accesible' : 'El webhook no es accesible', description: r.message, color: r.ok ? 'green' : 'red', timeout: 8000 })
  } catch (e) { apiError(e, 'No se pudo probar el webhook') }
  finally { busy.value = '' }
}

const webhookFaq = [
  { icon: 'i-heroicons-server', title: 'Cada servidor tiene su propia URL',
    text: 'La URL es https://<dominio de ese servidor>/api/messaging/webhooks/meta/<APP_ID>/. Se arma con PUBLIC_BASE_URL del .env de cada instalación, así que dos servidores nunca comparten URL.' },
  { icon: 'i-heroicons-key', title: 'El token de verificación es único',
    text: 'Se genera al azar al conectar cada App de Meta y solo existe en ese servidor. Puedes regenerarlo; después debes actualizarlo en Meta.' },
  { icon: 'i-heroicons-cube-transparent', title: 'Una App de Meta por instalación',
    text: 'Meta permite una sola URL de webhook por App. Si el mismo cliente o App se usa en dos servidores, solo uno recibirá los mensajes: usa una App distinta para cada instalación (o cliente).' },
  { icon: 'i-heroicons-arrows-right-left', title: 'Varias Apps en un mismo servidor',
    text: 'Un servidor puede atender varias Apps: el APP_ID en la URL identifica cuál es. Cada App tiene su propio token, firma y números.' },
  { icon: 'i-heroicons-shield-check', title: 'Seguridad',
    text: 'Cada evento se valida con la firma X-Hub-Signature-256 usando el App Secret; los eventos sin firma válida se rechazan.' },
  { icon: 'i-heroicons-arrow-path-rounded-square', title: 'Si cambias de dominio o servidor',
    text: 'Actualiza PUBLIC_BASE_URL, redespliega y cambia la URL en Meta. En una reinstalación, el token de verificación cambia si la base de datos es nueva.' },
]

const guide = computed(() => [
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
      'En developers.facebook.com → tu App → WhatsApp → Configuración → Webhook → Editar.',
      `URL de devolución de llamada: ${webhookInfo.value?.providers?.[0]?.webhook_url || webhookInfo.value?.url_template || 'la del recuadro "Webhook de este servidor"'}`,
      `Token de verificación: ${webhookInfo.value?.providers?.[0]?.verify_token || 'se genera al conectar la App (ver recuadro superior)'}`,
      'Antes de guardar en Meta usa "Probar que Meta pueda llegar": si falla, Meta también fallará.',
      'Al guardar, Meta llama a la URL y la conexión pasa a "Webhook verificado".',
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
])

onMounted(() => {
  loadProviders()
  loadLines()
  loadTemplates()  // necesarias para el resumen y el estado de la conexión
  loadCampaigns()
  loadWebhookInfo()
})

// Mantener la URL/token del webhook al día cuando cambian las conexiones
watch(providers, () => { loadWebhookInfo() })
</script>

<style scoped>
.wa-hero {
  background: linear-gradient(135deg, #064e3b 0%, #047857 55%, #10b981 100%);
}
.wa-hero-pattern {
  position: absolute;
  inset: 0;
  opacity: 0.12;
  background-image:
    radial-gradient(circle at 20% 20%, #fff 1.5px, transparent 1.5px),
    radial-gradient(circle at 70% 60%, #fff 1px, transparent 1px);
  background-size: 28px 28px, 18px 18px;
  pointer-events: none;
}
.wa-line-head {
  background: linear-gradient(120deg, #065f46 0%, #059669 100%);
}
.wa-wallpaper {
  background-color: #ece5dd;
  background-image: radial-gradient(rgba(6, 95, 70, 0.07) 1px, transparent 1px);
  background-size: 14px 14px;
}
.wa-bubble {
  position: relative;
  max-width: 92%;
  background: #fff;
  border-radius: 0 10px 10px 10px;
  padding: 8px 10px;
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.08);
  color: #111827;
}
.wa-bubble::before {
  content: '';
  position: absolute;
  top: 0;
  left: -7px;
  border-top: 8px solid #fff;
  border-left: 8px solid transparent;
}
</style>
