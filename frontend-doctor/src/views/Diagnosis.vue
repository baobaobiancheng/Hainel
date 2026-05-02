<template>
  <div class="page-wrap diagnosis-page">
    <div class="page-header">
      <div>
        <div class="section-label">DIAGNOSIS WORKSTATION</div>
        <h1 class="page-title-text">诊断 <span>总览台</span></h1>
      </div>
      <div class="header-actions">
        <a-select
          v-model:value="selectedConversationId"
          show-search
          allow-clear
          placeholder="选择会话加载诊断上下文"
          style="width: 360px"
          option-filter-prop="label"
          :options="conversationOptions"
          @change="handleConversationChange"
        />
      </div>
    </div>

    <a-spin :spinning="loading">
      <div v-if="!selectedConversationId" class="empty-state glass-card">
        <div class="empty-icon">+</div>
        <p>选择一个会话，查看患者诊断上下文、知识图谱提示和病历入口。</p>
      </div>

      <div v-else-if="loadError" class="empty-state glass-card">
        <div class="empty-icon warn">!</div>
        <p>{{ loadError }}</p>
      </div>

      <template v-else-if="diagnosisContext">
        <div v-if="isUrgent" class="glass-card urgent-banner">
          <div class="urgent-title">高优先级风险提醒</div>
          <div class="urgent-text">
            当前会话命中紧急分诊或高风险诊断，请优先处理红旗症状、行动清单与线下就医建议。
          </div>
        </div>

        <div class="glass-card hero-card">
          <div class="hero-main">
            <div>
              <div class="hero-title">{{ diagnosisContext.patient.name || '未命名患者' }}</div>
              <div class="hero-sub">
                {{ diagnosisContext.conversation.title || diagnosisContext.conversation.chief_complaint || '未命名会话' }}
              </div>
              <div class="hero-meta">
                <span class="meta-chip">{{ statusLabel(diagnosisContext.conversation.status) }}</span>
                <span v-if="diagnosisContext.patient.gender" class="meta-chip">{{ diagnosisContext.patient.gender }}</span>
                <span v-if="hasAge" class="meta-chip">{{ diagnosisContext.patient.age }} 岁</span>
                <span v-if="triageDepartment" class="meta-chip accent">{{ triageDepartment }}</span>
                <span v-if="triageUrgency" class="meta-chip" :class="urgencyClass">{{ triageUrgency }}</span>
                <span v-if="diagnosisContext.latest_diagnosis?.difficulty" class="meta-chip">
                  {{ difficultyLabel(diagnosisContext.latest_diagnosis.difficulty) }}
                </span>
              </div>
            </div>
            <div class="hero-actions">
              <button class="ghost-btn" @click="openConversationDetail">查看会话</button>
              <button class="ghost-btn" :disabled="!diagnosisContext.latest_diagnosis" @click="submitAgentFeedback('useful')">AI 有用</button>
              <button class="ghost-btn" :disabled="!diagnosisContext.latest_diagnosis" @click="submitAgentFeedback('inaccurate')">AI 不准确</button>
              <button class="ghost-btn primary" @click="openRecordWorkspace">
                {{ diagnosisContext.medical_records.length ? '查看病历工作台' : '生成病历草稿' }}
              </button>
            </div>
          </div>

          <div class="complaint-block">
            <div class="block-label">主诉</div>
            <div class="block-text">{{ diagnosisContext.conversation.chief_complaint || '暂无主诉' }}</div>
          </div>

          <div class="micro-stats">
            <div class="micro-card">
              <div class="micro-label">红旗症状</div>
              <div class="micro-value">{{ redFlags.length }}</div>
            </div>
            <div class="micro-card">
              <div class="micro-label">关联报告</div>
              <div class="micro-value">{{ diagnosisContext.linked_reports.length }}</div>
            </div>
            <div class="micro-card">
              <div class="micro-label">智能体参与</div>
              <div class="micro-value">{{ diagnosisContext.latest_diagnosis?.agents_used || 0 }}</div>
            </div>
            <div class="micro-card">
              <div class="micro-label">关联病历</div>
              <div class="micro-value">{{ diagnosisContext.medical_records.length }}</div>
            </div>
          </div>
        </div>

        <div class="diag-grid">
          <div class="main-col">
            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">AI 最终诊断结论</span>
                <span v-if="diagnosisContext.latest_diagnosis?.created_at" class="panel-hint mono">
                  {{ formatDateTime(diagnosisContext.latest_diagnosis.created_at) }}
                </span>
              </div>
              <div
                v-if="diagnosisContext.latest_diagnosis"
                class="rich-content"
                v-html="renderDiagnosisHtml(diagnosisContext.latest_diagnosis.content)"
              />
              <div v-else class="panel-empty">当前会话暂无智能诊断结果。</div>
            </div>

            <div v-if="redFlags.length" class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label danger">红旗症状</span>
              </div>
              <div class="flag-list">
                <div v-for="(flag, index) in redFlags" :key="index" class="flag-item">
                  <div class="flag-name">{{ flag.category || '风险提示' }}</div>
                  <div class="flag-tags">
                    <span v-for="keyword in (flag.keywords || [])" :key="keyword" class="flag-tag">
                      {{ keyword }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">行动清单</span>
              </div>
              <div v-if="actionChecklistSections.length" class="checklist-grid">
                <div v-for="section in actionChecklistSections" :key="section.key" class="checklist-section">
                  <div class="checklist-title">{{ section.title }}</div>
                  <ul class="checklist-list">
                    <li v-for="item in section.items" :key="item">{{ item }}</li>
                  </ul>
                </div>
              </div>
              <div v-else class="panel-empty">暂无行动清单。</div>
            </div>

            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">结构化问诊摘要</span>
              </div>
              <div v-if="structuredIntakeItems.length" class="kv-grid">
                <div v-for="item in structuredIntakeItems" :key="item.key" class="kv-item">
                  <div class="kv-label">{{ item.label }}</div>
                  <div class="kv-value">{{ item.value }}</div>
                </div>
              </div>
              <div v-else class="panel-empty">暂无结构化问诊数据。</div>
            </div>

            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">报告摘要与 OCR</span>
              </div>
              <div v-if="diagnosisContext.linked_reports.length" class="report-list">
                <div
                  v-for="report in diagnosisContext.linked_reports.slice(0, 3)"
                  :key="report.message_id || report.file_name"
                  class="report-item"
                >
                  <div class="report-head">
                    <div class="report-name">{{ report.file_name || report.report_type || '未命名报告' }}</div>
                    <span class="report-type">{{ report.report_type || report.file_type || '检查报告' }}</span>
                  </div>
                  <div class="report-text">{{ truncateText(report.ocr_text || '暂无 OCR 文本', 260) }}</div>
                </div>
              </div>
              <div v-else class="panel-empty">当前会话暂无关联报告。</div>
            </div>
          </div>

          <div class="side-col">
            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">患者健康档案</span>
              </div>
              <div v-if="healthProfileItems.length" class="kv-grid compact">
                <div v-for="item in healthProfileItems" :key="item.key" class="kv-item">
                  <div class="kv-label">{{ item.label }}</div>
                  <div class="kv-value">{{ item.value }}</div>
                </div>
              </div>
              <div v-else class="panel-empty">暂无健康档案信息。</div>
            </div>

            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">多智能体分析详情</span>
              </div>
              <div v-if="analysisCards.length" class="analysis-list">
                <div v-for="card in analysisCards" :key="card.key" class="analysis-card">
                  <div class="analysis-card-title">{{ card.title }}</div>
                  <div v-if="card.type === 'markdown'" class="rich-content compact" v-html="renderDiagnosisHtml(card.content)" />
                  <div v-else-if="card.type === 'opinions'" class="opinion-list">
                    <div v-for="(opinion, index) in card.content" :key="index" class="opinion-item">
                      <div class="opinion-role">{{ opinion.role || opinion.agent_name || `专家 ${index + 1}` }}</div>
                      <div class="opinion-text">{{ opinion.opinion || opinion.analysis || opinion.diagnosis || '暂无内容' }}</div>
                    </div>
                  </div>
                  <div v-else class="analysis-text">{{ card.content }}</div>
                </div>
              </div>
              <div v-else class="panel-empty">暂无可展示的多智能体内容。</div>
            </div>

            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">知识图谱临床提示</span>
              </div>
              <div v-if="kgSummary" class="kg-summary">{{ kgSummary }}</div>
              <div v-if="kgGroups.length" class="kg-group-grid">
                <div v-for="group in kgGroups" :key="group.key" class="kg-group-card">
                  <div class="kg-group-title">{{ group.title }}</div>
                  <div class="kg-chip-list">
                    <span v-for="item in group.display_items" :key="`${group.key}-${item.target}-${item.relation}`" class="kg-chip">
                      {{ item.display_text }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-if="!kgSummary && !kgGroups.length" class="panel-empty">暂无知识图谱摘要。</div>
            </div>

            <div class="glass-card panel-card">
              <div class="panel-head">
                <span class="panel-label">关联病历</span>
              </div>
              <div v-if="diagnosisContext.medical_records.length" class="record-list">
                <button
                  v-for="record in diagnosisContext.medical_records"
                  :key="record.id"
                  class="record-item"
                  @click="openRecord(record.id)"
                >
                  <div>
                    <div class="record-title">{{ record.title }}</div>
                    <div class="record-time mono">{{ formatDateTime(record.updated_at) }}</div>
                  </div>
                  <span class="record-status">{{ record.status }}</span>
                </button>
              </div>
              <div v-else class="panel-empty">暂无关联病历。</div>
            </div>
          </div>
        </div>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { getConversations } from '../api/conversations'
import { getDiagnosisContext, submitDiagnosisAgentFeedback } from '../api/diagnosis'
import { renderMarkdownToSafeHtml } from '../utils/markdown'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const loadError = ref('')
const conversations = ref([])
const selectedConversationId = ref(null)
const diagnosisContext = ref(null)

const STATUS_LABELS = {
  pending: '待处理',
  active: '进行中',
  paused: '已暂停',
  completed: '已完成',
  cancelled: '已取消'
}

const DIFFICULTY_LABELS = {
  basic: '基础诊断',
  intermediate: '多专科会诊',
  advanced: 'MDT 协作',
  urgent: '紧急风险'
}

const URGENCY_LABELS = {
  low: '低风险',
  normal: '常规',
  medium: '中风险',
  high: '高风险',
  urgent: '紧急'
}

const PROFILE_LABELS = {
  birth_date: '出生日期',
  age: '年龄',
  gender: '性别',
  height_cm: '身高(cm)',
  weight_kg: '体重(kg)',
  past_history: '既往史',
  allergies: '过敏史',
  long_term_medications: '长期用药',
  chronic_diseases: '慢病',
  family_history: '家族史',
  surgery_history: '手术史',
  pregnancy_status: '妊娠/哺乳状态'
}

const INTAKE_LABELS = {
  main_symptom: '主要症状',
  duration: '持续时间',
  accompanying_symptoms: '伴随症状',
  pain_location: '疼痛部位',
  pain_level: '疼痛程度',
  fever: '发热情况',
  recent_medication: '近期用药',
  red_flag_notes: '风险提示'
}

const CHECKLIST_LABELS = {
  observe: '观察事项',
  exams: '建议检查',
  when_to_seek_care: '何时就医',
  lifestyle: '生活建议'
}

const conversationOptions = computed(() => (
  conversations.value.map((conv) => ({
    value: conv.id,
    label: `${conv.patient_name || '未命名患者'} - ${conv.chief_complaint || conv.title || '未命名会话'}`
  }))
))

const triageInfo = computed(() => diagnosisContext.value?.triage || diagnosisContext.value?.latest_diagnosis?.triage || null)
const triageDepartment = computed(() => triageInfo.value?.department_name || triageInfo.value?.department || '')
const triageUrgency = computed(() => URGENCY_LABELS[triageInfo.value?.urgency] || triageInfo.value?.urgency || '')
const urgencyClass = computed(() => {
  const urgency = triageInfo.value?.urgency
  return urgency ? `urgency-${urgency}` : ''
})
const redFlags = computed(() => diagnosisContext.value?.latest_diagnosis?.red_flags || [])
const isUrgent = computed(() => diagnosisContext.value?.latest_diagnosis?.difficulty === 'urgent')
const kgContext = computed(() => diagnosisContext.value?.latest_diagnosis?.kg_context || null)
const kgSummary = computed(() => kgContext.value?.summary || '')
const kgGroups = computed(() => (
  (kgContext.value?.groups || []).map((group) => ({
    ...group,
    display_items: (group.items || []).map((item) => {
      const label = item.relation_label || group.title
      const target = item.target || ''
      return {
        ...item,
        display_text: `${label}：${target}`.trim()
      }
    })
  }))
))
const hasAge = computed(() => diagnosisContext.value?.patient?.age !== null && diagnosisContext.value?.patient?.age !== undefined)

const actionChecklistSections = computed(() => {
  const checklist = diagnosisContext.value?.latest_diagnosis?.action_checklist || {}
  return Object.entries(CHECKLIST_LABELS)
    .map(([key, title]) => ({
      key,
      title,
      items: Array.isArray(checklist[key]) ? checklist[key] : []
    }))
    .filter((section) => section.items.length > 0)
})

const healthProfileItems = computed(() => formatKeyValueItems(diagnosisContext.value?.health_profile || {}, PROFILE_LABELS))
const structuredIntakeItems = computed(() => formatKeyValueItems(diagnosisContext.value?.structured_intake || {}, INTAKE_LABELS))

const analysisCards = computed(() => {
  const diagnosis = diagnosisContext.value?.latest_diagnosis
  if (!diagnosis) return []

  const cards = []
  if (diagnosis.team_recruitment) {
    cards.push({ key: 'team-recruitment', title: '团队招募', type: 'text', content: diagnosis.team_recruitment })
  }
  if (diagnosis.expert_opinions?.length) {
    cards.push({ key: 'expert-opinions', title: '专家意见', type: 'opinions', content: diagnosis.expert_opinions })
  }
  if (diagnosis.mdt_plan) {
    cards.push({ key: 'mdt-plan', title: 'MDT 方案', type: 'text', content: diagnosis.mdt_plan })
  }
  if (diagnosis.team_reports?.length) {
    cards.push(...diagnosis.team_reports.map((report, index) => ({
      key: `team-report-${index}`,
      title: report.group || `团队报告 ${index + 1}`,
      type: 'markdown',
      content: report.report || ''
    })))
  }
  return cards
})

onMounted(async () => {
  await loadConversations()
  await applyRouteConversation()
})

watch(
  () => [route.query.conversation_id, route.query.id],
  async () => {
    await applyRouteConversation()
  }
)

const loadConversations = async () => {
  try {
    const response = await getConversations({ page: 1, page_size: 100 })
    conversations.value = Array.isArray(response) ? response : (response?.items || [])
  } catch (error) {
    loadError.value = '会话列表加载失败，请稍后重试。'
  }
}

const getRouteConversationId = () => {
  const rawId = route.query.conversation_id || route.query.id
  const value = Array.isArray(rawId) ? rawId[0] : rawId
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : null
}

const applyRouteConversation = async () => {
  const conversationId = getRouteConversationId()
  if (!conversationId) return
  if (selectedConversationId.value === conversationId && diagnosisContext.value) return
  selectedConversationId.value = conversationId
  await loadDiagnosisContext(conversationId)
}

const handleConversationChange = async (conversationId) => {
  if (!conversationId) {
    selectedConversationId.value = null
    diagnosisContext.value = null
    loadError.value = ''
    await router.replace({ path: '/diagnosis' })
    return
  }

  await router.replace({
    path: '/diagnosis',
    query: { conversation_id: String(conversationId) }
  })
  await loadDiagnosisContext(conversationId)
}

const loadDiagnosisContext = async (conversationId = selectedConversationId.value) => {
  if (!conversationId) return
  loading.value = true
  loadError.value = ''
  try {
    diagnosisContext.value = await getDiagnosisContext(conversationId)
  } catch (error) {
    diagnosisContext.value = null
    loadError.value = error?.response?.status === 403
      ? '当前账号无权查看该会话的诊断上下文。'
      : '诊断上下文加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

const submitAgentFeedback = async (feedbackType) => {
  if (!selectedConversationId.value || !diagnosisContext.value?.latest_diagnosis) return
  try {
    await submitDiagnosisAgentFeedback(selectedConversationId.value, {
      feedback_type: feedbackType,
      message_id: diagnosisContext.value.latest_diagnosis.message_id,
      comment: ''
    })
    message.success('Agent 反馈已记录')
  } catch (error) {
    message.error('Agent 反馈保存失败')
  }
}

const formatKeyValueItems = (source, labels) => (
  Object.entries(source || {})
    .filter(([, value]) => hasDisplayValue(value))
    .map(([key, value]) => ({
      key,
      label: labels[key] || key,
      value: formatValue(value)
    }))
)

const hasDisplayValue = (value) => {
  if (value === null || value === undefined) return false
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value).length > 0
  return String(value).trim() !== ''
}

const formatValue = (value) => {
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, item]) => `${key}: ${item}`)
      .join('；')
  }
  return String(value)
}

const statusLabel = (status) => STATUS_LABELS[status] || status || '未知状态'
const difficultyLabel = (difficulty) => DIFFICULTY_LABELS[difficulty] || difficulty
const renderDiagnosisHtml = (text) => renderMarkdownToSafeHtml(text || '暂无内容')
const truncateText = (text, maxLength = 260) => {
  const normalized = String(text || '').trim()
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength)}...` : normalized
}

const formatDateTime = (value) => {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN')
}

const openConversationDetail = () => {
  if (!selectedConversationId.value) return
  router.push({ path: '/conversations', query: { id: String(selectedConversationId.value) } })
}

const openRecordWorkspace = () => {
  if (!selectedConversationId.value) return
  router.push({ path: '/records', query: { conversation_id: String(selectedConversationId.value) } })
}

const openRecord = (recordId) => {
  router.push({ path: '/records', query: { id: String(recordId) } })
}
</script>

<style scoped>
.diagnosis-page {
  display: grid;
  gap: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.empty-state {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: var(--c-text-muted);
  text-align: center;
}

.empty-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--c-primary);
  background: rgba(34, 211, 238, 0.08);
}

.empty-icon.warn {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.08);
}

.urgent-banner {
  padding: 18px 22px;
  border: 1px solid rgba(248, 113, 113, 0.24);
  background:
    linear-gradient(135deg, rgba(127, 29, 29, 0.28), rgba(15, 23, 42, 0.94)),
    radial-gradient(circle at top right, rgba(248, 113, 113, 0.24), transparent 45%);
}

.urgent-title {
  font-size: 14px;
  font-weight: 700;
  color: #fecaca;
  margin-bottom: 8px;
}

.urgent-text {
  color: #fca5a5;
  line-height: 1.75;
  font-size: 13px;
}

.hero-card {
  padding: 22px;
  display: grid;
  gap: 18px;
}

.hero-main {
  display: flex;
  justify-content: space-between;
  gap: 24px;
}

.hero-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--c-text);
}

.hero-sub {
  margin-top: 6px;
  color: var(--c-text-sec);
  font-size: 14px;
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.meta-chip {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--c-text-sec);
  font-size: 12px;
  border: 1px solid var(--c-border-subtle);
}

.meta-chip.accent {
  color: var(--c-primary);
  border-color: var(--c-primary-border);
}

.meta-chip.urgency-high,
.meta-chip.urgency-urgent {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.28);
  background: rgba(248, 113, 113, 0.1);
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.complaint-block {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
}

.block-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-text-muted);
  margin-bottom: 10px;
}

.block-text {
  font-size: 15px;
  color: var(--c-text);
  line-height: 1.75;
}

.micro-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.micro-card {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid var(--c-border-subtle);
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    radial-gradient(circle at top right, rgba(34, 211, 238, 0.14), transparent 55%);
}

.micro-label {
  color: var(--c-text-muted);
  font-size: 12px;
}

.micro-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 700;
  color: var(--c-text);
}

.diag-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
  gap: 18px;
}

.main-col,
.side-col {
  display: grid;
  gap: 18px;
  align-content: start;
}

.panel-card {
  overflow: hidden;
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

.panel-label.danger {
  color: #fca5a5;
}

.panel-hint {
  font-size: 12px;
  color: var(--c-text-muted);
}

.panel-empty {
  padding: 22px 18px;
  color: var(--c-text-muted);
  font-size: 13px;
}

.rich-content {
  padding: 18px;
  color: var(--c-text-sec);
  line-height: 1.8;
}

.rich-content.compact {
  padding: 0;
}

.rich-content :deep(p:first-child) {
  margin-top: 0;
}

.rich-content :deep(p:last-child) {
  margin-bottom: 0;
}

.flag-list,
.report-list,
.analysis-list,
.record-list {
  display: grid;
  gap: 12px;
  padding: 16px 18px 18px;
}

.flag-item,
.report-item,
.analysis-card {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
}

.flag-name,
.report-name,
.analysis-card-title,
.record-title,
.opinion-role {
  font-size: 13px;
  font-weight: 700;
  color: var(--c-text);
}

.flag-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.flag-tag {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: #fecaca;
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.28);
}

.checklist-grid,
.kv-grid {
  display: grid;
  gap: 12px;
  padding: 16px 18px 18px;
}

.checklist-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.kv-grid.compact {
  grid-template-columns: 1fr;
}

.checklist-section,
.kv-item,
.kg-group-card {
  padding: 14px;
  border: 1px solid var(--c-border-subtle);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
}

.checklist-title,
.kv-label,
.kg-group-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 8px;
}

.checklist-list {
  margin: 0;
  padding-left: 18px;
  color: var(--c-text-sec);
  line-height: 1.7;
  font-size: 13px;
}

.kv-value,
.analysis-text,
.report-text,
.opinion-text {
  color: var(--c-text-sec);
  line-height: 1.75;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}

.report-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.report-type,
.record-status {
  font-size: 11px;
  color: var(--c-primary);
  border: 1px solid var(--c-primary-border);
  background: rgba(34, 211, 238, 0.08);
  padding: 3px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.analysis-card-title {
  margin-bottom: 10px;
}

.opinion-list {
  display: grid;
  gap: 10px;
}

.opinion-item {
  padding: 12px;
  border-radius: 12px;
  background: rgba(8, 15, 28, 0.42);
  border: 1px solid var(--c-border-subtle);
}

.opinion-role {
  margin-bottom: 6px;
}

.kg-summary {
  padding: 0 18px 12px;
  color: var(--c-text-sec);
  font-size: 13px;
  line-height: 1.75;
}

.kg-group-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 0 18px 18px;
}

.kg-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kg-chip {
  padding: 5px 9px;
  border-radius: 999px;
  border: 1px solid rgba(34, 211, 238, 0.16);
  background: rgba(34, 211, 238, 0.06);
  color: var(--c-text-sec);
  font-size: 12px;
}

.record-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--transition), background var(--transition);
}

.record-item:hover {
  border-color: var(--c-primary-border);
  background: rgba(34, 211, 238, 0.04);
}

.record-time {
  margin-top: 6px;
  font-size: 12px;
  color: var(--c-text-muted);
}

.ghost-btn {
  height: 38px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--c-text-sec);
  cursor: pointer;
  transition: all var(--transition);
  font-family: var(--f-body);
}

.ghost-btn:hover {
  border-color: var(--c-primary-border);
  color: var(--c-text);
}

.ghost-btn.primary {
  color: #081321;
  border-color: transparent;
  background: linear-gradient(135deg, #38bdf8, #67e8f9);
}

@media (max-width: 1280px) {
  .diag-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .hero-main {
    flex-direction: column;
  }

  .hero-actions {
    flex-wrap: wrap;
  }

  .micro-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .kg-group-grid,
  .checklist-grid {
    grid-template-columns: 1fr;
  }
}
</style>
