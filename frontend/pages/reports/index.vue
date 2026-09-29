<template>
  <div class="space-y-6">
    <!-- Encabezado -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Reportes y KPIs</h1>
        <p class="text-sm text-gray-500 mt-1">
          {{ periodText }}
          <span v-if="tab === 0 && summary" class="text-gray-400"> · comparado con el período anterior</span>
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <UDropdown :items="exportItems" :popper="{ placement: 'bottom-end' }">
          <UButton icon="i-heroicons-arrow-down-tray" color="gray" variant="outline" :loading="exporting">
            Exportar
          </UButton>
        </UDropdown>
        <UButton icon="i-heroicons-arrow-path" :loading="loading" @click="reload">Actualizar</UButton>
      </div>
    </div>

    <!-- Filtros -->
    <UCard :ui="{ body: { padding: 'p-4' } }">
      <div class="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3 items-end">
        <UFormGroup label="Período" class="col-span-2 md:col-span-1">
          <USelect v-model="filters.period" :options="periodOptions" />
        </UFormGroup>
        <UFormGroup v-if="filters.period === 'custom'" label="Desde">
          <UInput v-model="filters.startDate" type="date" />
        </UFormGroup>
        <UFormGroup v-if="filters.period === 'custom'" label="Hasta">
          <UInput v-model="filters.endDate" type="date" />
        </UFormGroup>
        <UFormGroup label="Campaña">
          <USelect v-model="filters.campaign" :options="[{ label: 'Todas', value: '' }, ...catalogs.campaigns]" />
        </UFormGroup>
        <UFormGroup label="Cola">
          <USelect v-model="filters.queue" :options="[{ label: 'Todas', value: '' }, ...catalogs.queues]" />
        </UFormGroup>
        <UFormGroup label="Agente">
          <USelect v-model="filters.agent" :options="[{ label: 'Todos', value: '' }, ...catalogs.agents]" />
        </UFormGroup>
        <UFormGroup label="Dirección">
          <USelect v-model="filters.direction" :options="directionOptions" />
        </UFormGroup>
        <UFormGroup label="Umbral SL (s)" help="Nivel de servicio">
          <UInput v-model.number="filters.sla" type="number" min="1" max="600" />
        </UFormGroup>
        <UButton block :loading="loading" @click="reload">Aplicar</UButton>
      </div>
    </UCard>

    <UTabs v-model="tab" :items="tabs" />

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" :title="error" />

    <!-- ═════════════════ RESUMEN ═════════════════ -->
    <div v-if="tab === 0" class="space-y-6">
      <template v-if="summary">
        <section aria-label="Volumen">
          <h2 class="section-title">Volumen</h2>
          <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
            <ReportKpi label="Llamadas" :value="n(cur.totalCalls)" :current="cur.totalCalls" :previous="prev.totalCalls"
                       :previous-text="n(prev.totalCalls)" :sub="`${n(cur.inboundCalls)} ent · ${n(cur.outboundCalls)} sal`" />
            <ReportKpi label="Atendidas" :value="n(cur.answeredCalls)" :current="cur.answeredCalls" :previous="prev.answeredCalls"
                       :previous-text="n(prev.answeredCalls)" :sub="`${cur.answerRate}% del total`" />
            <ReportKpi label="Abandonadas" :value="n(cur.abandonedCalls)" :current="cur.abandonedCalls" :previous="prev.abandonedCalls"
                       invert :previous-text="n(prev.abandonedCalls)" :sub="`${n(cur.shortAbandoned)} cortas (< 5 s)`" />
            <ReportKpi label="No contestadas" :value="n(cur.missedCalls)" :current="cur.missedCalls" :previous="prev.missedCalls"
                       invert :previous-text="n(prev.missedCalls)" sub="Ocupado / sin respuesta / canceladas" />
            <ReportKpi label="Clientes únicos" :value="n(cur.uniqueCallers)" :current="cur.uniqueCallers" :previous="prev.uniqueCallers"
                       :previous-text="n(prev.uniqueCallers)" :sub="`${n(cur.repeatCallers)} volvieron a llamar`" />
            <ReportKpi label="Agentes conectados" :value="n(cur.agentsWorked)" :sub="`${fmtDur(cur.loggedTime)} conectados`" />
          </div>
        </section>

        <section aria-label="Servicio">
          <h2 class="section-title">Servicio y experiencia</h2>
          <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
            <ReportKpi label="Nivel de servicio" :value="`${cur.serviceLevel}%`" :current="cur.serviceLevel"
                       :previous="prev.serviceLevel" points :previous-text="`${prev.serviceLevel}%`"
                       :tone="tone(cur.serviceLevel, 80, 60)" :sub="`Contestadas en ≤ ${cur.slaThreshold} s`"
                       hint="Entrantes contestadas dentro del umbral ÷ (entrantes − abandonos de menos de 5 s). Meta típica 80/20." />
            <ReportKpi label="Abandono" :value="`${cur.abandonRate}%`" :current="cur.abandonRate" :previous="prev.abandonRate"
                       points invert :previous-text="`${prev.abandonRate}%`" :tone="toneInv(cur.abandonRate, 5, 10)"
                       sub="Sobre llamadas entrantes" hint="Abandonadas ÷ entrantes. Meta típica < 5%." />
            <ReportKpi label="ASA" :value="fmtSec(cur.asa)" :current="cur.asa" :previous="prev.asa" invert
                       :previous-text="fmtSec(prev.asa)" :sub="`Máx. ${fmtSec(cur.maxWaitTime)}`"
                       hint="Velocidad media de respuesta: espera promedio de las entrantes contestadas." />
            <ReportKpi label="AHT (TMO)" :value="fmtSec(cur.aht)" :current="cur.aht" :previous="prev.aht" invert
                       :previous-text="fmtSec(prev.aht)" :sub="`Conv. ${fmtSec(cur.avgTalkTime)} · ACW ${fmtSec(cur.avgWrapupTime)}`"
                       hint="Tiempo medio de gestión: (conversación + retención + post-llamada) ÷ atendidas." />
            <ReportKpi label="FCR estimado" :value="`${cur.fcr}%`" :current="cur.fcr" :previous="prev.fcr" points
                       :previous-text="`${prev.fcr}%`" :tone="tone(cur.fcr, 80, 70)" :sub="`${cur.repeatRate}% rellamadas`"
                       hint="Resolución en el primer contacto estimada: clientes que no volvieron a llamar en el período." />
            <ReportKpi label="Espera al abandonar" :value="fmtSec(cur.avgAbandonWait)" :current="cur.avgAbandonWait"
                       :previous="prev.avgAbandonWait" :previous-text="fmtSec(prev.avgAbandonWait)"
                       sub="Paciencia promedio del cliente" hint="Cuánto esperan en promedio los clientes antes de colgar." />
          </div>
        </section>

        <section aria-label="Productividad">
          <h2 class="section-title">Productividad y gestión</h2>
          <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
            <ReportKpi label="Ocupación" :value="`${cur.occupancy}%`" :current="cur.occupancy" :previous="prev.occupancy" points
                       :previous-text="`${prev.occupancy}%`" :tone="cur.occupancy > 90 ? 'bad' : cur.occupancy >= 70 ? 'good' : 'warn'"
                       sub="Meta 75–85%" hint="(En llamada + post-llamada) ÷ (tiempo conectado − pausas)." />
            <ReportKpi label="Utilización" :value="`${cur.utilization}%`" :current="cur.utilization" :previous="prev.utilization"
                       points :previous-text="`${prev.utilization}%`" :sub="`Pausas ${fmtDur(cur.breakTime)}`"
                       hint="(En llamada + post-llamada) ÷ tiempo conectado total." />
            <ReportKpi label="Llamadas / hora" :value="cur.callsPerAgentHour" :current="cur.callsPerAgentHour"
                       :previous="prev.callsPerAgentHour" :previous-text="String(prev.callsPerAgentHour)"
                       sub="Atendidas por hora conectada" />
            <ReportKpi label="Contactabilidad" :value="`${cur.contactRate}%`" :current="cur.contactRate" :previous="prev.contactRate"
                       points :previous-text="`${prev.contactRate}%`" :sub="`${n(cur.machineCalls)} contestadores`"
                       hint="Salientes contestadas ÷ salientes." />
            <ReportKpi label="Conversión" :value="`${cur.conversionRate}%`" :current="cur.conversionRate"
                       :previous="prev.conversionRate" points :previous-text="`${prev.conversionRate}%`"
                       :sub="`${n(cur.successCalls)} éxitos · ${cur.typingRate}% tipificadas`"
                       hint="Llamadas tipificadas como exitosas ÷ atendidas." />
            <ReportKpi label="Transferencias" :value="`${cur.transferRate}%`" :current="cur.transferRate" :previous="prev.transferRate"
                       points invert :previous-text="`${prev.transferRate}%`" :sub="`${cur.shortCallRate}% llamadas < 10 s`" />
          </div>
        </section>

        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <!-- Tendencia diaria -->
          <UCard class="xl:col-span-2">
            <template #header>
              <div class="flex items-center justify-between">
                <h3 class="font-semibold">Tendencia diaria</h3>
                <Legend :items="[['bg-green-500', 'Atendidas'], ['bg-red-400', 'Abandonadas'], ['bg-gray-300', 'Otras']]" />
              </div>
            </template>
            <div v-if="summary.daily.length" class="overflow-x-auto">
              <div class="flex items-end gap-1 h-48 min-w-full" :style="{ minWidth: `${summary.daily.length * 22}px` }">
                <div v-for="d in summary.daily" :key="d.date" class="flex-1 flex flex-col items-center justify-end h-full group"
                     :title="`${fmtDate(d.date)}: ${d.total} llamadas · SL ${d.serviceLevel}% · abandono ${d.abandonRate}% · AHT ${fmtSec(d.aht)}`">
                  <span class="text-[10px] text-gray-500 mb-0.5">{{ d.total || '' }}</span>
                  <div class="w-full max-w-[28px] flex flex-col-reverse rounded-t overflow-hidden" :style="{ height: barPct(d.total, maxDaily) }">
                    <div class="bg-green-500" :style="{ height: segPct(d.answered, d.total) }" />
                    <div class="bg-red-400" :style="{ height: segPct(d.abandoned, d.total) }" />
                    <div class="bg-gray-300 dark:bg-gray-600 flex-1" />
                  </div>
                </div>
              </div>
              <div class="flex gap-1 mt-1" :style="{ minWidth: `${summary.daily.length * 22}px` }">
                <span v-for="d in summary.daily" :key="d.date" class="flex-1 text-center text-[10px] text-gray-400 truncate">
                  {{ shortDate(d.date) }}
                </span>
              </div>
            </div>
            <Empty v-else />
          </UCard>

          <!-- Estados -->
          <UCard>
            <template #header><h3 class="font-semibold">Resultado de las llamadas</h3></template>
            <ReportBars :items="statusItems" />
          </UCard>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <!-- Por hora -->
          <UCard class="xl:col-span-2">
            <template #header>
              <div class="flex items-center justify-between">
                <h3 class="font-semibold">Llamadas por hora</h3>
                <Legend :items="[['bg-green-500', 'Atendidas'], ['bg-red-400', 'Abandonadas'], ['bg-gray-300', 'Otras']]" />
              </div>
            </template>
            <div class="flex items-end gap-0.5 h-40">
              <div v-for="h in summary.hourly" :key="h.hour" class="flex-1 flex flex-col justify-end h-full"
                   :title="`${h.label}: ${h.total} llamadas · SL ${h.serviceLevel}% · ASA ${fmtSec(h.asa)}`">
                <div class="w-full flex flex-col-reverse rounded-t overflow-hidden" :style="{ height: barPct(h.total, maxHourly) }">
                  <div class="bg-green-500" :style="{ height: segPct(h.answered, h.total) }" />
                  <div class="bg-red-400" :style="{ height: segPct(h.abandoned, h.total) }" />
                  <div class="bg-gray-300 dark:bg-gray-600 flex-1" />
                </div>
              </div>
            </div>
            <div class="flex gap-0.5 mt-1">
              <span v-for="h in summary.hourly" :key="h.hour" class="flex-1 text-center text-[9px] text-gray-400">
                {{ h.hour % 3 === 0 ? h.hour : '' }}
              </span>
            </div>
          </UCard>

          <!-- Duración -->
          <UCard>
            <template #header><h3 class="font-semibold">Duración de las conversaciones</h3></template>
            <ReportBars :items="talkItems" color="bg-violet-500" />
          </UCard>
        </div>

        <!-- Mapa de calor -->
        <UCard>
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <h3 class="font-semibold">Mapa de calor: día de la semana × hora</h3>
              <span class="text-xs text-gray-400">Úsalo para dimensionar turnos (más oscuro = más llamadas)</span>
            </div>
          </template>
          <div class="overflow-x-auto">
            <table class="text-[10px] border-separate" style="border-spacing: 2px" aria-label="Llamadas por día y hora">
              <thead>
                <tr>
                  <th class="w-8" />
                  <th v-for="h in 24" :key="h" scope="col" class="font-normal text-gray-400 w-6">{{ h - 1 }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, di) in summary.heatmap.matrix" :key="di">
                  <th scope="row" class="text-right pr-1 font-medium text-gray-500">{{ summary.heatmap.days[di] }}</th>
                  <td v-for="(v, hi) in row" :key="hi" class="w-6 h-6 rounded text-center align-middle"
                      :style="heatStyle(v)" :title="`${summary.heatmap.days[di]} ${String(hi).padStart(2, '0')}:00 — ${v} llamadas`">
                    <span v-if="v" :class="v / (summary.heatmap.max || 1) > 0.55 ? 'text-white' : 'text-gray-700'">{{ v }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </UCard>

        <!-- Tabla diaria -->
        <UCard>
          <template #header><h3 class="font-semibold">Detalle por día</h3></template>
          <UTable :rows="summary.daily" :columns="dailyColumns" :empty-state="{ icon: 'i-heroicons-calendar', label: 'Sin datos' }">
            <template #date-data="{ row }">{{ fmtDate(row.date) }}</template>
            <template #serviceLevel-data="{ row }"><span :class="toneText(tone(row.serviceLevel, 80, 60))">{{ row.serviceLevel }}%</span></template>
            <template #abandonRate-data="{ row }"><span :class="toneText(toneInv(row.abandonRate, 5, 10))">{{ row.abandonRate }}%</span></template>
            <template #aht-data="{ row }">{{ fmtSec(row.aht) }}</template>
            <template #asa-data="{ row }">{{ fmtSec(row.asa) }}</template>
          </UTable>
        </UCard>
      </template>
      <Skeleton v-else-if="loading" />
    </div>

    <!-- ═════════════════ AGENTES ═════════════════ -->
    <div v-if="tab === 1" class="space-y-6">
      <UCard>
        <template #header>
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h3 class="font-semibold">Ranking y KPIs por agente</h3>
            <UTooltip text="Puntaje = 35% llamadas/hora (relativo al mejor) + 25% ocupación + 30% calidad (si tiene evaluaciones) + 10% sin transferencias">
              <span class="text-xs text-gray-400 inline-flex items-center gap-1">
                <UIcon name="i-heroicons-information-circle" class="w-4 h-4" /> ¿Cómo se calcula el puntaje?
              </span>
            </UTooltip>
          </div>
        </template>
        <UTable :rows="agents" :columns="agentColumns" :loading="loading" class="text-sm"
                :empty-state="{ icon: 'i-heroicons-user-group', label: 'Sin actividad de agentes en el período' }">
          <template #rank-data="{ row }">
            <span class="font-bold" :class="row.rank <= 3 ? 'text-amber-500' : 'text-gray-400'">#{{ row.rank }}</span>
          </template>
          <template #agentName-data="{ row }">
            <div>
              <p class="font-medium text-gray-900 dark:text-white">{{ row.agentName }}</p>
              <p class="text-xs text-gray-400">Ext. {{ row.extension }}</p>
            </div>
          </template>
          <template #score-data="{ row }">
            <UBadge :color="row.score >= 75 ? 'green' : row.score >= 50 ? 'amber' : 'red'" variant="soft">{{ row.score }}</UBadge>
          </template>
          <template #answeredCalls-data="{ row }">
            {{ row.answeredCalls }} <span class="text-xs text-gray-400">/ {{ row.totalCalls }}</span>
          </template>
          <template #aht-data="{ row }">{{ fmtSec(row.aht) }}</template>
          <template #avgTalkTime-data="{ row }">{{ fmtSec(row.avgTalkTime) }}</template>
          <template #avgWrapupTime-data="{ row }">{{ fmtSec(row.avgWrapupTime) }}</template>
          <template #loggedTime-data="{ row }">{{ fmtDur(row.loggedTime) }}</template>
          <template #breakTime-data="{ row }">{{ fmtDur(row.breakTime) }}</template>
          <template #occupancy-data="{ row }">
            <span :class="row.occupancy > 90 ? 'text-red-600' : row.occupancy >= 70 ? 'text-green-600' : 'text-amber-600'">{{ row.occupancy }}%</span>
          </template>
          <template #conversionRate-data="{ row }">{{ row.conversionRate }}%</template>
          <template #qualityScore-data="{ row }">
            <span v-if="row.evaluations" :class="toneText(tone(row.qualityScore, 85, 70))">{{ row.qualityScore }}</span>
            <span v-else class="text-gray-300">—</span>
          </template>
        </UTable>
      </UCard>

      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <UCard>
          <template #header><h3 class="font-semibold">Distribución del tiempo conectado</h3></template>
          <div v-if="agents.length" class="space-y-3">
            <div v-for="a in agents.slice(0, 15)" :key="a.agentId">
              <div class="flex justify-between text-xs mb-1">
                <span class="font-medium text-gray-700 dark:text-gray-200">{{ a.agentName }}</span>
                <span class="text-gray-400">{{ fmtDur(a.loggedTime) }}</span>
              </div>
              <div class="flex h-3 rounded overflow-hidden bg-gray-100 dark:bg-gray-800"
                   :title="`Disponible ${fmtDur(a.availableTime)} · En llamada ${fmtDur(a.oncallTime)} · Post-llamada ${fmtDur(a.wrapupTime)} · Pausa ${fmtDur(a.breakTime)}`">
                <div class="bg-green-500" :style="{ width: segPct(a.availableTime, a.loggedTime) }" />
                <div class="bg-sky-500" :style="{ width: segPct(a.oncallTime, a.loggedTime) }" />
                <div class="bg-violet-500" :style="{ width: segPct(a.wrapupTime, a.loggedTime) }" />
                <div class="bg-amber-400" :style="{ width: segPct(a.breakTime, a.loggedTime) }" />
              </div>
            </div>
            <Legend :items="[['bg-green-500', 'Disponible'], ['bg-sky-500', 'En llamada'], ['bg-violet-500', 'Post-llamada'], ['bg-amber-400', 'Pausa']]" />
          </div>
          <Empty v-else />
        </UCard>

        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Pausas por motivo</h3>
              <span v-if="breaks" class="text-xs text-gray-400">{{ breaks.totalBreaks }} pausas · {{ fmtDur(breaks.totalTime) }}</span>
            </div>
          </template>
          <ReportBars color="bg-amber-400" :items="breakItems" empty="Sin pausas en el período" />
        </UCard>
      </div>

      <UCard v-if="breaks && breaks.exceeded.length">
        <template #header>
          <h3 class="font-semibold flex items-center gap-2">
            <UIcon name="i-heroicons-exclamation-triangle" class="w-5 h-5 text-amber-500" />
            Pausas que excedieron el tiempo permitido ({{ breaks.exceededCount }})
          </h3>
        </template>
        <UTable :rows="breaks.exceeded" :columns="exceededColumns">
          <template #start-data="{ row }">{{ fmtDateTime(row.start) }}</template>
          <template #duration-data="{ row }">{{ fmtSec(row.duration) }}</template>
          <template #limit-data="{ row }">{{ fmtSec(row.limit) }}</template>
          <template #excess-data="{ row }"><span class="text-red-600 font-medium">+{{ fmtSec(row.excess) }}</span></template>
        </UTable>
      </UCard>
    </div>

    <!-- ═════════════════ COLAS Y ABANDONO ═════════════════ -->
    <div v-if="tab === 2" class="space-y-6">
      <UCard>
        <template #header><h3 class="font-semibold">Nivel de servicio por cola</h3></template>
        <UTable :rows="queues?.queues || []" :columns="queueColumns" :loading="loading"
                :empty-state="{ icon: 'i-heroicons-queue-list', label: 'Sin llamadas entrantes en el período' }">
          <template #serviceLevel-data="{ row }">
            <span :class="toneText(tone(row.serviceLevel, 80, 60))" class="font-medium">{{ row.serviceLevel }}%</span>
            <span class="text-xs text-gray-400"> ≤{{ row.slaThreshold }}s</span>
          </template>
          <template #abandonRate-data="{ row }"><span :class="toneText(toneInv(row.abandonRate, 5, 10))">{{ row.abandonRate }}%</span></template>
          <template #asa-data="{ row }">{{ fmtSec(row.asa) }}</template>
          <template #maxWait-data="{ row }">{{ fmtSec(row.maxWait) }}</template>
          <template #avgAbandonWait-data="{ row }">{{ fmtSec(row.avgAbandonWait) }}</template>
          <template #aht-data="{ row }">{{ fmtSec(row.aht) }}</template>
        </UTable>
      </UCard>

      <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">Tiempo de espera</h3>
              <Legend :items="[['bg-green-500', 'Atendidas'], ['bg-red-400', 'Abandonadas']]" />
            </div>
          </template>
          <div v-if="queues" class="space-y-3">
            <div v-for="b in queues.waitDistribution" :key="b.label">
              <div class="flex justify-between text-xs mb-1">
                <span class="text-gray-600 dark:text-gray-300">{{ b.label }}</span>
                <span class="text-gray-400">{{ b.answered }} / <span class="text-red-500">{{ b.abandoned }}</span></span>
              </div>
              <div class="flex gap-1">
                <div class="h-2 rounded bg-green-500" :style="{ width: barPct(b.answered, maxWaitBucket, true) }" />
                <div class="h-2 rounded bg-red-400" :style="{ width: barPct(b.abandoned, maxWaitBucket, true) }" />
              </div>
            </div>
            <p class="text-xs text-gray-400 pt-2">Si los abandonos se concentran en un tramo, ahí se pierde la paciencia del cliente: conviene anunciar posición o ofrecer devolución de llamada antes.</p>
          </div>
        </UCard>

        <div class="xl:col-span-2 space-y-4">
          <div v-if="abandoned" class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <ReportKpi label="Llamadas perdidas" :value="n(abandoned.total)" :sub="`${n(abandoned.uniqueNumbers)} números distintos`" />
            <ReportKpi label="Devueltas" :value="n(abandoned.returned)" :tone="tone(abandoned.returnRate, 80, 50)" :sub="`${abandoned.returnRate}% recuperadas`"
                       hint="Hubo una llamada saliente a ese número o una entrante contestada del mismo número después de la pérdida." />
            <ReportKpi label="Sin devolver" :value="n(abandoned.pending)" :tone="abandoned.pending ? 'bad' : 'good'" sub="Oportunidades pendientes" />
            <ReportKpi label="Tiempo de devolución" :value="fmtDur(abandoned.avgReturnDelay)" sub="Promedio" />
          </div>
          <UCard>
            <template #header>
              <div class="flex flex-wrap items-center justify-between gap-2">
                <h3 class="font-semibold">Llamadas perdidas</h3>
                <UCheckbox v-model="onlyPending" label="Solo sin devolver" />
              </div>
            </template>
            <UTable :rows="abandonedRows" :columns="abandonedColumns" :loading="loading"
                    :empty-state="{ icon: 'i-heroicons-check-circle', label: 'Sin llamadas perdidas' }">
              <template #start-data="{ row }">{{ fmtDateTime(row.start) }}</template>
              <template #statusLabel-data="{ row }"><UBadge color="red" variant="soft" size="xs">{{ row.statusLabel }}</UBadge></template>
              <template #waitTime-data="{ row }">{{ fmtSec(row.waitTime) }}</template>
              <template #attempts-data="{ row }">
                <span :class="row.attempts > 1 ? 'text-red-600 font-semibold' : ''">{{ row.attempts }}</span>
              </template>
              <template #returned-data="{ row }">
                <UBadge v-if="row.returned" color="green" variant="soft" size="xs">
                  En {{ fmtDur(row.returnDelay) }}{{ row.returnedBy ? ` · ${row.returnedBy}` : '' }}
                </UBadge>
                <UBadge v-else color="amber" variant="soft" size="xs">Pendiente</UBadge>
              </template>
            </UTable>
          </UCard>
        </div>
      </div>
    </div>

    <!-- ═════════════════ CAMPAÑAS ═════════════════ -->
    <div v-if="tab === 3" class="space-y-6">
      <UCard>
        <template #header><h3 class="font-semibold">KPIs por campaña</h3></template>
        <UTable :rows="campaigns?.rows || []" :columns="campaignColumns" :loading="loading"
                :empty-state="{ icon: 'i-heroicons-megaphone', label: 'Sin campañas con actividad' }">
          <template #campaignName-data="{ row }">
            <p class="font-medium text-gray-900 dark:text-white">{{ row.campaignName }}</p>
            <p class="text-xs text-gray-400">{{ campaignType(row.type) }}{{ row.dialer ? ` · ${row.dialer}` : '' }}</p>
          </template>
          <template #status-data="{ row }">
            <UBadge :color="row.status === 'active' ? 'green' : 'gray'" variant="soft" size="xs">{{ row.status }}</UBadge>
          </template>
          <template #contactRate-data="{ row }">{{ row.contactRate }}%</template>
          <template #conversionRate-data="{ row }">
            <span class="font-medium" :class="row.conversionRate > 0 ? 'text-green-600' : 'text-gray-400'">{{ row.conversionRate }}%</span>
          </template>
          <template #penetration-data="{ row }">
            <div v-if="row.contactsTotal" class="min-w-[110px]">
              <div class="flex justify-between text-xs"><span>{{ row.penetration }}%</span><span class="text-gray-400">{{ n(row.contactsPending) }} pend.</span></div>
              <div class="h-1.5 bg-gray-100 dark:bg-gray-800 rounded mt-1"><div class="h-1.5 bg-sky-500 rounded" :style="{ width: `${row.penetration}%` }" /></div>
            </div>
            <span v-else class="text-gray-300">—</span>
          </template>
          <template #avgTalkTime-data="{ row }">{{ fmtSec(row.avgTalkTime) }}</template>
        </UTable>
      </UCard>

      <div v-if="campaigns" class="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div class="space-y-3">
          <ReportKpi label="Gestiones tipificadas" :value="n(campaigns.dispositions.total)" :sub="`${campaigns.dispositions.typingRate}% de las llamadas atendidas`" />
          <ReportKpi label="Resultados exitosos" :value="n(campaigns.dispositions.success)" tone="good"
                     :sub="`${pctOf(campaigns.dispositions.success, campaigns.dispositions.total)}% de lo tipificado`" />
          <ReportKpi label="Llamadas sin tipificar" :value="n(campaigns.dispositions.untypedCalls)"
                     :tone="campaigns.dispositions.untypedCalls ? 'warn' : 'good'" sub="Atendidas sin disposición" />
        </div>
        <UCard class="xl:col-span-2">
          <template #header><h3 class="font-semibold">Tipificaciones</h3></template>
          <ReportBars :items="dispositionItems" empty="Sin tipificaciones en el período" />
        </UCard>
      </div>
    </div>

    <!-- ═════════════════ OMNICANAL ═════════════════ -->
    <div v-if="tab === 4" class="space-y-6">
      <template v-if="omni">
        <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <ReportKpi label="Conversaciones" :value="n(omni.totals.total)" :sub="`${n(omni.totals.open)} abiertas`" />
          <ReportKpi label="Sin asignar" :value="n(omni.totals.unassigned)" :tone="omni.totals.unassigned ? 'warn' : 'good'" sub="Abiertas sin agente" />
          <ReportKpi label="1ª respuesta" :value="fmtSec(omni.totals.avgFirstResponse)" sub="Promedio"
                     hint="Tiempo desde que inicia la conversación hasta la primera respuesta del agente." />
          <ReportKpi :label="`1ª resp. ≤ ${omni.frtTarget / 60} min`" :value="`${omni.totals.frtWithinTarget}%`"
                     :tone="tone(omni.totals.frtWithinTarget, 80, 60)" sub="Nivel de servicio chat" />
          <ReportKpi label="Resolución" :value="fmtDur(omni.totals.avgResolution)" :sub="`${omni.totals.resolutionRate}% cerradas`" />
          <ReportKpi label="Mensajes" :value="n(omni.totals.inboundMessages + omni.totals.outboundMessages)"
                     :sub="`${n(omni.totals.inboundMessages)} recibidos · ${n(omni.totals.outboundMessages)} enviados`" />
        </div>

        <UCard>
          <template #header><h3 class="font-semibold">Por canal</h3></template>
          <UTable :rows="omni.byChannel" :columns="omniColumns" :empty-state="{ icon: 'i-heroicons-chat-bubble-left-right', label: 'Sin conversaciones en el período' }">
            <template #avgFirstResponse-data="{ row }">{{ fmtSec(row.avgFirstResponse) }}</template>
            <template #frtWithinTarget-data="{ row }"><span :class="toneText(tone(row.frtWithinTarget, 80, 60))">{{ row.frtWithinTarget }}%</span></template>
            <template #avgResolution-data="{ row }">{{ fmtDur(row.avgResolution) }}</template>
            <template #resolutionRate-data="{ row }">{{ row.resolutionRate }}%</template>
          </UTable>
        </UCard>

        <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <UCard>
            <template #header><h3 class="font-semibold">Conversaciones por agente</h3></template>
            <UTable :rows="omni.byAgent" :columns="omniAgentColumns" :empty-state="{ icon: 'i-heroicons-user', label: 'Sin datos' }">
              <template #avgFirstResponse-data="{ row }">{{ fmtSec(row.avgFirstResponse) }}</template>
              <template #avgResolution-data="{ row }">{{ fmtDur(row.avgResolution) }}</template>
            </UTable>
          </UCard>
          <UCard>
            <template #header><h3 class="font-semibold">Conversaciones por hora</h3></template>
            <div class="flex items-end gap-0.5 h-40">
              <div v-for="h in omni.hourly" :key="h.hour" class="flex-1 flex flex-col justify-end h-full" :title="`${h.label}: ${h.total}`">
                <div class="w-full bg-teal-500 rounded-t" :style="{ height: barPct(h.total, maxOmniHourly) }" />
              </div>
            </div>
            <div class="flex gap-0.5 mt-1">
              <span v-for="h in omni.hourly" :key="h.hour" class="flex-1 text-center text-[9px] text-gray-400">{{ h.hour % 3 === 0 ? h.hour : '' }}</span>
            </div>
          </UCard>
        </div>
      </template>
      <Skeleton v-else-if="loading" />
    </div>

    <!-- ═════════════════ CALIDAD ═════════════════ -->
    <div v-if="tab === 5" class="space-y-6">
      <template v-if="quality">
        <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <ReportKpi label="Evaluaciones" :value="n(quality.evaluations)" />
          <ReportKpi label="Puntaje promedio" :value="quality.avgScore" :tone="tone(quality.avgScore, 85, 70)" sub="Sobre 100" />
          <ReportKpi label="Mínimo / máximo" :value="`${quality.minScore} / ${quality.maxScore}`" />
          <ReportKpi label="Cobertura" :value="`${quality.coverage}%`" :sub="`${n(quality.recordedCalls)} llamadas grabadas`"
                     hint="Evaluaciones ÷ llamadas grabadas del período. Meta típica: 2–5% de las llamadas." />
          <ReportKpi label="Con feedback" :value="`${quality.feedbackRate}%`" sub="Retroalimentación enviada" />
          <ReportKpi label="Bajo 60" :value="n(quality.distribution[0].count)" :tone="quality.distribution[0].count ? 'bad' : 'good'" sub="Requieren plan de mejora" />
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <UCard>
            <template #header><h3 class="font-semibold">Distribución de puntajes</h3></template>
            <ReportBars :items="qualityItems" />
            <div class="mt-6">
              <p class="text-sm font-medium mb-2">Por evaluador</p>
              <ReportBars :items="evaluatorItems" color="bg-gray-400" />
            </div>
          </UCard>
          <UCard class="xl:col-span-2">
            <template #header><h3 class="font-semibold">Calidad por agente</h3></template>
            <UTable :rows="quality.byAgent" :columns="qualityColumns" :empty-state="{ icon: 'i-heroicons-star', label: 'Sin evaluaciones en el período' }">
              <template #avgScore-data="{ row }">
                <div class="flex items-center gap-2 min-w-[140px]">
                  <div class="flex-1 h-2 bg-gray-100 dark:bg-gray-800 rounded">
                    <div class="h-2 rounded" :class="row.avgScore >= 85 ? 'bg-green-500' : row.avgScore >= 70 ? 'bg-amber-400' : 'bg-red-500'" :style="{ width: `${Math.min(100, row.avgScore)}%` }" />
                  </div>
                  <span class="font-medium w-10 text-right">{{ row.avgScore }}</span>
                </div>
              </template>
              <template #belowTarget-data="{ row }"><span :class="row.belowTarget ? 'text-red-600' : 'text-gray-400'">{{ row.belowTarget }}</span></template>
            </UTable>
          </UCard>
        </div>
      </template>
      <Skeleton v-else-if="loading" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, defineComponent, type PropType } from 'vue'

definePageMeta({ middleware: ['auth'] })
useHead({ title: 'Reportes y KPIs' })

const http = useHttp()
const toast = useToast()

// ─── Componentes locales pequeños ───────────────────────────────────────────
const Legend = defineComponent({
  props: { items: { type: Array as PropType<string[][]>, required: true } },
  setup: (p) => () => h('div', { class: 'flex flex-wrap items-center gap-3' }, p.items.map(([c, l]) =>
    h('span', { class: 'inline-flex items-center gap-1 text-xs text-gray-500' }, [h('span', { class: `w-2.5 h-2.5 rounded-sm ${c}` }), l]))),
})
const Empty = defineComponent({
  setup: () => () => h('p', { class: 'py-10 text-center text-sm text-gray-400' }, 'Sin datos para el período seleccionado'),
})
const Skeleton = defineComponent({
  setup: () => () => h('div', { class: 'grid grid-cols-2 md:grid-cols-6 gap-3', 'aria-busy': 'true', 'aria-label': 'Cargando' },
    Array.from({ length: 12 }, (_, i) => h('div', { key: i, class: 'h-24 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse' }))),
})

// ─── Filtros y pestañas ─────────────────────────────────────────────────────
const tabs = [
  { label: 'Resumen', icon: 'i-heroicons-chart-pie' },
  { label: 'Agentes', icon: 'i-heroicons-user-group' },
  { label: 'Colas y abandono', icon: 'i-heroicons-queue-list' },
  { label: 'Campañas', icon: 'i-heroicons-megaphone' },
  { label: 'Omnicanal', icon: 'i-heroicons-chat-bubble-left-right' },
  { label: 'Calidad', icon: 'i-heroicons-star' },
]
const tab = ref(0)

const periodOptions = [
  { label: 'Hoy', value: 'today' },
  { label: 'Ayer', value: 'yesterday' },
  { label: 'Esta semana', value: 'thisweek' },
  { label: 'Semana pasada', value: 'lastweek' },
  { label: 'Últimos 7 días', value: 'last7days' },
  { label: 'Últimos 30 días', value: 'last30days' },
  { label: 'Este mes', value: 'thismonth' },
  { label: 'Mes pasado', value: 'lastmonth' },
  { label: 'Personalizado', value: 'custom' },
]
const directionOptions = [
  { label: 'Todas', value: '' },
  { label: 'Entrantes', value: 'inbound' },
  { label: 'Salientes', value: 'outbound' },
]
const filters = reactive({
  period: 'today', startDate: '', endDate: '', campaign: '', queue: '', agent: '', direction: '', sla: 20,
})
const catalogs = reactive({ campaigns: [] as any[], queues: [] as any[], agents: [] as any[] })

// ─── Datos ──────────────────────────────────────────────────────────────────
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const period = ref<{ start: string; end: string } | null>(null)
const summary = ref<any>(null)
const agents = ref<any[]>([])
const breaks = ref<any>(null)
const queues = ref<any>(null)
const abandoned = ref<any>(null)
const campaigns = ref<any>(null)
const omni = ref<any>(null)
const quality = ref<any>(null)
const onlyPending = ref(false)
const loadedKey = reactive<Record<number, string>>({})

const cur = computed(() => summary.value?.current || {})
const prev = computed(() => summary.value?.previous || {})

const query = () => {
  const q: Record<string, any> = { period: filters.period, sla: filters.sla || 20 }
  if (filters.period === 'custom') {
    if (filters.startDate) q.start_date = filters.startDate
    if (filters.endDate) q.end_date = filters.endDate
  }
  for (const k of ['campaign', 'queue', 'agent', 'direction'] as const) if (filters[k]) q[k] = filters[k]
  return q
}
const filterKey = () => JSON.stringify(query())

async function loadTab(index: number, force = false) {
  const key = filterKey()
  if (!force && loadedKey[index] === key) return
  loading.value = true
  error.value = ''
  const q = query()
  try {
    if (index === 0) {
      const data: any = await http.get('/reports/analytics/summary/', q)
      summary.value = data
      period.value = data.period
    } else if (index === 1) {
      const [a, b]: any[] = await Promise.all([
        http.get('/reports/analytics/agents/', q), http.get('/reports/analytics/breaks/', q),
      ])
      agents.value = a.rows || []
      breaks.value = b
      period.value = a.period
    } else if (index === 2) {
      const [a, b]: any[] = await Promise.all([
        http.get('/reports/analytics/queues/', q), http.get('/reports/analytics/abandoned/', q),
      ])
      queues.value = a
      abandoned.value = b
      period.value = a.period
    } else if (index === 3) {
      campaigns.value = await http.get('/reports/analytics/campaigns/', q)
      period.value = campaigns.value.period
    } else if (index === 4) {
      omni.value = await http.get('/reports/analytics/omnichannel/', q)
      period.value = omni.value.period
    } else if (index === 5) {
      quality.value = await http.get('/reports/analytics/quality/', q)
      period.value = quality.value.period
    }
    loadedKey[index] = key
  } catch (e: any) {
    error.value = http.errorMessage(e, 'No se pudieron cargar los reportes')
  } finally {
    loading.value = false
  }
}

function reload() {
  if (filters.period === 'custom' && (!filters.startDate || !filters.endDate)) {
    toast.add({ title: 'Selecciona las fechas desde y hasta', color: 'orange' })
    return
  }
  loadTab(tab.value, true)
}

watch(tab, (i) => loadTab(i))

async function loadCatalogs() {
  const [camps, qs, ags] = await Promise.allSettled([
    http.get('/campaigns/', { page_size: 200 }),
    http.get('/queues/', { page_size: 200 }),
    http.get('/agents/', { page_size: 500 }),
  ])
  if (camps.status === 'fulfilled') catalogs.campaigns = http.results(camps.value).map((c: any) => ({ label: c.name, value: String(c.id) }))
  if (qs.status === 'fulfilled') catalogs.queues = http.results(qs.value).map((q: any) => ({ label: q.name, value: String(q.id) }))
  if (ags.status === 'fulfilled') catalogs.agents = http.results(ags.value).map((a: any) => ({
    label: `${a.user_details?.name || a.user_details?.first_name || a.agent_id}${a.sip_extension ? ` (${a.sip_extension})` : ''}`,
    value: String(a.id),
  }))
}

onMounted(() => {
  loadCatalogs()
  loadTab(0)
})

// ─── Exportación ────────────────────────────────────────────────────────────
const TAB_DATASETS: Record<number, [string, string][]> = {
  0: [['daily', 'Resumen diario'], ['hourly', 'Llamadas por hora'], ['calls', 'Detalle de llamadas']],
  1: [['agent_kpis', 'KPIs y ranking de agentes'], ['breaks', 'Pausas por agente y motivo'], ['agents', 'Llamadas por agente']],
  2: [['queue_sla', 'Nivel de servicio por cola'], ['abandoned', 'Llamadas perdidas y devoluciones']],
  3: [['campaign_kpis', 'KPIs de campañas'], ['dispositions', 'Tipificaciones']],
  4: [['omnichannel', 'Omnicanal por canal'], ['chats', 'Detalle de conversaciones']],
  5: [['quality', 'Calidad por agente']],
}
const exportItems = computed(() => [
  (TAB_DATASETS[tab.value] || []).map(([dataset, label]) => ({
    label: `${label} (Excel)`, icon: 'i-heroicons-table-cells', click: () => doExport(dataset, 'xlsx'),
  })),
  (TAB_DATASETS[tab.value] || []).slice(0, 1).map(([dataset, label]) => ({
    label: `${label} (CSV)`, icon: 'i-heroicons-document-text', click: () => doExport(dataset, 'csv'),
  })),
])
async function doExport(dataset: string, format: 'xlsx' | 'csv') {
  exporting.value = true
  try {
    await http.download('/reports/export/', { ...query(), dataset, format }, `${dataset}.${format}`)
  } catch (e: any) {
    toast.add({ title: 'No se pudo exportar', description: await http.blobErrorMessage(e), color: 'red' })
  } finally {
    exporting.value = false
  }
}

// ─── Columnas ───────────────────────────────────────────────────────────────
const dailyColumns = [
  { key: 'date', label: 'Fecha' }, { key: 'total', label: 'Total' }, { key: 'inbound', label: 'Entrantes' },
  { key: 'outbound', label: 'Salientes' }, { key: 'answered', label: 'Atendidas' }, { key: 'abandoned', label: 'Abandonadas' },
  { key: 'serviceLevel', label: 'SL' }, { key: 'abandonRate', label: '% abandono' }, { key: 'asa', label: 'ASA' }, { key: 'aht', label: 'AHT' },
]
const agentColumns = [
  { key: 'rank', label: '#', sortable: true }, { key: 'agentName', label: 'Agente', sortable: true },
  { key: 'score', label: 'Puntaje', sortable: true }, { key: 'answeredCalls', label: 'Atendidas', sortable: true },
  { key: 'chats', label: 'Chats', sortable: true }, { key: 'aht', label: 'AHT', sortable: true },
  { key: 'avgTalkTime', label: 'Conv. prom.', sortable: true }, { key: 'avgWrapupTime', label: 'ACW', sortable: true },
  { key: 'callsPerHour', label: 'Llam./h', sortable: true }, { key: 'loggedTime', label: 'Conectado', sortable: true },
  { key: 'breakTime', label: 'Pausas', sortable: true }, { key: 'occupancy', label: 'Ocupación', sortable: true },
  { key: 'transferRate', label: '% transf.', sortable: true }, { key: 'conversionRate', label: 'Conversión', sortable: true },
  { key: 'qualityScore', label: 'Calidad', sortable: true },
]
const exceededColumns = [
  { key: 'start', label: 'Inicio' }, { key: 'agentName', label: 'Agente' }, { key: 'reason', label: 'Motivo' },
  { key: 'duration', label: 'Duración' }, { key: 'limit', label: 'Permitido' }, { key: 'excess', label: 'Exceso' },
]
const queueColumns = [
  { key: 'queueName', label: 'Cola', sortable: true }, { key: 'offered', label: 'Ofrecidas', sortable: true },
  { key: 'answered', label: 'Atendidas', sortable: true }, { key: 'abandoned', label: 'Abandonadas', sortable: true },
  { key: 'serviceLevel', label: 'Nivel de servicio', sortable: true }, { key: 'abandonRate', label: '% abandono', sortable: true },
  { key: 'asa', label: 'ASA', sortable: true }, { key: 'maxWait', label: 'Espera máx.', sortable: true },
  { key: 'avgAbandonWait', label: 'Espera al abandonar' }, { key: 'aht', label: 'AHT', sortable: true },
]
const abandonedColumns = [
  { key: 'start', label: 'Fecha' }, { key: 'caller', label: 'Número' }, { key: 'queue', label: 'Cola' },
  { key: 'statusLabel', label: 'Estado' }, { key: 'waitTime', label: 'Espera' }, { key: 'attempts', label: 'Intentos' },
  { key: 'returned', label: 'Devolución' },
]
const campaignColumns = [
  { key: 'campaignName', label: 'Campaña', sortable: true }, { key: 'status', label: 'Estado' },
  { key: 'calls', label: 'Llamadas', sortable: true }, { key: 'answered', label: 'Contactadas', sortable: true },
  { key: 'contactRate', label: 'Contactab.', sortable: true }, { key: 'machine', label: 'Contestador', sortable: true },
  { key: 'success', label: 'Éxitos', sortable: true }, { key: 'conversionRate', label: 'Conversión', sortable: true },
  { key: 'callbacks', label: 'Rellamadas' }, { key: 'chats', label: 'Chats', sortable: true },
  { key: 'penetration', label: 'Barrido de base' }, { key: 'avgAttempts', label: 'Intentos prom.' },
  { key: 'avgTalkTime', label: 'Conv. prom.' },
]
const omniColumns = [
  { key: 'label', label: 'Canal' }, { key: 'total', label: 'Conversaciones', sortable: true },
  { key: 'closed', label: 'Cerradas' }, { key: 'unassigned', label: 'Sin asignar' },
  { key: 'responseRate', label: '% respondidas' }, { key: 'avgFirstResponse', label: '1ª respuesta' },
  { key: 'frtWithinTarget', label: 'En meta' }, { key: 'avgResolution', label: 'Resolución' },
  { key: 'resolutionRate', label: '% cerradas' }, { key: 'inboundMessages', label: 'Msj. recibidos' },
  { key: 'outboundMessages', label: 'Msj. enviados' },
]
const omniAgentColumns = [
  { key: 'agentName', label: 'Agente' }, { key: 'total', label: 'Conversaciones', sortable: true },
  { key: 'closed', label: 'Cerradas' }, { key: 'avgFirstResponse', label: '1ª respuesta' }, { key: 'avgResolution', label: 'Resolución' },
]
const qualityColumns = [
  { key: 'agentName', label: 'Agente', sortable: true }, { key: 'evaluations', label: 'Evaluaciones', sortable: true },
  { key: 'avgScore', label: 'Promedio', sortable: true }, { key: 'minScore', label: 'Mín.' },
  { key: 'maxScore', label: 'Máx.' }, { key: 'belowTarget', label: 'Bajo 60' },
]

// ─── Derivados para gráficos ────────────────────────────────────────────────
const maxDaily = computed(() => Math.max(1, ...(summary.value?.daily || []).map((d: any) => d.total)))
const maxHourly = computed(() => Math.max(1, ...(summary.value?.hourly || []).map((d: any) => d.total)))
const maxOmniHourly = computed(() => Math.max(1, ...(omni.value?.hourly || []).map((d: any) => d.total)))
const maxWaitBucket = computed(() => Math.max(1, ...(queues.value?.waitDistribution || []).map((b: any) => Math.max(b.answered, b.abandoned))))
const abandonedRows = computed(() => (abandoned.value?.rows || []).filter((r: any) => !onlyPending.value || !r.returned))

// Items para ReportBars
const statusItems = computed(() => (summary.value?.byStatus || []).map((s: any) => ({
  label: s.label, value: s.count, sub: `${pctOf(s.count, cur.value.totalCalls)}%`, color: statusBar(s.status),
})))
const talkItems = computed(() => (summary.value?.talkDistribution || []).map((t: any) => ({
  label: t.label, value: t.count, sub: `${pctOf(t.count, cur.value.answeredCalls)}%`,
})))
const breakItems = computed(() => (breaks.value?.byReason || []).map((r: any) => ({
  label: r.reason, value: r.total, display: fmtDur(r.total),
  sub: `${r.count} · prom. ${fmtSec(r.avg)}${r.exceeded ? ` · ${r.exceeded} excedidas` : ''}`,
})))
const dispositionItems = computed(() => (campaigns.value?.dispositions?.rows || []).map((d: any) => ({
  label: d.campaign ? `${d.name} · ${d.campaign}` : d.name,
  value: d.total,
  sub: `${d.share}%${d.chats ? ` · ${d.chats} chats` : ''}`,
  color: d.isSuccess ? 'bg-green-500' : 'bg-sky-500',
})))
const QUALITY_COLORS = ['bg-red-500', 'bg-amber-400', 'bg-sky-500', 'bg-green-500']
const qualityItems = computed(() => (quality.value?.distribution || []).map((d: any, i: number) => ({
  label: d.label, value: d.count, color: QUALITY_COLORS[i],
})))
const evaluatorItems = computed(() => (quality.value?.byEvaluator || []).map((e: any) => ({
  label: e.evaluator, value: e.evaluations, sub: `prom. ${e.avgScore}`,
})))

// ─── Formato ────────────────────────────────────────────────────────────────
const n = (v: number) => (v || 0).toLocaleString('es-CO')
const pctOf = (a: number, b: number) => (b ? Math.round((a / b) * 1000) / 10 : 0)
const fmtSec = (s: number) => {
  if (!s || s < 0) return '0:00'
  const total = Math.round(s)
  const hh = Math.floor(total / 3600)
  const mm = Math.floor((total % 3600) / 60)
  const ss = total % 60
  return hh ? `${hh}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${mm}:${String(ss).padStart(2, '0')}`
}
const fmtDur = (s: number) => {
  if (!s || s < 0) return '0 m'
  const hh = Math.floor(s / 3600)
  const mm = Math.round((s % 3600) / 60)
  return hh ? `${hh} h ${mm} m` : `${mm} m`
}
const fmtDate = (d: string) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' }) : '')
const shortDate = (d: string) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'numeric' }) : '')
const fmtDateTime = (d: string) => (d ? new Date(d).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '')
const periodText = computed(() => {
  if (!period.value) return 'Análisis y estadísticas del contact center'
  const s = new Date(period.value.start)
  const e = new Date(period.value.end)
  const f = (d: Date) => d.toLocaleString('es-CO', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  return `${f(s)} → ${f(e)}`
})

const barPct = (v: number, max: number, min = false) => (v > 0 ? `${Math.max(min ? 2 : 3, (v / max) * 100)}%` : '0%')
const segPct = (v: number, total: number) => (total > 0 ? `${(v / total) * 100}%` : '0%')
const tone = (v: number, good: number, warn: number) => (v >= good ? 'good' : v >= warn ? 'warn' : 'bad')
const toneInv = (v: number, good: number, warn: number) => (v <= good ? 'good' : v <= warn ? 'warn' : 'bad')
const toneText = (t: string) => ({ good: 'text-green-600', warn: 'text-amber-600', bad: 'text-red-600' } as Record<string, string>)[t] || ''
const heatStyle = (v: number) => {
  const max = summary.value?.heatmap?.max || 1
  if (!v) return { backgroundColor: 'rgba(148, 163, 184, 0.12)' }
  return { backgroundColor: `rgba(14, 165, 233, ${0.15 + (v / max) * 0.85})` }
}
const statusBar = (s: string) => ({
  completed: 'bg-green-500', abandoned: 'bg-red-500', no_answer: 'bg-amber-400', busy: 'bg-orange-400',
  cancelled: 'bg-gray-400', failed: 'bg-red-300', voicemail: 'bg-violet-500', machine: 'bg-purple-400',
} as Record<string, string>)[s] || 'bg-sky-500'
const campaignType = (t: string) => ({ inbound: 'Entrante', outbound: 'Saliente', blended: 'Mixta', preview: 'Preview' } as Record<string, string>)[t] || t
</script>

<style scoped>
.section-title {
  @apply text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3;
}
</style>
