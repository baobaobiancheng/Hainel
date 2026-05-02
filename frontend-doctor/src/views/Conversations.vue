<template>
  <div class="page-wrap">
    <!-- Header -->
    <div class="page-header">
      <div>
        <div class="section-label">CONVERSATION CENTER</div>
        <h1 class="page-title-text">会话 <span>管理</span></h1>
      </div>
      <div class="header-actions">
        <a-select
          v-model:value="filterStatus"
          style="width: 130px"
          @change="handleFilterChange"
        >
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option value="active">进行中</a-select-option>
          <a-select-option value="pending">待处理</a-select-option>
          <a-select-option value="paused">已暂停</a-select-option>
          <a-select-option value="completed">已完成</a-select-option>
          <a-select-option value="cancelled">已取消</a-select-option>
        </a-select>
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索患者姓名"
          style="width: 220px"
          @search="handleFilterChange"
          allow-clear
        />
      </div>
    </div>

    <!-- Table -->
    <div class="table-card glass-card">
      <a-table
        :columns="columns"
        :data-source="conversations"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
        :scroll="{ x: 1000 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'id'">
            <span class="mono id-text">#{{ record.id }}</span>
          </template>
          <template v-else-if="column.key === 'patient_name'">
            <div class="name-cell">
              <div class="name-avatar">{{ (record.patient_name || '患')[0] }}</div>
              <span>{{ record.patient_name || `患者 #${record.patient_id}` }}</span>
            </div>
          </template>
          <template v-else-if="column.key === 'status'">
            <span class="conv-status-badge" :class="record.status">
              {{ getStatusText(record.status) }}
            </span>
          </template>
          <template v-else-if="column.key === 'complexity_level'">
            <span v-if="record.complexity_level" class="complexity-badge" :class="record.complexity_level">
              {{ getComplexityText(record.complexity_level) }}
            </span>
            <span v-else class="mono" style="color:var(--c-text-muted)">—</span>
          </template>
          <template v-else-if="column.key === 'message_count'">
            <span class="mono badge-num">{{ record.message_count || 0 }}</span>
          </template>
          <template v-else-if="column.key === 'created_at'">
            <span class="mono time-text">{{ formatDate(record.created_at) }}</span>
          </template>
          <template v-else-if="column.key === 'action'">
            <div class="action-btns">
              <button class="act-btn primary" @click="viewDetail(record.id)">查看</button>
              <button class="act-btn accent" @click="viewDiagnosis(record.id)">诊断</button>
              <button
                v-if="record.status === 'active'"
                class="act-btn danger"
                @click="closeConversation(record.id)"
              >关闭</button>
            </div>
          </template>
        </template>
      </a-table>
    </div>

    <!-- Detail Drawer -->
    <a-drawer
      v-model:open="drawerVisible"
      title="会话详情"
      width="820"
      @close="currentConversation = null; messages = []"
    >
      <a-spin :spinning="detailLoading">
        <div v-if="currentConversation">
          <!-- Conversation info -->
          <div class="drawer-conv-header">
            <div class="drawer-conv-meta">
              <div class="conv-meta-row">
                <span class="meta-label">患者</span>
                <span class="meta-val">{{ currentConversation.patient_name || `患者 #${currentConversation.patient_id}` }}</span>
              </div>
              <div class="conv-meta-row">
                <span class="meta-label">状态</span>
                <span class="conv-status-badge" :class="currentConversation.status">
                  {{ getStatusText(currentConversation.status) }}
                </span>
              </div>
              <div class="conv-meta-row">
                <span class="meta-label">主诉</span>
                <span class="meta-val">{{ currentConversation.chief_complaint || '无' }}</span>
              </div>
              <div class="conv-meta-row">
                <span class="meta-label">创建时间</span>
                <span class="meta-val mono">{{ formatDate(currentConversation.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- Patient-side AI context -->
          <div v-if="hasConsultationContext" class="context-panel">
            <div class="messages-header">
              <span class="section-label">患者上下文</span>
              <span class="msg-count mono">AI TRIAGE</span>
            </div>

            <div class="context-grid">
              <div v-if="consultationContext.triage" class="context-card triage-card">
                <div class="context-title-row">
                  <span class="context-title">分诊建议</span>
                  <span class="context-badge">{{ getUrgencyText(consultationContext.triage.urgency) }}</span>
                </div>
                <div class="triage-main">
                  {{ getTriageDepartment(consultationContext.triage) }}
                  <span v-if="consultationContext.triage.confidence" class="mono confidence-inline">
                    {{ formatConfidence(consultationContext.triage.confidence) }}
                  </span>
                </div>
                <p v-if="consultationContext.triage.reason" class="context-desc">
                  {{ consultationContext.triage.reason }}
                </p>
              </div>

              <div v-if="structuredIntakeItems.length" class="context-card">
                <div class="context-title">结构化问诊</div>
                <div class="context-kv-list">
                  <div v-for="item in structuredIntakeItems" :key="item.key" class="context-kv">
                    <span class="context-key">{{ item.label }}</span>
                    <span class="context-val">{{ item.value }}</span>
                  </div>
                </div>
              </div>

              <div v-if="consultationContext.linkedReports.length" class="context-card report-card">
                <div class="context-title">关联报告 / OCR</div>
                <div
                  v-for="report in consultationContext.linkedReports"
                  :key="report.message_id || report.file_name"
                  class="report-item"
                >
                  <div class="report-name">{{ report.file_name || report.report_type || '未命名报告' }}</div>
                  <div class="report-meta">
                    {{ report.report_type || report.file_type || '检查报告' }}
                  </div>
                  <p v-if="report.ocr_text" class="report-ocr">{{ truncateText(report.ocr_text, 120) }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Messages -->
          <div class="messages-header">
            <span class="section-label">消息记录</span>
            <span class="msg-count mono">{{ messages.length }} 条</span>
          </div>

          <div class="messages-container">
            <a-empty v-if="!messages.length" :image="null" description="暂无消息记录" style="padding:40px" />
            <div v-else class="messages-list">
              <div
                class="msg-bubble"
                v-for="item in messages"
                :key="item.id"
                :class="`role-${normalizeRole(item.role)}`"
              >
                <div class="msg-avatar" :style="{ background: getRoleGradient(item.role) }">
                  {{ getRoleAvatar(item.role) }}
                </div>
                <div class="msg-content-wrap">
                  <div class="msg-header-row">
                    <span class="msg-role-name">{{ getRoleName(item.role) }}</span>
                    <span class="msg-time mono">{{ formatDate(item.created_at) }}</span>
                  </div>
                  <div v-if="isImageMessage(item)" class="msg-image-card">
                    <img
                      class="msg-image"
                      :src="getMessageFileUrl(item.file_url)"
                      :alt="item.file_name || '症状图片'"
                      @click="previewMessageImage(item)"
                    />
                    <span class="msg-file-name">{{ item.file_name || item.content || '症状图片' }}</span>
                  </div>
                  <div
                    v-else-if="isMarkdownAssistantMessage(item)"
                    class="msg-text msg-text-md"
                    v-html="renderAssistantMarkdown(item.content)"
                  />
                  <div v-else class="msg-text">{{ item.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  getConversations,
  getConversationDetail,
  getConversationMessages,
  updateConversationStatus
} from '../api/conversations'
import { renderMarkdownToSafeHtml } from '../utils/markdown'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const detailLoading = ref(false)
const searchText = ref('')
const filterStatus = ref('')
const conversations = ref([])
const currentConversation = ref(null)
const messages = ref([])
const drawerVisible = ref(false)

const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条记录`
})

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '患者姓名', key: 'patient_name', ellipsis: true },
  { title: '主诉', dataIndex: 'chief_complaint', key: 'chief_complaint', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '复杂度', dataIndex: 'complexity_level', key: 'complexity_level', width: 100 },
  { title: '消息数', dataIndex: 'message_count', key: 'message_count', width: 90, align: 'center' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' }
]

const consultationContext = computed(() => {
  const metadata = [...messages.value]
    .reverse()
    .map((item) => normalizeMetadata(item.metadata))
    .find((item) => item.triage || item.structured_intake || item.linked_reports?.length)

  return {
    triage: metadata?.triage || null,
    structuredIntake: metadata?.structured_intake || null,
    linkedReports: Array.isArray(metadata?.linked_reports) ? metadata.linked_reports : []
  }
})

const structuredIntakeItems = computed(() => {
  const intake = consultationContext.value.structuredIntake
  if (!intake || typeof intake !== 'object' || Array.isArray(intake)) return []

  return Object.entries(intake)
    .filter(([, value]) => hasDisplayValue(value))
    .map(([key, value]) => ({
      key,
      label: INTAKE_LABELS[key] || key,
      value: formatContextValue(value)
    }))
})

const hasConsultationContext = computed(() => (
  Boolean(consultationContext.value.triage) ||
  structuredIntakeItems.value.length > 0 ||
  consultationContext.value.linkedReports.length > 0
))

onMounted(async () => {
  if (route.query.patient_id) filterStatus.value = ''
  await loadConversations()
  await openRouteConversation()
  window.addEventListener('doctor:new-session', handleNewSession)
})

watch(
  () => route.query.id,
  async () => {
    await openRouteConversation()
  }
)

onUnmounted(() => {
  window.removeEventListener('doctor:new-session', handleNewSession)
})

const loadConversations = async () => {
  loading.value = true
  try {
    const params = { page: pagination.value.current, page_size: pagination.value.pageSize }
    if (filterStatus.value) params.status = filterStatus.value
    if (route.query.patient_id) params.patient_id = route.query.patient_id
    const data = await getConversations(params)
    conversations.value = Array.isArray(data) ? data : (data?.items || [])
    pagination.value.total = Array.isArray(data) ? data.length : (data?.total || 0)
  } catch (error) {
    message.error('加载会话列表失败')
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  pagination.value.current = 1
  loadConversations()
}

const handleTableChange = (pag) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  loadConversations()
}

const handleNewSession = () => {
  loadConversations()
  if (drawerVisible.value && currentConversation.value?.id) {
    viewDetail(currentConversation.value.id)
  }
}

const viewDetail = async (id) => {
  drawerVisible.value = true
  detailLoading.value = true
  currentConversation.value = null
  messages.value = []
  try {
    const [convData, msgData] = await Promise.all([
      getConversationDetail(id),
      getConversationMessages(id, { page: 1, page_size: 100 })
    ])
    const fromList = conversations.value.find((c) => c.id === id)
    currentConversation.value = {
      ...convData,
      patient_name: convData.patient_name ?? fromList?.patient_name ?? null
    }
    messages.value = msgData?.items || []
  } catch (error) {
    message.error('加载会话详情失败')
  } finally {
    detailLoading.value = false
  }
}

const openRouteConversation = async () => {
  const conversationId = getRouteConversationId()
  if (!conversationId || currentConversation.value?.id === conversationId) return
  await viewDetail(conversationId)
}

const getRouteConversationId = () => {
  const rawId = route.query.id
  const value = Array.isArray(rawId) ? rawId[0] : rawId
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : null
}

const viewDiagnosis = (conversationId) => {
  router.push(`/diagnosis?conversation_id=${conversationId}`)
}

const closeConversation = async (id) => {
  try {
    await updateConversationStatus(id, 'cancelled')
    message.success('会话已关闭')
    loadConversations()
  } catch (error) {
    message.error('关闭会话失败')
  }
}

const STATUS_TEXT_MAP = {
  active: '进行中', pending: '待处理', completed: '已完成',
  cancelled: '已取消', paused: '已暂停', closed: '已关闭'
}
const getStatusText = (status) => STATUS_TEXT_MAP[status] || status
const getComplexityColor = (level) => ({ low: 'green', medium: 'orange', high: 'red' }[level] || 'default')
const getComplexityText = (level) => ({ low: '低', medium: '中', high: '高' }[level] || level)

const ROLE_GRADIENT = {
  user: 'linear-gradient(135deg,#0e7490,#0369a1)',
  patient: 'linear-gradient(135deg,#0e7490,#0369a1)',
  doctor: 'linear-gradient(135deg,#065f46,#059669)',
  system: 'linear-gradient(135deg,#581c87,#7c3aed)',
  agent: 'linear-gradient(135deg,#92400e,#d97706)',
  assistant: 'linear-gradient(135deg,#92400e,#d97706)'
}
const normalizeRole = (role) => String(role || '').toLowerCase()
const getRoleName = (role) => ({ user: '患者', patient: '患者', doctor: '医生', system: '系统', agent: '智能体', assistant: '智能体' }[normalizeRole(role)] || role)
const getRoleAvatar = (role) => ({ user: '患', patient: '患', doctor: '医', system: '系', agent: '智', assistant: '智' }[normalizeRole(role)] || '?')
const getRoleGradient = (role) => ROLE_GRADIENT[normalizeRole(role)] || 'linear-gradient(135deg,#374151,#6b7280)'

const INTAKE_LABELS = {
  symptoms: '症状',
  symptom: '症状',
  duration: '持续时间',
  severity: '严重程度',
  onset: '起病情况',
  location: '部位',
  accompanying_symptoms: '伴随症状',
  medical_history: '既往史',
  medication_history: '用药史',
  medications: '用药',
  allergy_history: '过敏史',
  allergies: '过敏史',
  family_history: '家族史',
  lifestyle: '生活方式'
}

const normalizeMetadata = (metadata) => {
  if (!metadata) return {}
  if (typeof metadata === 'object') return metadata
  try {
    return JSON.parse(metadata)
  } catch (error) {
    return {}
  }
}

const hasDisplayValue = (value) => {
  if (value === null || value === undefined || value === '') return false
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value).length > 0
  return true
}

const formatContextValue = (value) => {
  if (Array.isArray(value)) return value.map(formatContextValue).join('、')
  if (typeof value === 'object' && value !== null) return JSON.stringify(value)
  return String(value)
}

const getTriageDepartment = (triage) => triage.department_name || triage.department || '待医生评估'
const getUrgencyText = (urgency) => ({
  emergency: '急诊',
  urgent: '加急',
  normal: '普通',
  low: '低优先级'
}[urgency] || urgency || '未分级')

const formatConfidence = (confidence) => {
  const value = Number(confidence)
  if (!Number.isFinite(value)) return ''
  return `${(value * 100).toFixed(0)}%`
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

const isImageMessage = (item) => String(item.message_type || '').toLowerCase() === 'image' && item.file_url

/** 助手/智能体文本回复按 Markdown 渲染（图片消息仍走图片卡片）。 */
const isMarkdownAssistantMessage = (item) => {
  const r = normalizeRole(item.role)
  const assistantLike = r === 'assistant' || r === 'agent'
  return assistantLike && !isImageMessage(item)
}

const renderAssistantMarkdown = (content) => renderMarkdownToSafeHtml(content)

const getMessageFileUrl = (url) => {
  if (!url) return ''
  if (/^https?:\/\//.test(url)) return url
  return url.startsWith('/api/') ? url : `/api/v1${url.startsWith('/') ? url : `/${url}`}`
}
const previewMessageImage = (item) => {
  const url = getMessageFileUrl(item.file_url)
  if (url) window.open(url, '_blank')
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}
</script>

<style scoped>
.header-actions { display: flex; gap: 10px; align-items: center; }

.table-card {
  border-radius: var(--radius);
  overflow: hidden;
}

/* Cells */
.name-cell { display: flex; align-items: center; gap: 9px; }
.name-avatar {
  width: 28px; height: 28px; border-radius: 8px;
  background: linear-gradient(135deg, #0e7490, #1d4ed8);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.id-text { color: var(--c-text-muted); font-size: 12px; }
.badge-num {
  background: rgba(34,211,238,0.08); color: var(--c-primary);
  padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: 600;
}
.time-text { font-size: 12px; color: var(--c-text-sec); }

/* Status badges */
.conv-status-badge {
  display: inline-block;
  font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 5px; letter-spacing: 0.04em;
}
.conv-status-badge.active { background: rgba(34,211,238,0.1); color: #22d3ee; border: 1px solid rgba(34,211,238,0.2); }
.conv-status-badge.pending { background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.2); }
.conv-status-badge.completed { background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.2); }
.conv-status-badge.cancelled, .conv-status-badge.closed { background: rgba(100,116,139,0.1); color: #64748b; border: 1px solid rgba(100,116,139,0.2); }

/* Complexity */
.complexity-badge {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.04em;
}
.complexity-badge.low { background: rgba(52,211,153,0.1); color: #34d399; }
.complexity-badge.medium { background: rgba(251,191,36,0.1); color: #fbbf24; }
.complexity-badge.high { background: rgba(248,113,113,0.1); color: #f87171; }

/* Action buttons */
.action-btns { display: flex; gap: 5px; }
.act-btn {
  font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px; border: 1px solid; cursor: pointer; transition: all var(--transition);
}
.act-btn.primary { background: rgba(34,211,238,0.08); border-color: rgba(34,211,238,0.18); color: var(--c-primary); }
.act-btn.primary:hover { background: rgba(34,211,238,0.16); }
.act-btn.accent { background: rgba(167,139,250,0.08); border-color: rgba(167,139,250,0.18); color: var(--c-agent); }
.act-btn.accent:hover { background: rgba(167,139,250,0.16); }
.act-btn.danger { background: rgba(248,113,113,0.08); border-color: rgba(248,113,113,0.18); color: var(--c-danger); }
.act-btn.danger:hover { background: rgba(248,113,113,0.16); }
.act-btn.ghost { background: transparent; border-color: var(--c-border); color: var(--c-text-sec); }
.act-btn.ghost:hover { border-color: var(--c-text-sec); color: var(--c-text); }

/* Drawer: Conversation header */
.drawer-conv-header {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  padding: 16px 20px;
  margin-bottom: 24px;
}
.drawer-conv-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.conv-meta-row { display: flex; flex-direction: column; gap: 3px; }
.meta-label { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--c-text-muted); }
.meta-val { font-size: 13px; color: var(--c-text); }

/* Patient context */
.context-panel { margin-bottom: 24px; }
.context-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.context-card {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 14px;
}
.triage-card { border-color: rgba(34,211,238,0.2); }
.context-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.context-title {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 10px;
}
.context-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--c-primary);
  background: rgba(34,211,238,0.08);
  border: 1px solid rgba(34,211,238,0.18);
  border-radius: 999px;
  padding: 2px 8px;
}
.triage-main {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-primary);
  margin-bottom: 8px;
}
.confidence-inline {
  font-size: 12px;
  color: var(--c-text-muted);
  margin-left: 6px;
}
.context-desc {
  margin: 0;
  color: var(--c-text-sec);
  font-size: 12px;
  line-height: 1.6;
}
.context-kv-list { display: flex; flex-direction: column; gap: 8px; }
.context-kv {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 10px;
  font-size: 12px;
}
.context-key { color: var(--c-text-muted); }
.context-val { color: var(--c-text-sec); line-height: 1.5; }
.report-card { display: flex; flex-direction: column; gap: 10px; }
.report-item {
  padding: 10px;
  border-radius: 8px;
  background: var(--c-bg-card);
  border: 1px solid var(--c-border-subtle);
}
.report-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 3px;
}
.report-meta {
  font-size: 11px;
  color: var(--c-primary);
  margin-bottom: 6px;
}
.report-ocr {
  margin: 0;
  color: var(--c-text-sec);
  font-size: 12px;
  line-height: 1.5;
}

/* Messages */
.messages-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.msg-count { font-size: 12px; color: var(--c-text-muted); }
.messages-container {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  max-height: 520px;
  overflow-y: auto;
}
.messages-list { padding: 16px; display: flex; flex-direction: column; gap: 14px; }

.msg-bubble {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.msg-avatar {
  width: 34px; height: 34px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #fff;
  flex-shrink: 0;
}
.msg-content-wrap { flex: 1; min-width: 0; }
.msg-header-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 5px;
}
.msg-role-name { font-size: 12px; font-weight: 700; color: var(--c-text); }
.msg-time { font-size: 11px; color: var(--c-text-muted); }
.msg-text {
  font-size: 13.5px;
  color: var(--c-text-sec);
  line-height: 1.6;
  white-space: pre-wrap;
  background: var(--c-bg-card);
  border: 1px solid var(--c-border-subtle);
  border-radius: 0 10px 10px 10px;
  padding: 10px 14px;
}
.msg-text-md {
  white-space: normal;
  max-width: 100%;
  overflow-wrap: anywhere;
}
.msg-text-md :deep(h1),
.msg-text-md :deep(h2),
.msg-text-md :deep(h3) {
  color: var(--c-text);
  font-weight: 700;
  margin: 0.6em 0 0.35em;
  line-height: 1.35;
}
.msg-text-md :deep(h1) { font-size: 1.05rem; }
.msg-text-md :deep(h2) { font-size: 1rem; }
.msg-text-md :deep(h3) { font-size: 0.95rem; }
.msg-text-md :deep(p) {
  margin: 0.45em 0;
  color: var(--c-text-sec);
}
.msg-text-md :deep(ul),
.msg-text-md :deep(ol) {
  margin: 0.4em 0 0.4em 1.1em;
  padding: 0;
  color: var(--c-text-sec);
}
.msg-text-md :deep(li) { margin: 0.2em 0; }
.msg-text-md :deep(strong) { color: var(--c-text); }
.msg-text-md :deep(code) {
  font-family: var(--f-mono, ui-monospace, monospace);
  font-size: 0.88em;
  background: rgba(0, 0, 0, 0.2);
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
.msg-text-md :deep(pre) {
  margin: 0.5em 0;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12px;
}
.msg-text-md :deep(pre code) {
  background: transparent;
  padding: 0;
}
.msg-text-md :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.25em 0 0.25em 10px;
  border-left: 3px solid rgba(167, 139, 250, 0.45);
  color: var(--c-text-muted);
}
.msg-text-md :deep(a) {
  color: var(--c-primary);
  text-decoration: underline;
}
.msg-bubble.role-patient .msg-text { border-color: rgba(34,211,238,0.1); }
.msg-bubble.role-user .msg-text,
.msg-bubble.role-user .msg-image-card { border-color: rgba(34,211,238,0.1); }
.msg-bubble.role-doctor .msg-text { border-color: rgba(52,211,153,0.1); }
.msg-bubble.role-agent .msg-text,
.msg-bubble.role-assistant .msg-text { border-color: rgba(167,139,250,0.12); }
.msg-bubble.role-system .msg-text { border-color: rgba(100,116,139,0.15); opacity: 0.7; }

.msg-image-card {
  display: inline-flex;
  flex-direction: column;
  gap: 8px;
  max-width: 260px;
  background: var(--c-bg-card);
  border: 1px solid var(--c-border-subtle);
  border-radius: 0 12px 12px 12px;
  padding: 10px;
}

.msg-image {
  max-width: 240px;
  max-height: 220px;
  object-fit: cover;
  border-radius: 8px;
  cursor: pointer;
}

.msg-file-name {
  font-size: 12px;
  color: var(--c-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
