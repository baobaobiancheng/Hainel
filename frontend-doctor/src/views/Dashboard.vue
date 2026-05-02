<template>
  <div class="page-wrap dashboard-page">
    <div class="page-header">
      <div>
        <div class="section-label">DOCTOR OPERATIONS</div>
        <h1 class="page-title-text">医生 <span>工作总览</span></h1>
      </div>
      <div class="header-actions">
        <div class="range-switch">
          <button
            v-for="item in rangeOptions"
            :key="item.value"
            class="range-btn"
            :class="{ active: selectedRange === item.value }"
            @click="changeRange(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div class="stats-grid">
        <div class="stat-card accent-cyan">
          <div class="stat-label">今日会话</div>
          <div class="stat-value mono">{{ overview?.kpis?.today_consultations ?? 0 }}</div>
          <div class="stat-foot">当天新增接诊会话</div>
        </div>
        <div class="stat-card accent-blue">
          <div class="stat-label">进行中会话</div>
          <div class="stat-value mono">{{ overview?.kpis?.active_conversations ?? 0 }}</div>
          <div class="stat-foot">当前仍需持续跟进</div>
        </div>
        <div class="stat-card accent-red">
          <div class="stat-label">高风险分诊</div>
          <div class="stat-value mono">{{ overview?.kpis?.urgent_triage_count ?? 0 }}</div>
          <div class="stat-foot">优先处理高危患者</div>
        </div>
        <div class="stat-card accent-amber">
          <div class="stat-label">待医生确认病历</div>
          <div class="stat-value mono">{{ overview?.kpis?.pending_confirmation_records ?? 0 }}</div>
          <div class="stat-foot">AI 草稿待补充与确认</div>
        </div>
        <div class="stat-card accent-violet">
          <div class="stat-label">已确认病历</div>
          <div class="stat-value mono">{{ overview?.kpis?.confirmed_records ?? 0 }}</div>
          <div class="stat-foot">医生已确认，可直接归档</div>
        </div>
      </div>

      <div v-if="loadError" class="glass-card empty-panel">{{ loadError }}</div>

      <template v-else>
        <div class="chart-grid">
          <div class="glass-card chart-panel wide">
            <div class="panel-head">
              <span class="panel-label">会话趋势</span>
            </div>
            <div ref="consultationTrendRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-panel">
            <div class="panel-head">
              <span class="panel-label">紧急程度分布</span>
            </div>
            <div ref="triageDistRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-panel">
            <div class="panel-head">
              <span class="panel-label">分诊科室分布</span>
            </div>
            <div ref="departmentDistRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-panel">
            <div class="panel-head">
              <span class="panel-label">病历状态分布</span>
            </div>
            <div ref="recordStatusRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-panel">
            <div class="panel-head">
              <span class="panel-label">报告上传趋势</span>
            </div>
            <div ref="reportTrendRef" class="chart-box"></div>
          </div>

          <div class="glass-card queue-panel">
            <div class="panel-head">
              <span class="panel-label">待处理队列</span>
              <span class="panel-hint">{{ queueItems.length }} 项</span>
            </div>
            <div v-if="queueItems.length" class="queue-list">
              <button
                v-for="item in queueItems"
                :key="`${item.type}-${item.id}`"
                class="queue-item"
                @click="openQueueItem(item)"
              >
                <div class="queue-main">
                  <div class="queue-title">{{ item.title }}</div>
                  <div class="queue-sub">{{ item.subtitle || '待补充信息' }}</div>
                </div>
                <div class="queue-meta">
                  <span class="queue-priority" :class="`priority-${item.priority}`">{{ priorityLabel(item.priority) }}</span>
                  <span class="queue-status">{{ item.status }}</span>
                </div>
              </button>
            </div>
            <div v-else class="empty-queue">当前没有待处理积压。</div>
          </div>
        </div>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getDashboardOverview } from '../api/doctors'

const router = useRouter()

const loading = ref(false)
const loadError = ref('')
const selectedRange = ref('7d')
const overview = ref(null)

const consultationTrendRef = ref(null)
const triageDistRef = ref(null)
const departmentDistRef = ref(null)
const recordStatusRef = ref(null)
const reportTrendRef = ref(null)

const chartInstances = new Map()

const rangeOptions = [
  { value: '7d', label: '7 天' },
  { value: '30d', label: '30 天' },
  { value: '90d', label: '90 天' }
]

const queueItems = computed(() => overview.value?.doctor_queue || [])

onMounted(async () => {
  await loadOverview()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  destroyCharts()
})

watch(overview, async () => {
  await nextTick()
  renderCharts()
})

const changeRange = async (range) => {
  if (selectedRange.value === range) return
  selectedRange.value = range
  await loadOverview()
}

const loadOverview = async () => {
  loading.value = true
  loadError.value = ''
  try {
    overview.value = await getDashboardOverview(selectedRange.value)
  } catch (error) {
    overview.value = null
    loadError.value = '工作总览加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

const ensureChart = (key, el) => {
  if (!el) return null
  if (chartInstances.has(key)) return chartInstances.get(key)
  const instance = echarts.init(el)
  chartInstances.set(key, instance)
  return instance
}

const destroyCharts = () => {
  chartInstances.forEach((instance) => instance.dispose())
  chartInstances.clear()
}

const resizeCharts = () => {
  chartInstances.forEach((instance) => instance.resize())
}

const renderCharts = () => {
  renderConsultationTrend()
  renderPieChart(
    'triage',
    triageDistRef.value,
    overview.value?.triage_distribution || [],
    ['#38bdf8', '#f59e0b', '#fb7185', '#8b5cf6', '#14b8a6']
  )
  renderPieChart(
    'department',
    departmentDistRef.value,
    overview.value?.department_distribution || [],
    ['#22d3ee', '#34d399', '#f59e0b', '#60a5fa', '#f472b6', '#a78bfa']
  )
  renderBarChart(
    'records',
    recordStatusRef.value,
    overview.value?.record_status_distribution || [],
    '#60a5fa'
  )
  renderReportTrend()
}

const renderConsultationTrend = () => {
  const chart = ensureChart('consultationTrend', consultationTrendRef.value)
  if (!chart) return
  const trend = overview.value?.consultation_trend || []
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: 'category',
      data: trend.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: 'rgba(148,163,184,0.25)' } },
      axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } },
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8' }
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbolSize: 8,
        data: trend.map((item) => item.value),
        lineStyle: { color: '#22d3ee', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(34,211,238,0.35)' },
            { offset: 1, color: 'rgba(34,211,238,0.02)' }
          ])
        },
        itemStyle: { color: '#67e8f9' }
      }
    ]
  })
}

const renderPieChart = (key, el, rows, colors) => {
  const chart = ensureChart(key, el)
  if (!chart) return
  chart.setOption({
    backgroundColor: 'transparent',
    color: colors,
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 0,
      textStyle: { color: '#94a3b8', fontSize: 11 }
    },
    series: [
      {
        type: 'pie',
        radius: ['42%', '70%'],
        center: ['50%', '42%'],
        label: { color: '#cbd5e1', fontSize: 11 },
        data: rows.map((item) => ({
          value: item.value,
          name: labelize(item.label)
        }))
      }
    ]
  })
}

const renderBarChart = (key, el, rows, color) => {
  const chart = ensureChart(key, el)
  if (!chart) return
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: 'category',
      data: rows.map((item) => labelize(item.label)),
      axisLine: { lineStyle: { color: 'rgba(148,163,184,0.25)' } },
      axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } },
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8' }
    },
    series: [
      {
        type: 'bar',
        barWidth: 24,
        itemStyle: {
          color,
          borderRadius: [8, 8, 0, 0]
        },
        data: rows.map((item) => item.value)
      }
    ]
  })
}

const renderReportTrend = () => {
  const chart = ensureChart('reportTrend', reportTrendRef.value)
  if (!chart) return
  const trend = overview.value?.report_upload_trend || []
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: 'category',
      data: trend.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: 'rgba(148,163,184,0.25)' } },
      axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } },
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8' }
    },
    series: [
      {
        type: 'bar',
        barWidth: 18,
        data: trend.map((item) => item.value),
        itemStyle: {
          color: '#34d399',
          borderRadius: [6, 6, 0, 0]
        }
      }
    ]
  })
}

const priorityLabel = (priority) => ({
  urgent: '紧急',
  high: '高优先',
  medium: '已确认',
  normal: '待确认'
}[priority] || priority)

const labelize = (label) => ({
  draft: '草稿',
  confirmed: '已确认',
  reviewed: '已审核（历史）',
  archived: '已归档',
  low: '低风险',
  normal: '常规',
  medium: '中风险',
  high: '高风险',
  urgent: '紧急'
}[label] || label)

const openQueueItem = (item) => {
  if (item.type === 'conversation' && item.conversation_id) {
    router.push({ path: '/diagnosis', query: { conversation_id: String(item.conversation_id) } })
    return
  }
  if (item.type === 'record') {
    const query = { id: String(item.id) }
    if (item.conversation_id) query.conversation_id = String(item.conversation_id)
    router.push({ path: '/records', query })
  }
}
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
}

.range-switch {
  display: inline-flex;
  padding: 4px;
  border-radius: 999px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
  gap: 4px;
}

.range-btn {
  height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--c-text-sec);
  cursor: pointer;
  font-family: var(--f-body);
}

.range-btn.active {
  color: #081321;
  background: linear-gradient(135deg, #38bdf8, #67e8f9);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  position: relative;
  overflow: hidden;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid var(--c-border-subtle);
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.12), transparent 45%);
}

.stat-card::after {
  content: '';
  position: absolute;
  inset: auto 0 0 0;
  height: 3px;
  background: currentColor;
  opacity: 0.75;
}

.accent-cyan { color: #22d3ee; }
.accent-blue { color: #60a5fa; }
.accent-red { color: #fb7185; }
.accent-amber { color: #f59e0b; }
.accent-violet { color: #a78bfa; }

.stat-label {
  color: var(--c-text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stat-value {
  margin-top: 12px;
  font-size: 34px;
  font-weight: 700;
  color: var(--c-text);
}

.stat-foot {
  margin-top: 10px;
  color: var(--c-text-sec);
  font-size: 12px;
}

.empty-panel {
  padding: 28px;
  color: var(--c-text-muted);
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.chart-panel,
.queue-panel {
  overflow: hidden;
}

.chart-panel.wide {
  grid-column: span 2;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--c-border-subtle);
}

.panel-label {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-text-sec);
}

.panel-hint {
  color: var(--c-text-muted);
  font-size: 12px;
}

.chart-box {
  height: 290px;
}

.queue-list {
  display: grid;
  gap: 10px;
  padding: 16px;
}

.queue-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--transition), background var(--transition);
}

.queue-item:hover {
  border-color: var(--c-primary-border);
  background: rgba(34, 211, 238, 0.04);
}

.queue-title {
  color: var(--c-text);
  font-weight: 700;
  font-size: 13px;
}

.queue-sub {
  margin-top: 6px;
  color: var(--c-text-sec);
  font-size: 12px;
}

.queue-meta {
  display: grid;
  justify-items: end;
  gap: 8px;
}

.queue-priority,
.queue-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  border: 1px solid var(--c-border-subtle);
}

.priority-urgent,
.priority-high {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.26);
  background: rgba(248, 113, 113, 0.12);
}

.priority-medium {
  color: #fde68a;
  border-color: rgba(245, 158, 11, 0.24);
  background: rgba(245, 158, 11, 0.12);
}

.priority-normal {
  color: #bae6fd;
  border-color: rgba(56, 189, 248, 0.24);
  background: rgba(56, 189, 248, 0.12);
}

.queue-status {
  color: var(--c-text-sec);
}

.empty-queue {
  padding: 30px 18px;
  color: var(--c-text-muted);
}

@media (max-width: 1360px) {
  .stats-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chart-panel.wide {
    grid-column: span 2;
  }
}

@media (max-width: 900px) {
  .stats-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-panel.wide {
    grid-column: span 1;
  }
}
</style>
