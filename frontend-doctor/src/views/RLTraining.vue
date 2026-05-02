<template>
  <div class="page-wrap rl-page">
    <div class="page-header">
      <div>
        <div class="section-label">RL OPERATIONS</div>
        <h1 class="page-title-text">强化学习训练 <span>训练台</span></h1>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card accent-cyan">
        <div class="stat-label">最近数据集</div>
        <div class="stat-value mono">{{ latestDataset.datasetSize }}</div>
        <div class="stat-foot">{{ latestDataset.summary }}</div>
      </div>
      <div class="stat-card accent-blue">
        <div class="stat-label">最近训练</div>
        <div class="stat-value mono">{{ latestTraining.runId }}</div>
        <div class="stat-foot">{{ latestTraining.summary }}</div>
      </div>
      <div class="stat-card accent-amber">
        <div class="stat-label">最近评估</div>
        <div class="stat-value mono">{{ latestEvaluation.reward }}</div>
        <div class="stat-foot">{{ latestEvaluation.summary }}</div>
      </div>
      <div class="stat-card accent-violet">
        <div class="stat-label">当前激活</div>
        <div class="stat-value mono">{{ latestActivation.version }}</div>
        <div class="stat-foot">{{ latestActivation.summary }}</div>
      </div>
    </div>

    <a-tabs v-model:activeKey="activeTab" class="rl-tabs">
      <a-tab-pane key="dataset" tab="数据集">
        <div class="panel-grid two-col">
          <div class="glass-card panel-card">
            <div class="panel-head">
              <span class="panel-label">构建</span>
              <a-tag :color="datasetStateTag.color">{{ datasetStateTag.text }}</a-tag>
            </div>

            <a-form layout="vertical" :model="datasetForm" @finish="submitDatasetBuild">
              <a-form-item label="策略范围">
                <a-select v-model:value="datasetForm.agent_type" :options="agentTypeOptions" />
              </a-form-item>
              <a-form-item label="样本上限">
                <a-input-number v-model:value="datasetForm.limit" :min="1" :max="50000" style="width: 100%" />
              </a-form-item>
              <div class="action-row">
                <a-button type="primary" html-type="submit" :loading="loading.datasetBuild">生成数据集</a-button>
              </div>
            </a-form>
          </div>

          <div class="glass-card panel-card">
            <div class="panel-head">
              <span class="panel-label">最近构建结果</span>
            </div>

            <div v-if="datasetResult" class="kv-grid">
              <div class="kv-item">
                <span class="kv-label">数据集 ID</span>
                <span class="kv-value mono">{{ datasetResult.dataset_id }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">总样本</span>
                <span class="kv-value mono">{{ datasetResult.total_entries ?? 0 }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">训练集</span>
                <span class="kv-value mono">{{ datasetResult.train_size ?? 0 }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">验证集</span>
                <span class="kv-value mono">{{ datasetResult.val_size ?? 0 }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">测试集</span>
                <span class="kv-value mono">{{ datasetResult.test_size ?? 0 }}</span>
              </div>
              <div class="kv-item wide">
                <span class="kv-label">策略类型</span>
                <span class="kv-value">{{ (datasetResult.policy_types || []).join(', ') || '--' }}</span>
              </div>
            </div>

            <div v-if="exportArtifacts.length" class="artifact-panel">
              <div class="artifact-title">导出文件</div>
              <div class="artifact-list">
                <div v-for="item in exportArtifacts" :key="item.split" class="artifact-item">
                  <div class="artifact-meta">
                    <span class="artifact-split">{{ item.split }}</span>
                    <span class="artifact-name mono">{{ item.file_name }}</span>
                  </div>
                  <a-button size="small" @click="handleDownload(item)">下载</a-button>
                </div>
              </div>
            </div>

            <a-empty v-if="!datasetResult && !exportArtifacts.length" description="暂无结果" />
          </div>
        </div>

        <div class="glass-card panel-card">
          <div class="panel-head">
            <span class="panel-label">数据集列表</span>
            <a-button size="small" :loading="loading.datasetList" @click="loadDatasets">刷新</a-button>
          </div>

          <div class="dataset-picker-row">
            <a-select
              v-model:value="selectedDatasetId"
              placeholder="选择已构建数据集"
              style="width: 100%"
              :options="datasetOptions"
            />
          </div>

          <div v-if="selectedDataset" class="dataset-summary">
            <span>当前训练/评估将使用数据集：</span>
            <span class="mono">{{ selectedDataset.dataset_id }}</span>
            <span>({{ selectedDataset.agent_type }} · {{ selectedDatasetSummary }})</span>
          </div>

          <div v-if="datasets.length" class="result-list">
            <div v-for="item in datasets" :key="item.dataset_id" class="result-item">
              <div class="result-head">
                <span class="result-title">{{ item.agent_type }}</span>
                <a-tag :color="item.dataset_id === selectedDatasetId ? 'cyan' : 'default'">
                  {{ item.dataset_id === selectedDatasetId ? '已选中' : '可选' }}
                </a-tag>
              </div>
              <div class="result-meta">
                <span class="mono">{{ item.dataset_id }}</span>
                <a-button size="small" @click="selectDataset(item.dataset_id)">用于训练</a-button>
              </div>
              <div class="metric-row">
                <a-tag>样本 {{ item.summary?.total_entries ?? 0 }}</a-tag>
                <a-tag>训练 {{ item.summary?.train_size ?? 0 }}</a-tag>
                <a-tag>验证 {{ item.summary?.val_size ?? 0 }}</a-tag>
                <a-tag>测试 {{ item.summary?.test_size ?? 0 }}</a-tag>
              </div>
            </div>
          </div>
          <a-empty v-else description="暂无已构建数据集" />
        </div>
      </a-tab-pane>

      <a-tab-pane key="training" tab="训练">
        <div class="panel-grid two-col">
          <div class="glass-card panel-card">
            <div class="panel-head">
              <span class="panel-label">启动训练</span>
              <a-tag :color="trainingStateTag.color">{{ trainingStateTag.text }}</a-tag>
            </div>

            <a-alert
              class="inline-alert"
              type="info"
              show-icon
              message="训练前请先在数据集页构建并选择一个数据集。Run ID 将在训练完成后自动带入运行查询。"
            />

            <a-form layout="vertical" :model="trainingForm" @finish="submitTrainingRun">
              <a-form-item label="已选数据集">
                <a-select
                  v-model:value="trainingForm.dataset_id"
                  placeholder="请选择数据集"
                  :options="datasetOptions"
                />
              </a-form-item>
              <a-form-item label="策略范围">
                <a-input :value="selectedDataset?.agent_type || '--'" disabled />
              </a-form-item>
              <a-form-item>
                <a-checkbox v-model:checked="trainingForm.auto_activate">训练后自动激活</a-checkbox>
              </a-form-item>
              <div class="action-row">
                <a-button type="primary" html-type="submit" :loading="loading.trainingRun">开始训练</a-button>
              </div>
            </a-form>
          </div>

          <div class="glass-card panel-card">
            <div class="panel-head">
              <span class="panel-label">训练产出</span>
            </div>

            <div v-if="trainingPolicies.length" class="result-list">
              <div v-for="item in trainingPolicies" :key="item.policy_type + item.run_id" class="result-item">
                <div class="result-head">
                  <span class="result-title">{{ item.policy_type }}</span>
                  <a-tag color="blue">{{ item.policy_version || '--' }}</a-tag>
                </div>
                <div class="result-meta">
                  <span class="mono">{{ item.run_id }}</span>
                  <div class="inline-actions">
                    <a-button size="small" @click="queryRun(item.run_id)">查询此运行</a-button>
                    <a-button size="small" @click="copyText(item.run_id)">复制</a-button>
                  </div>
                </div>
                <div class="metric-row">
                  <a-tag v-for="metric in formatMetrics(item.metrics)" :key="metric.key">
                    {{ metric.label }}: {{ metric.value }}
                  </a-tag>
                </div>
              </div>
            </div>
            <a-empty v-else description="请先构建并选择数据集，再启动训练" />
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="evaluation" tab="评估与激活">
        <div class="panel-grid two-col">
          <div class="glass-card panel-card">
            <div class="panel-head">
              <span class="panel-label">离线评估</span>
            </div>

            <a-alert
              class="inline-alert"
              type="info"
              show-icon
              :message="selectedDataset ? `当前评估数据集：${selectedDataset.dataset_id}` : '请先选择数据集后再评估'"
            />

            <a-form layout="vertical" :model="evaluationForm" @finish="submitEvaluation">
              <a-form-item label="已选数据集">
                <a-select
                  v-model:value="evaluationForm.dataset_id"
                  placeholder="请选择数据集"
                  :options="datasetOptions"
                />
              </a-form-item>
              <a-form-item label="策略范围">
                <a-input :value="selectedDataset?.agent_type || '--'" disabled />
              </a-form-item>
              <div class="action-row">
                <a-button type="primary" html-type="submit" :loading="loading.evaluationRun">开始评估</a-button>
              </div>
            </a-form>

            <div v-if="evaluationCards.length" class="metrics-grid">
              <div v-for="card in evaluationCards" :key="card.key" class="metric-card">
                <div class="metric-name">{{ card.label }}</div>
                <div class="metric-value mono">{{ card.value }}</div>
              </div>
            </div>
          </div>

          <div class="glass-card panel-card">
            <div class="panel-head">
              <span class="panel-label">策略激活</span>
            </div>

            <a-alert
              class="inline-alert"
              type="info"
              show-icon
              message="版本号来自训练结果，或从下方历史版本中选择。"
            />

            <a-form layout="vertical" :model="activationForm">
              <a-form-item label="策略类型">
                <a-select v-model:value="activationForm.policy_type" :options="policyTypeOptions" />
              </a-form-item>
              <a-form-item label="策略版本">
                <a-select
                  v-model:value="activationForm.policy_version"
                  placeholder="请选择或输入版本号"
                  :options="policyVersionOptions"
                  show-search
                  :filter-option="filterOption"
                />
              </a-form-item>
              <div class="action-row activation-row">
                <a-button @click="activateLatestTrainedVersion" :disabled="!latestTrainableVersion">
                  激活最近训练版本
                </a-button>
                <a-popconfirm
                  title="确认激活该版本？"
                  ok-text="确认"
                  cancel-text="取消"
                  @confirm="submitPolicyActivation"
                >
                  <a-button type="primary" danger :loading="loading.policyActivation">激活策略</a-button>
                </a-popconfirm>
              </div>
            </a-form>

            <div v-if="activationState" class="kv-grid compact-grid">
              <div class="kv-item">
                <span class="kv-label">类型</span>
                <span class="kv-value">{{ activationState.policy_type }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">版本</span>
                <span class="kv-value mono">{{ activationState.version }}</span>
              </div>
            </div>

            <div v-if="policyVersions.length" class="artifact-panel">
              <div class="artifact-title">历史版本</div>
              <div class="result-list">
                <div v-for="item in policyVersions" :key="item.version" class="result-item">
                  <div class="result-head">
                    <span class="result-title mono">{{ item.version }}</span>
                    <a-tag :color="item.is_active ? 'green' : 'default'">
                      {{ item.is_active ? '当前激活' : '历史版本' }}
                    </a-tag>
                  </div>
                  <div class="result-meta">
                    <span>{{ item.created_at || '--' }}</span>
                    <a-button size="small" @click="usePolicyVersion(item)">使用此版本</a-button>
                  </div>
                </div>
              </div>
            </div>
            <a-empty v-else description="请先训练得到策略版本或从历史版本中选择" />
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="runs" tab="运行查询">
        <div class="panel-grid">
          <div class="glass-card panel-card">
            <div class="panel-head">
              <span class="panel-label">Run ID</span>
            </div>

            <a-alert
              class="inline-alert"
              type="info"
              show-icon
              message="Run ID 来源于训练结果卡片，训练完成后会自动带入此处。"
            />

            <div class="run-query-row">
              <a-input v-model:value="runQueryForm.run_id" placeholder="输入 Run ID" @pressEnter="submitRunQuery" />
              <a-button type="primary" :loading="loading.runQuery" @click="submitRunQuery">查询</a-button>
            </div>

            <div v-if="runStatus" class="run-status-grid">
              <div class="kv-item">
                <span class="kv-label">状态</span>
                <span class="kv-value">{{ runStatus.status || '--' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">策略类型</span>
                <span class="kv-value">{{ runStatus.policy_type || '--' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">版本</span>
                <span class="kv-value mono">{{ runStatus.version || '--' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">数据集 ID</span>
                <span class="kv-value mono">{{ runStatus.dataset_id || runStatus.params?.dataset_id || '--' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">开始时间</span>
                <span class="kv-value mono">{{ runStatus.started_at || '--' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">更新时间</span>
                <span class="kv-value mono">{{ runStatus.updated_at || '--' }}</span>
              </div>
            </div>

            <div v-if="runStatus?.error" class="error-box">{{ runStatus.error }}</div>
            <a-empty v-else-if="!runStatus" description="可从训练结果直接带入 Run ID" />
          </div>
        </div>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  activatePolicy,
  buildTrainingDataset,
  downloadTrainingExport,
  evaluateTraining,
  getTrainingRunStatus,
  listPolicyVersions,
  listTrainingDatasets,
  runTraining
} from '../api/agents'

const activeTab = ref('dataset')

const agentTypeOptions = [
  { label: '全部策略', value: 'all' },
  { label: '路由策略', value: 'moderator' },
  { label: 'PCC', value: 'pcc' },
  { label: 'MDT', value: 'mdt' },
  { label: 'ICT', value: 'ict' },
  { label: '患者模拟器', value: 'patient_simulator' }
]

const policyTypeOptions = [
  { label: '问诊路由', value: 'routing' },
  { label: '追问策略', value: 'followup' },
  { label: '分诊策略', value: 'triage' },
  { label: 'moderator', value: 'moderator' },
  { label: 'pcc', value: 'pcc' },
  { label: 'mdt', value: 'mdt' },
  { label: 'ict', value: 'ict' }
]

const loading = reactive({
  datasetBuild: false,
  datasetList: false,
  trainingRun: false,
  evaluationRun: false,
  policyActivation: false,
  policyVersions: false,
  runQuery: false
})

const requestState = reactive({
  dataset: 'idle',
  training: 'idle'
})

const datasetForm = reactive({
  agent_type: 'all',
  limit: 1000
})

const trainingForm = reactive({
  dataset_id: undefined,
  auto_activate: false
})

const evaluationForm = reactive({
  dataset_id: undefined
})

const activationForm = reactive({
  policy_type: 'routing',
  policy_version: undefined
})

const runQueryForm = reactive({
  run_id: ''
})

const datasetResult = ref(null)
const trainingResult = ref(null)
const evaluationResult = ref(null)
const activationState = ref(null)
const runStatus = ref(null)
const datasets = ref([])
const selectedDatasetId = ref(undefined)
const policyVersions = ref([])

const latestDataset = computed(() => {
  if (!datasetResult.value) {
    return { datasetSize: '--', summary: '未生成' }
  }
  return {
    datasetSize: datasetResult.value.dataset_size ?? datasetResult.value.total_entries ?? 0,
    summary: `${datasetResult.value.train_size ?? 0}/${datasetResult.value.val_size ?? 0}/${datasetResult.value.test_size ?? 0}`
  }
})

const latestTraining = computed(() => {
  const item = trainingResult.value?.policy_results?.[0]
  if (!item) return { runId: '--', summary: '未训练' }
  return {
    runId: truncateMiddle(item.run_id),
    summary: `${item.policy_type} · ${truncateMiddle(item.policy_version, 18)}`
  }
})

const latestEvaluation = computed(() => {
  const metrics = evaluationResult.value?.metrics
  if (!metrics) return { reward: '--', summary: '未评估' }
  return {
    reward: metricDisplay(metrics.avg_reward),
    summary: selectedDataset.value?.dataset_id ? truncateMiddle(selectedDataset.value.dataset_id, 18) : '数据集待定'
  }
})

const latestActivation = computed(() => {
  if (!activationState.value) return { version: '--', summary: '未激活' }
  return {
    version: truncateMiddle(activationState.value.version, 18),
    summary: activationState.value.policy_type || '--'
  }
})

const datasetStateTag = computed(() => ({
  idle: { color: 'default', text: '未执行' },
  loading: { color: 'processing', text: '处理中' },
  success: { color: 'success', text: '成功' },
  failed: { color: 'error', text: '失败' }
}[requestState.dataset]))

const trainingStateTag = computed(() => ({
  idle: { color: 'default', text: '未执行' },
  loading: { color: 'processing', text: '处理中' },
  success: { color: 'success', text: '成功' },
  failed: { color: 'error', text: '失败' }
}[requestState.training]))

const exportArtifacts = computed(() => {
  const artifacts = datasetResult.value?.export_artifacts || []
  if (artifacts.length) return artifacts

  const files = datasetResult.value?.export_files || {}
  return Object.entries(files)
    .filter(([split]) => split !== 'export_samples')
    .map(([split, fullPath]) => {
      const fileName = String(fullPath || '').split(/[/\\]/).pop() || ''
      return {
        split,
        file_name: fileName,
        download_url: `/api/v1/agents/training/exports/${encodeURIComponent(fileName)}`
      }
    })
})

const trainingPolicies = computed(() => trainingResult.value?.policy_results || [])

const evaluationCards = computed(() => {
  const metrics = evaluationResult.value?.metrics
  if (!metrics) return []
  return [
    { key: 'reward', label: '平均奖励', value: metricDisplay(metrics.avg_reward) },
    { key: 'triage', label: '分诊准确率', value: metricDisplay(metrics.triage_accuracy, true) },
    { key: 'flags', label: '红旗召回', value: metricDisplay(metrics.red_flag_recall, true) },
    { key: 'turns', label: '平均轮次', value: metricDisplay(metrics.avg_turns) },
    { key: 'adoption', label: '病历采用率', value: metricDisplay(metrics.record_adoption_rate, true) }
  ]
})

const datasetOptions = computed(() => datasets.value.map((item) => ({
  label: `${item.dataset_id} · ${item.agent_type} · ${item.summary?.total_entries ?? 0} 条`,
  value: item.dataset_id
})))

const selectedDataset = computed(() => datasets.value.find((item) => item.dataset_id === selectedDatasetId.value) || null)

const selectedDatasetSummary = computed(() => {
  const summary = selectedDataset.value?.summary
  if (!summary) return '--'
  return `${summary.train_size ?? 0}/${summary.val_size ?? 0}/${summary.test_size ?? 0}`
})

const policyVersionOptions = computed(() => policyVersions.value.map((item) => ({
  label: item.is_active ? `${item.version} · 当前激活` : item.version,
  value: item.version
})))

const latestTrainableVersion = computed(() => {
  const item = trainingPolicies.value.find((row) => row.policy_type === activationForm.policy_type)
  return item ? { policy_type: item.policy_type, policy_version: item.policy_version } : null
})

watch(selectedDatasetId, (value) => {
  trainingForm.dataset_id = value
  evaluationForm.dataset_id = value
})

watch(
  () => trainingForm.dataset_id,
  (value) => {
    if (value && value !== selectedDatasetId.value) {
      selectedDatasetId.value = value
    }
  }
)

watch(
  () => evaluationForm.dataset_id,
  (value) => {
    if (value && value !== selectedDatasetId.value) {
      selectedDatasetId.value = value
    }
  }
)

watch(
  () => activationForm.policy_type,
  async (value) => {
    activationForm.policy_version = undefined
    if (!value) {
      policyVersions.value = []
      return
    }
    await loadPolicyVersions(value)
  },
  { immediate: true }
)

onMounted(async () => {
  await loadDatasets()
})

const getErrorMessage = (error, fallback) => {
  return error?.response?.data?.detail || error?.response?.data?.message || fallback
}

const loadDatasets = async () => {
  loading.datasetList = true
  try {
    datasets.value = await listTrainingDatasets()
    if (!selectedDatasetId.value && datasets.value.length) {
      selectDataset(datasets.value[0].dataset_id)
    }
  } catch (error) {
    message.error(getErrorMessage(error, '加载数据集失败'))
  } finally {
    loading.datasetList = false
  }
}

const loadPolicyVersions = async (policyType) => {
  loading.policyVersions = true
  try {
    policyVersions.value = await listPolicyVersions(policyType)
    if (!activationForm.policy_version && policyVersions.value.length) {
      const active = policyVersions.value.find((item) => item.is_active)
      activationForm.policy_version = active?.version || policyVersions.value[0].version
    }
  } catch (error) {
    policyVersions.value = []
    message.error(getErrorMessage(error, '加载策略版本失败'))
  } finally {
    loading.policyVersions = false
  }
}

const selectDataset = (datasetId) => {
  selectedDatasetId.value = datasetId
}

const syncTrainingOutputs = async () => {
  await loadDatasets()

  const firstResult = trainingPolicies.value[0]
  if (!firstResult) return

  runQueryForm.run_id = firstResult.run_id
  activationForm.policy_type = firstResult.policy_type
  await loadPolicyVersions(firstResult.policy_type)
  activationForm.policy_version = firstResult.policy_version
}

const submitDatasetBuild = async () => {
  loading.datasetBuild = true
  requestState.dataset = 'loading'
  try {
    datasetResult.value = await buildTrainingDataset({
      agent_type: datasetForm.agent_type,
      limit: datasetForm.limit || undefined
    })
    requestState.dataset = 'success'
    selectDataset(datasetResult.value.dataset_id)
    await loadDatasets()
    message.success('数据集已生成，并已设置为当前训练数据集')
  } catch (error) {
    requestState.dataset = 'failed'
    message.error(getErrorMessage(error, '生成失败'))
  } finally {
    loading.datasetBuild = false
  }
}

const submitTrainingRun = async () => {
  if (!trainingForm.dataset_id) {
    message.warning('请先选择数据集，再启动训练')
    activeTab.value = 'dataset'
    return
  }

  loading.trainingRun = true
  requestState.training = 'loading'
  try {
    trainingResult.value = await runTraining({
      dataset_id: trainingForm.dataset_id,
      agent_type: selectedDataset.value?.agent_type || 'all',
      auto_activate: trainingForm.auto_activate
    })
    requestState.training = 'success'
    await syncTrainingOutputs()
    message.success('训练完成，Run ID 与策略版本已自动带入')
  } catch (error) {
    requestState.training = 'failed'
    message.error(getErrorMessage(error, '训练失败'))
  } finally {
    loading.trainingRun = false
  }
}

const submitEvaluation = async () => {
  if (!evaluationForm.dataset_id) {
    message.warning('请先选择数据集后再评估')
    activeTab.value = 'dataset'
    return
  }

  loading.evaluationRun = true
  try {
    evaluationResult.value = await evaluateTraining({
      dataset_id: evaluationForm.dataset_id,
      agent_type: selectedDataset.value?.agent_type || 'all'
    })
    message.success('评估完成')
  } catch (error) {
    message.error(getErrorMessage(error, '评估失败'))
  } finally {
    loading.evaluationRun = false
  }
}

const submitPolicyActivation = async () => {
  if (!activationForm.policy_version) {
    message.warning('请先选择一个策略版本')
    return
  }

  loading.policyActivation = true
  try {
    const response = await activatePolicy(activationForm.policy_type, activationForm)
    activationState.value = {
      policy_type: response.policy_type,
      version: response.version,
      snapshot_path: response.snapshot_path
    }
    await loadPolicyVersions(activationForm.policy_type)
    message.success('激活成功')
  } catch (error) {
    message.error(getErrorMessage(error, '激活失败'))
  } finally {
    loading.policyActivation = false
  }
}

const activateLatestTrainedVersion = async () => {
  if (!latestTrainableVersion.value) {
    message.warning('当前策略类型没有最近训练版本')
    return
  }
  activationForm.policy_type = latestTrainableVersion.value.policy_type
  activationForm.policy_version = latestTrainableVersion.value.policy_version
  await submitPolicyActivation()
}

const submitRunQuery = async () => {
  if (!runQueryForm.run_id.trim()) {
    message.warning('请输入 Run ID')
    return
  }

  loading.runQuery = true
  try {
    runStatus.value = await getTrainingRunStatus(runQueryForm.run_id.trim())
    message.success('查询成功')
  } catch (error) {
    runStatus.value = null
    message.error(getErrorMessage(error, '查询失败'))
  } finally {
    loading.runQuery = false
  }
}

const queryRun = async (runId) => {
  if (!runId) return
  runQueryForm.run_id = runId
  activeTab.value = 'runs'
  await submitRunQuery()
}

const usePolicyVersion = (item) => {
  activationForm.policy_type = item.policy_type
  activationForm.policy_version = item.version
}

const handleDownload = async (item) => {
  if (!item?.file_name) {
    message.warning('文件不存在')
    return
  }

  try {
    const blob = await downloadTrainingExport(item.file_name)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = item.file_name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    message.success('下载已开始')
  } catch (error) {
    message.error(getErrorMessage(error, '下载失败'))
  }
}

const formatMetrics = (metrics) => {
  if (!metrics || typeof metrics !== 'object') return []
  return Object.entries(metrics).slice(0, 4).map(([key, value]) => ({
    key,
    label: key,
    value: metricDisplay(value, /rate|accuracy|recall/i.test(key))
  }))
}

const metricDisplay = (value, percentage = false) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  if (percentage) return `${(num * 100).toFixed(1)}%`
  return num.toFixed(3)
}

const truncateMiddle = (text, max = 14) => {
  if (!text) return '--'
  if (text.length <= max) return text
  const side = Math.max(4, Math.floor((max - 3) / 2))
  return `${text.slice(0, side)}...${text.slice(-side)}`
}

const copyText = async (text) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(String(text))
    message.success('已复制')
  } catch (error) {
    message.error('复制失败')
  }
}

const filterOption = (input, option) => String(option?.label || '').toLowerCase().includes(String(input).toLowerCase())
</script>

<style scoped>
.rl-page {
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  position: relative;
  overflow: hidden;
  min-height: 132px;
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

.stat-foot {
  margin-top: 10px;
  color: var(--c-text-sec);
  font-size: 12px;
}

.rl-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 20px;
}

.rl-tabs :deep(.ant-tabs-tab) {
  color: #94a3b8;
}

.rl-tabs :deep(.ant-tabs-tab-active) {
  color: #22d3ee;
}

.rl-tabs :deep(.ant-tabs-ink-bar) {
  background: #22d3ee;
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

.action-row {
  display: flex;
  justify-content: flex-start;
}

.activation-row {
  gap: 10px;
  flex-wrap: wrap;
}

.inline-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.inline-alert {
  margin-bottom: 16px;
}

.kv-grid,
.run-status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.compact-grid {
  margin-top: 16px;
}

.kv-item,
.metric-card,
.result-item,
.artifact-panel,
.error-box {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
}

.kv-item.wide {
  grid-column: 1 / -1;
}

.kv-label {
  color: var(--c-text-muted);
  font-size: 12px;
}

.kv-value {
  margin-top: 6px;
  color: var(--c-text);
  font-size: 13px;
  font-weight: 600;
}

.artifact-panel,
.dataset-summary {
  margin-top: 14px;
}

.artifact-title {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 12px;
}

.artifact-list,
.result-list {
  display: grid;
  gap: 10px;
}

.artifact-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--c-border-subtle);
}

.artifact-meta {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.artifact-split {
  color: #22d3ee;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.artifact-name,
.result-title {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
}

.result-head,
.result-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.result-meta,
.dataset-summary {
  color: var(--c-text-sec);
  font-size: 12px;
}

.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.metric-name {
  color: var(--c-text-muted);
  font-size: 12px;
}

.metric-value {
  margin-top: 8px;
  color: var(--c-text);
  font-size: 20px;
  font-weight: 700;
}

.run-query-row,
.dataset-picker-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

.dataset-picker-row {
  grid-template-columns: 1fr;
}

.run-status-grid {
  margin-top: 16px;
}

.error-box {
  margin-top: 14px;
  color: #fca5a5;
  font-size: 12px;
  line-height: 1.6;
}

.mono {
  font-family: 'SF Mono', 'Monaco', monospace;
}

@media (max-width: 1360px) {
  .stats-grid,
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .panel-grid.two-col {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .page-header,
  .stats-grid,
  .kv-grid,
  .run-status-grid,
  .metrics-grid,
  .run-query-row,
  .artifact-item {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>
