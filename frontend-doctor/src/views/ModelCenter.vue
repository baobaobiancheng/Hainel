<template>
  <div class="page-wrap model-center-page">
    <div class="page-header">
      <div>
        <div class="section-label">MODEL OPERATIONS</div>
        <h1 class="page-title-text">模型中心 <span>配置、连通性与 Token 监控</span></h1>
      </div>
      <div class="header-actions">
        <a-range-picker v-model:value="dateRange" value-format="YYYY-MM-DD" @change="handleDateRangeChange" />
        <a-button :loading="loading.metrics" @click="loadTokenUsage">刷新图表</a-button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card accent-cyan">
        <div class="stat-label">请求总数</div>
        <div class="stat-value mono">{{ tokenSummary.request_count ?? 0 }}</div>
        <div class="stat-foot">当前筛选时间范围内的模型调用次数</div>
      </div>
      <div class="stat-card accent-blue">
        <div class="stat-label">总 Token</div>
        <div class="stat-value mono">{{ formatInt(tokenSummary.total_tokens) }}</div>
        <div class="stat-foot">Prompt 与 Completion 总和</div>
      </div>
      <div class="stat-card accent-amber">
        <div class="stat-label">Prompt Token</div>
        <div class="stat-value mono">{{ formatInt(tokenSummary.prompt_tokens) }}</div>
        <div class="stat-foot">输入侧消耗</div>
      </div>
      <div class="stat-card accent-violet">
        <div class="stat-label">最近调用</div>
        <div class="stat-value compact mono">{{ tokenSummary.last_called_at || '--' }}</div>
        <div class="stat-foot">最后一次采集时间</div>
      </div>
    </div>

    <div class="panel-grid two-col">
      <div class="glass-card panel-card">
        <div class="panel-head">
          <span class="panel-label">模型配置</span>
          <a-tag color="blue">运行时热更新</a-tag>
        </div>

        <a-form layout="vertical" :model="modelForm" @finish="saveConfig">
          <div class="form-grid">
            <a-form-item label="主 LLM Provider">
              <a-input v-model:value="modelForm.llm_provider" />
            </a-form-item>
            <a-form-item label="主 LLM 模型">
              <a-input v-model:value="modelForm.llm_model_name" />
            </a-form-item>
            <a-form-item label="LLM API Base">
              <a-input v-model:value="modelForm.llm_api_base" />
            </a-form-item>
            <a-form-item label="LLM Temperature">
              <a-input-number v-model:value="modelForm.llm_temperature" :min="0" :max="2" :step="0.1" style="width: 100%" />
            </a-form-item>
            <a-form-item label="LLM Max Tokens">
              <a-input-number v-model:value="modelForm.llm_max_tokens" :min="128" :max="8192" style="width: 100%" />
            </a-form-item>
            <a-form-item label="LLM API Key">
              <a-input-password v-model:value="modelForm.llm_api_key" placeholder="留空表示不覆盖现有密钥" />
            </a-form-item>

            <a-form-item label="DeepSeek Base URL">
              <a-input v-model:value="modelForm.deepseek_base_url" />
            </a-form-item>
            <a-form-item label="DeepSeek 模型">
              <a-input v-model:value="modelForm.deepseek_model" />
            </a-form-item>
            <a-form-item label="DeepSeek API Key">
              <a-input-password v-model:value="modelForm.deepseek_api_key" placeholder="留空表示不覆盖现有密钥" />
            </a-form-item>

            <a-form-item label="OCR Provider">
              <a-input v-model:value="modelForm.ocr_provider" />
            </a-form-item>
            <a-form-item label="Embedding 模型">
              <a-input v-model:value="modelForm.chroma_embedding_model" />
            </a-form-item>
            <a-form-item label="Embedding 缓存目录">
              <a-input v-model:value="modelForm.chroma_model_cache_dir" />
            </a-form-item>
          </div>

          <a-alert
            class="inline-alert"
            type="info"
            show-icon
            message="保存配置只更新当前运行时。若要持久化，服务重启前仍需同步到 .env。"
          />

          <div class="action-row">
            <a-button type="primary" html-type="submit" :loading="loading.configSave">保存配置</a-button>
          </div>
        </a-form>
      </div>

      <div class="glass-card panel-card">
        <div class="panel-head">
          <span class="panel-label">连通性测试</span>
        </div>

        <div class="test-grid">
          <div v-for="target in testTargets" :key="target.key" class="test-card">
            <div class="test-head">
              <div>
                <div class="test-title">{{ target.label }}</div>
                <div class="test-desc">{{ target.desc }}</div>
              </div>
              <a-button size="small" :loading="testLoading[target.key]" @click="runTest(target.key)">测试</a-button>
            </div>

            <div class="test-result">
              <a-tag :color="testStatusColor(testResults[target.key]?.success)">
                {{ testResults[target.key]?.success === true ? 'success' : testResults[target.key]?.success === false ? 'failed' : 'idle' }}
              </a-tag>
              <span class="mono">{{ testResults[target.key]?.model || '--' }}</span>
            </div>
            <div class="test-meta">
              <span>耗时：{{ testResults[target.key]?.latency_ms ?? '--' }} ms</span>
            </div>
            <div class="test-message">
              {{ testResults[target.key]?.error || testResults[target.key]?.message || '尚未测试' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel-grid">
      <div class="glass-card panel-card">
        <div class="panel-head">
          <span class="panel-label">Token 可视化</span>
          <a-tag color="purple">按模型聚合</a-tag>
        </div>

        <div class="chart-grid">
          <div class="chart-card">
            <div class="chart-title">各模型总 Token</div>
            <div ref="totalChartRef" class="chart-box"></div>
          </div>
          <div class="chart-card">
            <div class="chart-title">Prompt / Completion 堆叠</div>
            <div ref="stackChartRef" class="chart-box"></div>
          </div>
          <div class="chart-card wide">
            <div class="chart-title">按天趋势</div>
            <div ref="trendChartRef" class="chart-box trend"></div>
          </div>
        </div>

        <a-table
          class="metrics-table"
          :columns="usageColumns"
          :data-source="tableRows"
          :pagination="false"
          row-key="model_name"
        />

        <a-empty v-if="!tableRows.length && !loading.metrics" description="当前时间范围内暂无 Token 数据" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import {
  getModelConfig,
  getModelTokenUsage,
  testModelConnection,
  updateModelConfig
} from '../api/agents'

const loading = reactive({
  config: false,
  configSave: false,
  metrics: false
})

const testLoading = reactive({
  llm: false,
  deepseek: false,
  ocr: false,
  embedding: false
})

const configData = ref(null)
const tokenUsage = ref({
  summary: {},
  by_model: [],
  timeseries: []
})
const testResults = reactive({})

const modelForm = reactive({
  llm_provider: '',
  llm_model_name: '',
  llm_api_base: '',
  llm_api_key: '',
  llm_temperature: 0.7,
  llm_max_tokens: 2048,
  deepseek_base_url: '',
  deepseek_model: '',
  deepseek_api_key: '',
  ocr_provider: '',
  chroma_embedding_model: '',
  chroma_model_cache_dir: ''
})

const dateRange = ref([])
const totalChartRef = ref(null)
const stackChartRef = ref(null)
const trendChartRef = ref(null)

let totalChart = null
let stackChart = null
let trendChart = null

const testTargets = [
  { key: 'llm', label: '主 LLM', desc: '测试主问诊模型 API 连通性' },
  { key: 'deepseek', label: 'DeepSeek', desc: '测试 DeepSeek 诊断链路连通性' },
  { key: 'ocr', label: 'OCR', desc: '测试 OCR 服务调用是否正常' },
  { key: 'embedding', label: 'Embedding', desc: '测试本地 Embedding 初始化' }
]

const tokenSummary = computed(() => tokenUsage.value.summary || {})
const tableRows = computed(() => tokenUsage.value.by_model || [])

const usageColumns = [
  {
    title: '模型名',
    dataIndex: 'model_name',
    key: 'model_name'
  },
  {
    title: 'Provider',
    dataIndex: 'provider',
    key: 'provider'
  },
  {
    title: '请求数',
    dataIndex: 'request_count',
    key: 'request_count',
    customRender: ({ text }) => formatInt(text)
  },
  {
    title: 'Prompt Tokens',
    dataIndex: 'prompt_tokens',
    key: 'prompt_tokens',
    customRender: ({ text }) => formatInt(text)
  },
  {
    title: 'Completion Tokens',
    dataIndex: 'completion_tokens',
    key: 'completion_tokens',
    customRender: ({ text }) => formatInt(text)
  },
  {
    title: 'Total Tokens',
    dataIndex: 'total_tokens',
    key: 'total_tokens',
    customRender: ({ text }) => formatInt(text)
  },
  {
    title: '平均每次',
    dataIndex: 'avg_tokens_per_request',
    key: 'avg_tokens_per_request',
    customRender: ({ text }) => formatInt(text)
  },
  {
    title: '最近调用',
    dataIndex: 'last_called_at',
    key: 'last_called_at'
  }
]

onMounted(async () => {
  await loadConfig()
  await loadTokenUsage()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  totalChart?.dispose()
  stackChart?.dispose()
  trendChart?.dispose()
})

const loadConfig = async () => {
  loading.config = true
  try {
    const response = await getModelConfig()
    configData.value = response
    Object.assign(modelForm, {
      llm_provider: response.llm_provider || '',
      llm_model_name: response.llm_model_name || '',
      llm_api_base: response.llm_api_base || '',
      llm_api_key: '',
      llm_temperature: response.llm_temperature ?? 0.7,
      llm_max_tokens: response.llm_max_tokens ?? 2048,
      deepseek_base_url: response.deepseek_base_url || '',
      deepseek_model: response.deepseek_model || '',
      deepseek_api_key: '',
      ocr_provider: response.ocr_provider || '',
      chroma_embedding_model: response.chroma_embedding_model || '',
      chroma_model_cache_dir: response.chroma_model_cache_dir || ''
    })
  } catch (error) {
    message.error(error.response?.data?.detail || '加载模型配置失败')
  } finally {
    loading.config = false
  }
}

const saveConfig = async () => {
  loading.configSave = true
  try {
    const payload = { ...modelForm }
    if (!payload.llm_api_key) delete payload.llm_api_key
    if (!payload.deepseek_api_key) delete payload.deepseek_api_key
    const response = await updateModelConfig(payload)
    configData.value = response
    modelForm.llm_api_key = ''
    modelForm.deepseek_api_key = ''
    message.success('模型配置已更新到当前运行时')
  } catch (error) {
    message.error(error.response?.data?.detail || '保存模型配置失败')
  } finally {
    loading.configSave = false
  }
}

const runTest = async (target) => {
  testLoading[target] = true
  try {
    const payload = { target }
    if (target === 'llm') {
      payload.model_name = modelForm.llm_model_name
      payload.api_base = modelForm.llm_api_base
      if (modelForm.llm_api_key) payload.api_key = modelForm.llm_api_key
    } else if (target === 'deepseek') {
      payload.model_name = modelForm.deepseek_model
      payload.api_base = modelForm.deepseek_base_url
      if (modelForm.deepseek_api_key) payload.api_key = modelForm.deepseek_api_key
    } else if (target === 'embedding') {
      payload.model_name = modelForm.chroma_embedding_model
    }

    testResults[target] = await testModelConnection(payload)
    message.success(`${target} 测试已完成`)
  } catch (error) {
    testResults[target] = {
      success: false,
      target,
      error: error.response?.data?.detail || error.message || '测试失败'
    }
    message.error(`${target} 测试失败`)
  } finally {
    testLoading[target] = false
  }
}

const loadTokenUsage = async () => {
  loading.metrics = true
  try {
    const params = { group_by: 'day' }
    if (dateRange.value?.[0]) params.date_from = `${dateRange.value[0]}T00:00:00`
    if (dateRange.value?.[1]) params.date_to = `${dateRange.value[1]}T23:59:59`
    tokenUsage.value = await getModelTokenUsage(params)
    await nextTick()
    renderCharts()
  } catch (error) {
    message.error(error.response?.data?.detail || '加载 Token 统计失败')
  } finally {
    loading.metrics = false
  }
}

const handleDateRangeChange = async () => {
  await loadTokenUsage()
}

const renderCharts = () => {
  const rows = tokenUsage.value.by_model || []
  const timeseries = tokenUsage.value.timeseries || []

  if (totalChartRef.value) {
    totalChart = totalChart || echarts.init(totalChartRef.value)
    totalChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 36, bottom: 36 },
      xAxis: {
        type: 'category',
        data: rows.map((item) => item.model_name),
        axisLabel: { color: '#94a3b8', rotate: 18 }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
      },
      series: [
        {
          type: 'bar',
          data: rows.map((item) => item.total_tokens),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#22d3ee' },
              { offset: 1, color: '#2563eb' }
            ]),
            borderRadius: [8, 8, 0, 0]
          }
        }
      ]
    })
  }

  if (stackChartRef.value) {
    stackChart = stackChart || echarts.init(stackChartRef.value)
    stackChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { color: '#cbd5e1' } },
      grid: { left: 40, right: 16, top: 48, bottom: 36 },
      xAxis: {
        type: 'category',
        data: rows.map((item) => item.model_name),
        axisLabel: { color: '#94a3b8', rotate: 18 }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
      },
      series: [
        {
          name: 'Prompt',
          type: 'bar',
          stack: 'tokens',
          data: rows.map((item) => item.prompt_tokens),
          itemStyle: { color: '#38bdf8' }
        },
        {
          name: 'Completion',
          type: 'bar',
          stack: 'tokens',
          data: rows.map((item) => item.completion_tokens),
          itemStyle: { color: '#f59e0b' }
        }
      ]
    })
  }

  if (trendChartRef.value) {
    trendChart = trendChart || echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { color: '#cbd5e1' } },
      grid: { left: 40, right: 16, top: 48, bottom: 36 },
      xAxis: {
        type: 'category',
        data: timeseries.map((item) => item.bucket),
        axisLabel: { color: '#94a3b8' }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
      },
      series: [
        {
          name: 'Prompt',
          type: 'line',
          smooth: true,
          data: timeseries.map((item) => item.prompt_tokens),
          itemStyle: { color: '#22d3ee' },
          areaStyle: { color: 'rgba(34, 211, 238, 0.12)' }
        },
        {
          name: 'Completion',
          type: 'line',
          smooth: true,
          data: timeseries.map((item) => item.completion_tokens),
          itemStyle: { color: '#f97316' },
          areaStyle: { color: 'rgba(249, 115, 22, 0.12)' }
        },
        {
          name: 'Total',
          type: 'line',
          smooth: true,
          data: timeseries.map((item) => item.total_tokens),
          itemStyle: { color: '#a78bfa' }
        }
      ]
    })
  }
}

const resizeCharts = () => {
  totalChart?.resize()
  stackChart?.resize()
  trendChart?.resize()
}

const testStatusColor = (success) => {
  if (success === true) return 'green'
  if (success === false) return 'red'
  return 'default'
}

const formatInt = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return num.toLocaleString('zh-CN')
}
</script>

<style scoped>
.model-center-page {
  display: grid;
  gap: 18px;
}

.page-wrap {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--c-primary, #22d3ee);
  margin-bottom: 4px;
}

.page-title-text {
  font-size: 24px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
}

.page-title-text span {
  font-weight: 400;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
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

.accent-cyan {
  color: #22d3ee;
}

.accent-blue {
  color: #60a5fa;
}

.accent-amber {
  color: #f59e0b;
}

.accent-violet {
  color: #a78bfa;
}

.stat-label {
  color: var(--c-text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stat-value {
  margin-top: 12px;
  font-size: 30px;
  font-weight: 700;
  color: var(--c-text);
}

.stat-value.compact {
  font-size: 15px;
  line-height: 1.5;
}

.stat-foot {
  margin-top: 10px;
  color: var(--c-text-sec);
  font-size: 12px;
}

.panel-grid {
  display: grid;
  gap: 18px;
}

.panel-grid.two-col {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.glass-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
}

.panel-card {
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.panel-label {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-text-sec);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
}

.inline-alert {
  margin: 8px 0 16px;
  border-radius: 14px;
}

.action-row {
  display: flex;
  justify-content: flex-start;
}

.test-grid {
  display: grid;
  gap: 12px;
}

.test-card,
.chart-card {
  border: 1px solid var(--c-border-subtle);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
}

.test-card {
  padding: 14px;
}

.test-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.test-title {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
}

.test-desc,
.test-meta,
.test-message {
  color: var(--c-text-sec);
  font-size: 12px;
}

.test-result {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.test-meta,
.test-message {
  margin-top: 8px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.chart-card {
  padding: 16px;
}

.chart-card.wide {
  grid-column: 1 / -1;
}

.chart-title {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 12px;
}

.chart-box {
  width: 100%;
  height: 280px;
}

.chart-box.trend {
  height: 320px;
}

.metrics-table :deep(.ant-table) {
  background: transparent;
}

.metrics-table :deep(.ant-table-thead > tr > th) {
  background: rgba(255, 255, 255, 0.04);
  color: #cbd5e1;
  border-bottom-color: var(--c-border-subtle);
}

.metrics-table :deep(.ant-table-tbody > tr > td) {
  background: transparent;
  color: #cbd5e1;
  border-bottom-color: var(--c-border-subtle);
}

.mono {
  font-family: 'SF Mono', 'Monaco', monospace;
}

@media (max-width: 1360px) {
  .stats-grid,
  .chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .panel-grid.two-col,
  .form-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-card.wide {
    grid-column: auto;
  }
}

@media (max-width: 900px) {
  .page-header,
  .stats-grid {
    display: grid;
    grid-template-columns: 1fr;
  }

  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
