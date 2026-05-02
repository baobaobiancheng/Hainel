<template>
  <div class="page-wrap records-page">
    <div class="page-header">
      <div>
        <div class="section-label">MEDICAL RECORD WORKSPACE</div>
        <h1 class="page-title-text">病历 <span>工作台</span></h1>
      </div>
      <div class="header-actions">
        <div class="status-tabs">
          <button
            v-for="item in statusTabs"
            :key="item.value"
            class="status-tab"
            :class="{ active: filterStatus === item.value }"
            @click="changeStatus(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索主诉 / 病历标题"
          style="width: 240px"
          @search="reloadAll"
          allow-clear
        />
        <button class="create-btn" @click="openCreateWizard">新建病历</button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stats-card">
        <div class="stats-label">草稿</div>
        <div class="stats-value mono">{{ statusSummary.draft || 0 }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">已确认</div>
        <div class="stats-value mono">{{ statusSummary.confirmed || 0 }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">已归档</div>
        <div class="stats-value mono">{{ statusSummary.archived || 0 }}</div>
      </div>
      <div class="stats-card">
        <div class="stats-label">AI 草稿</div>
        <div class="stats-value mono">{{ aiDraftCount }}</div>
      </div>
    </div>

    <div class="workspace-grid">
      <div class="glass-card queue-panel">
        <div class="panel-head">
          <span class="panel-label">病历队列</span>
          <span class="panel-hint">{{ pagination.total }} 条</span>
        </div>
        <a-spin :spinning="loadingList">
          <div v-if="records.length" class="queue-list">
            <button
              v-for="record in records"
              :key="record.id"
              class="queue-item"
              :class="{ active: selectedRecordId === record.id }"
              @click="selectRecord(record)"
            >
              <div class="queue-top">
                <span class="queue-patient">{{ getPatientName(record.patient_id) }}</span>
                <span class="queue-status" :class="`status-${record.status}`">{{ statusLabel(record.status) }}</span>
              </div>
              <div class="queue-title">{{ record.title || record.chief_complaint || '未命名病历' }}</div>
              <div class="queue-sub">{{ record.chief_complaint || '暂无主诉' }}</div>
              <div class="queue-foot mono">
                <span v-if="record.conversation_id">会话 #{{ record.conversation_id }}</span>
                <span>{{ formatDate(record.updated_at || record.created_at) }}</span>
              </div>
            </button>
          </div>
          <div v-else class="panel-empty">当前筛选条件下暂无病历。</div>
        </a-spin>
      </div>

      <div class="glass-card editor-panel">
        <div class="panel-head">
          <div>
            <div class="panel-label">病历编辑区</div>
            <div class="editor-subtitle">
              {{ editorTitle }}
              <span v-if="editorRecordMeta?.metadata?.source === 'ai_draft'" class="source-pill">AI 生成，待医生确认</span>
            </div>
          </div>
          <div class="editor-actions">
            <button class="ghost-btn" @click="resetEditor">清空</button>
            <button class="ghost-btn" :disabled="saving || !editorRecordId" @click="runQualityCheck">AI 质检</button>
            <button v-if="!isReadonlyRecord" class="ghost-btn" :disabled="saving || !editorRecordId" @click="assistRecord">智能补全</button>
            <button v-if="!isReadonlyRecord" class="ghost-btn" :disabled="saving" @click="saveDraft">保存草稿</button>
            <button
              v-if="!isReadonlyRecord"
              class="primary-btn"
              :disabled="saving"
              @click="confirmRecord"
            >
              确认病历
            </button>
            <button
              v-if="showArchiveAction"
              class="primary-btn archive-btn"
              :disabled="saving"
              @click="archiveRecord(editorRecordMeta.id)"
            >
              {{ archiveActionLabel }}
            </button>
          </div>
        </div>

        <div class="editor-scroll">
          <div v-if="!editorForm.patient_id && !editorForm.conversation_id && !editorRecordId" class="panel-empty large">
            从诊断页生成病历草稿，或从上方“新建病历”进入创建向导。
          </div>

          <a-form v-else layout="vertical" class="record-form" :disabled="isReadonlyRecord">
            <div v-if="showArchiveAction" class="record-status-banner">
              <div>
                <div class="record-status-banner-title">{{ archiveBannerTitle }}</div>
                <div class="record-status-banner-text">{{ archiveBannerText }}</div>
              </div>
              <button
                class="primary-btn archive-btn inline"
                :disabled="saving"
                @click.prevent="archiveRecord(editorRecordMeta.id)"
              >
                {{ archiveActionLabel }}
              </button>
            </div>

            <div class="form-grid two">
              <a-form-item label="病历标题" required>
                <a-input v-model:value="editorForm.title" placeholder="请输入病历标题" />
              </a-form-item>
              <a-form-item label="患者">
                <a-input :value="editorPatientLabel" disabled />
              </a-form-item>
            </div>

            <div class="form-grid two">
              <a-form-item label="关联会话">
                <a-input :value="editorConversationLabel" disabled />
              </a-form-item>
              <a-form-item label="当前状态">
                <a-input :value="statusLabel(editorRecordMeta?.status || 'draft')" disabled />
              </a-form-item>
            </div>

            <a-form-item label="主诉" required>
              <a-textarea v-model:value="editorForm.chief_complaint" :rows="3" placeholder="请输入主诉" />
            </a-form-item>

            <a-form-item label="现病史">
              <a-textarea v-model:value="editorForm.present_illness" :rows="4" placeholder="请输入现病史" />
            </a-form-item>

            <div class="form-grid two">
              <a-form-item label="既往史">
                <a-textarea v-model:value="editorForm.past_history" :rows="4" placeholder="请输入既往史" />
              </a-form-item>
              <a-form-item label="体格检查">
                <a-textarea v-model:value="editorForm.physical_examination" :rows="4" placeholder="请输入体格检查" />
              </a-form-item>
            </div>

            <a-form-item label="辅助检查">
              <a-textarea v-model:value="editorForm.auxiliary_examination" :rows="4" placeholder="请输入辅助检查摘要" />
            </a-form-item>

            <a-form-item label="初步诊断">
              <a-textarea v-model:value="editorForm.preliminary_diagnosis" :rows="4" placeholder="请输入初步诊断" />
            </a-form-item>

            <div class="form-grid two">
              <a-form-item label="处理方案">
                <a-textarea v-model:value="editorForm.treatment_plan" :rows="5" placeholder="请输入处理方案" />
              </a-form-item>
              <a-form-item label="医嘱 / 随访建议">
                <a-textarea v-model:value="editorForm.medical_advice" :rows="5" placeholder="请输入医嘱" />
              </a-form-item>
            </div>
          </a-form>
        </div>

        <div v-if="editorRecordMeta" class="editor-footer">
          <button
            v-if="editorRecordMeta.status === 'draft' && editorRecordMeta.id"
            class="footer-btn danger"
            @click="removeRecord(editorRecordMeta.id)"
          >
            删除草稿
          </button>
        </div>
      </div>

      <div class="glass-card context-panel">
        <div class="panel-head">
          <span class="panel-label">患者与会话上下文</span>
        </div>
        <div class="context-scroll">
          <div class="context-block">
            <div class="context-title">患者摘要</div>
            <div v-if="patientSummary" class="context-kv-list">
              <div class="context-kv">
                <span class="context-key">患者</span>
                <span class="context-val">{{ patientSummary.patient.full_name || patientSummary.patient.username }}</span>
              </div>
              <div class="context-kv">
                <span class="context-key">会话数</span>
                <span class="context-val">{{ patientSummary.conversation_stats.total }}</span>
              </div>
              <div class="context-kv">
                <span class="context-key">病历数</span>
                <span class="context-val">{{ patientSummary.medical_record_stats.total }}</span>
              </div>
              <div
                v-for="item in patientHealthProfile"
                :key="item.key"
                class="context-kv"
              >
                <span class="context-key">{{ item.label }}</span>
                <span class="context-val">{{ item.value }}</span>
              </div>
            </div>
            <div v-else class="context-empty">暂无患者摘要。</div>
          </div>

          <div class="context-block">
            <div class="context-title">诊断上下文</div>
            <template v-if="diagnosisContext">
              <div class="context-highlight">{{ diagnosisContext.conversation.chief_complaint || '暂无主诉' }}</div>
              <div v-if="diagnosisContext.triage" class="triage-chip">
                {{ diagnosisContext.triage.department_name || diagnosisContext.triage.department || '待医生评估' }}
                <span>{{ diagnosisContext.triage.urgency || 'normal' }}</span>
              </div>
              <div v-if="diagnosisContext.latest_diagnosis?.content" class="context-text">
                {{ truncateText(diagnosisContext.latest_diagnosis.content, 240) }}
              </div>
              <div v-if="diagnosisContext.linked_reports?.length" class="report-mini-list">
                <div
                  v-for="report in diagnosisContext.linked_reports.slice(0, 3)"
                  :key="report.message_id || report.file_name"
                  class="report-mini-item"
                >
                  <div class="report-mini-name">{{ report.file_name || report.report_type || '未命名报告' }}</div>
                  <div class="report-mini-text">{{ truncateText(report.ocr_text || '', 110) || '暂无 OCR 文本' }}</div>
                </div>
              </div>
            </template>
            <div v-else class="context-empty">暂无会话诊断上下文。</div>
          </div>

          <div class="context-block">
            <div class="context-title">草稿来源说明</div>
            <div v-if="editorRecordMeta?.metadata?.source === 'ai_draft'" class="context-text">
              该草稿由 AI 基于当前会话的结构化问诊、报告 OCR、分诊结果和诊断内容预填生成。医生可修改全部字段，保存草稿不会自动确认。
            </div>
            <div v-else class="context-empty">当前病历不是 AI 预填草稿。</div>
          </div>
          <div v-if="editorRecordId" class="context-block">
            <div class="context-title">Agent 反馈</div>
            <div class="feedback-actions">
              <button class="feedback-btn" @click="submitAgentFeedback('useful')">有用</button>
              <button class="feedback-btn" @click="submitAgentFeedback('inaccurate')">不准确</button>
              <button class="feedback-btn danger" @click="submitAgentFeedback('missed_risk')">遗漏风险</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <a-modal
      v-model:open="createVisible"
      title="新建病历"
      @ok="startCreateWorkflow"
      :confirm-loading="creating"
      ok-text="进入编辑"
    >
      <a-form layout="vertical">
        <a-form-item label="患者" required>
          <a-select
            v-model:value="createForm.patient_id"
            show-search
            placeholder="请选择患者"
            option-filter-prop="label"
            :options="patientOptions"
            @change="handleCreatePatientChange"
          />
        </a-form-item>
        <a-form-item label="关联会话">
          <a-select
            v-model:value="createForm.conversation_id"
            allow-clear
            show-search
            placeholder="如有会话，优先选择以生成 AI 草稿"
            option-filter-prop="label"
            :options="createConversationOptions"
          />
        </a-form-item>
        <div class="wizard-tip">
          选择会话后会自动预填主诉、问诊摘要、诊断内容和报告摘要；不选会话则创建绑定患者的空白草稿。
        </div>
      </a-form>
    </a-modal>

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  archiveMedicalRecord,
  assistMedicalRecord,
  createMedicalRecord,
  deleteMedicalRecord,
  getMedicalRecordDetail,
  getMedicalRecordDraft,
  getMedicalRecords,
  qualityCheckMedicalRecord,
  submitMedicalRecordAgentFeedback,
  updateMedicalRecord,
  updateMedicalRecordStatus
} from '../api/medicalRecords'
import { getConversations } from '../api/conversations'
import { getPatients, getPatientDetail } from '../api/patients'
import { getDiagnosisContext } from '../api/diagnosis'

const route = useRoute()
const router = useRouter()

const loadingList = ref(false)
const saving = ref(false)
const creating = ref(false)
const createVisible = ref(false)

const filterStatus = ref('draft')
const searchText = ref('')
const records = ref([])
const pagination = ref({ total: 0 })
const statusSummary = ref({ draft: 0, confirmed: 0, reviewed: 0, archived: 0 })

const patients = ref([])
const patientSummary = ref(null)
const diagnosisContext = ref(null)
const patientConversations = ref([])

const selectedRecordId = ref(null)
const editorRecordId = ref(null)
const editorRecordMeta = ref(null)
const editorForm = ref(createEmptyEditor())

const createForm = ref({ patient_id: null, conversation_id: null })
const statusTabs = [
  { value: 'draft', label: '草稿' },
  { value: 'confirmed', label: '已确认' },
  { value: 'reviewed', label: '已审核（历史）' },
  { value: 'archived', label: '已归档' }
]

const patientMap = computed(() => Object.fromEntries(
  patients.value.map((item) => [item.id, item])
))

const patientOptions = computed(() => patients.value.map((patient) => ({
  value: patient.id,
  label: `${patient.full_name || patient.username} (#${patient.id})`
})))

const createConversationOptions = computed(() => patientConversations.value.map((item) => ({
  value: item.id,
  label: `${item.chief_complaint || item.title || `会话 #${item.id}`}`
})))

const editorPatientLabel = computed(() => {
  if (!editorForm.value.patient_id) return '未绑定患者'
  return getPatientName(editorForm.value.patient_id)
})

const editorConversationLabel = computed(() => {
  if (!editorForm.value.conversation_id) return '无关联会话'
  const match = patientConversations.value.find((item) => item.id === editorForm.value.conversation_id)
  return match?.chief_complaint || match?.title || `会话 #${editorForm.value.conversation_id}`
})

const editorTitle = computed(() => {
  if (editorRecordId.value) return `病历 #${editorRecordId.value}`
  if (editorForm.value.conversation_id) return '新建 AI 草稿'
  if (editorForm.value.patient_id) return '新建空白草稿'
  return '病历编辑区'
})

const patientHealthProfile = computed(() => {
  const profile = patientSummary.value?.patient?.health_profile || {}
  return Object.entries(profile)
    .filter(([, value]) => value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length))
    .slice(0, 6)
    .map(([key, value]) => ({
      key,
      label: PROFILE_LABELS[key] || key,
      value: Array.isArray(value) ? value.join('、') : String(value)
    }))
})

const aiDraftCount = computed(() => records.value.filter((record) => record.metadata?.source === 'ai_draft').length)
const isReadonlyRecord = computed(() => ['confirmed', 'reviewed', 'archived'].includes(editorRecordMeta.value?.status))
const showArchiveAction = computed(() => ['confirmed', 'reviewed'].includes(editorRecordMeta.value?.status))
const archiveActionLabel = computed(() => editorRecordMeta.value?.status === 'reviewed' ? '归档历史已审核病历' : '归档已确认病历')
const archiveBannerTitle = computed(() => editorRecordMeta.value?.status === 'reviewed' ? '历史已审核病历可直接归档' : '当前病历已确认，可直接归档')
const archiveBannerText = computed(() => editorRecordMeta.value?.status === 'reviewed'
  ? '该病历处于历史已审核状态，归档后将转为只读归档记录。'
  : '接诊医生已完成确认，不再进入待审核队列；归档后将转为只读记录。')

onMounted(async () => {
  await Promise.all([loadPatients(), loadStatusSummary(), loadRecords()])
  await handleInitialRoute()
})

function createEmptyEditor () {
  return {
    patient_id: null,
    conversation_id: null,
    title: '',
    chief_complaint: '',
    present_illness: '',
    past_history: '',
    physical_examination: '',
    auxiliary_examination: '',
    preliminary_diagnosis: '',
    treatment_plan: '',
    medical_advice: '',
    follow_up: '',
    metadata: {}
  }
}

async function loadPatients () {
  try {
    const response = await getPatients({ page: 1, page_size: 100 })
    patients.value = Array.isArray(response) ? response : (response?.items || [])
  } catch (error) {
    message.error('患者列表加载失败')
  }
}

async function loadStatusSummary () {
  const statuses = ['draft', 'confirmed', 'reviewed', 'archived']
  try {
    const responses = await Promise.all(
      statuses.map((status) => getMedicalRecords({ status, page: 1, page_size: 1 }))
    )
    statusSummary.value = statuses.reduce((acc, status, index) => {
      acc[status] = responses[index]?.total || 0
      return acc
    }, {})
  } catch (error) {
    statusSummary.value = { draft: 0, confirmed: 0, reviewed: 0, archived: 0 }
  }
}

async function loadRecords () {
  loadingList.value = true
  try {
    const params = {
      page: 1,
      page_size: 100,
      status: filterStatus.value,
      search: searchText.value.trim() || undefined
    }
    const response = await getMedicalRecords(params)
    records.value = response?.items || []
    pagination.value.total = response?.total || records.value.length
    if (!selectedRecordId.value && records.value.length) {
      await selectRecord(records.value[0])
    }
  } catch (error) {
    message.error('病历队列加载失败')
  } finally {
    loadingList.value = false
  }
}

async function reloadAll () {
  await Promise.all([loadStatusSummary(), loadRecords()])
}

async function changeStatus (status) {
  filterStatus.value = status
  selectedRecordId.value = null
  await loadRecords()
}

async function handleInitialRoute () {
  const routeRecordId = parseNumeric(route.query.id)
  const routeConversationId = parseNumeric(route.query.conversation_id)
  const routePatientId = parseNumeric(route.query.patient_id)
  const shouldCreate = route.query.create === '1'

  if (routeRecordId) {
    await openRecordById(routeRecordId)
    return
  }
  if (routeConversationId) {
    await startDraftFromConversation(routeConversationId)
    return
  }
  if (routePatientId && shouldCreate) {
    await preloadCreateWizard(routePatientId)
  }
}

async function selectRecord (record) {
  selectedRecordId.value = record.id
  await openRecordById(record.id, record)
}

async function openRecordById (recordId, listRecord = null) {
  try {
    const detail = await getMedicalRecordDetail(recordId)
    editorRecordId.value = detail.id
    editorRecordMeta.value = { ...detail, ...(listRecord || {}) }
    editorForm.value = mapRecordToEditor(detail)
    await loadContextForEditor(detail.patient_id, detail.conversation_id)
  } catch (error) {
    message.error('病历详情加载失败')
  }
}

async function loadContextForEditor (patientId, conversationId) {
  patientSummary.value = null
  diagnosisContext.value = null
  patientConversations.value = []

  const tasks = []
  if (patientId) {
    tasks.push(
      getPatientDetail(patientId).then((response) => {
        patientSummary.value = response
      })
    )
    tasks.push(
      getConversations({ patient_id: patientId, page: 1, page_size: 30 }).then((response) => {
        patientConversations.value = Array.isArray(response) ? response : (response?.items || [])
      })
    )
  }
  if (conversationId) {
    tasks.push(
      getDiagnosisContext(conversationId).then((response) => {
        diagnosisContext.value = response
      })
    )
  }
  await Promise.allSettled(tasks)
}

async function openCreateWizard () {
  createForm.value = { patient_id: null, conversation_id: null }
  patientConversations.value = []
  createVisible.value = true
}

async function preloadCreateWizard (patientId) {
  createForm.value = { patient_id: patientId, conversation_id: null }
  createVisible.value = true
  await handleCreatePatientChange(patientId)
  if (patientConversations.value.length === 1) {
    createForm.value.conversation_id = patientConversations.value[0].id
  }
}

async function handleCreatePatientChange (patientId) {
  createForm.value.conversation_id = null
  if (!patientId) {
    patientConversations.value = []
    return
  }
  try {
    const response = await getConversations({ patient_id: patientId, page: 1, page_size: 30 })
    patientConversations.value = Array.isArray(response) ? response : (response?.items || [])
  } catch (error) {
    patientConversations.value = []
  }
}

async function startCreateWorkflow () {
  if (!createForm.value.patient_id) {
    message.warning('请先选择患者')
    return
  }
  creating.value = true
  try {
    if (createForm.value.conversation_id) {
      await startDraftFromConversation(createForm.value.conversation_id)
    } else {
      editorRecordId.value = null
      editorRecordMeta.value = {
        status: 'draft',
        metadata: {}
      }
      editorForm.value = {
        ...createEmptyEditor(),
        patient_id: createForm.value.patient_id,
        title: `${getPatientName(createForm.value.patient_id)} - 手工草稿`,
        metadata: { source: 'manual_draft' }
      }
      await loadContextForEditor(createForm.value.patient_id, null)
    }
    createVisible.value = false
  } catch (error) {
    message.error('病历草稿初始化失败')
  } finally {
    creating.value = false
  }
}

async function startDraftFromConversation (conversationId) {
  const draft = await getMedicalRecordDraft(conversationId)
  editorRecordId.value = null
  editorRecordMeta.value = {
    status: draft.draft_record.status || 'draft',
    metadata: draft.draft_record.metadata || {}
  }
  editorForm.value = {
    patient_id: draft.patient.id,
    conversation_id: draft.conversation.id,
    title: draft.draft_record.title || '',
    chief_complaint: draft.draft_record.chief_complaint || '',
    present_illness: draft.draft_record.present_illness || '',
    past_history: draft.draft_record.past_history || '',
    physical_examination: draft.draft_record.physical_examination || '',
    auxiliary_examination: draft.draft_record.auxiliary_examination || '',
    preliminary_diagnosis: draft.draft_record.preliminary_diagnosis || (draft.draft_record.diagnosis?.[0]?.name || ''),
    treatment_plan: draft.draft_record.treatment_plan || '',
    medical_advice: draft.draft_record.medical_advice || '',
    follow_up: draft.draft_record.follow_up || '',
    metadata: draft.draft_record.metadata || {}
  }
  await loadContextForEditor(draft.patient.id, draft.conversation.id)
}

function resetEditor () {
  editorRecordId.value = null
  editorRecordMeta.value = null
  selectedRecordId.value = null
  editorForm.value = createEmptyEditor()
  patientSummary.value = null
  diagnosisContext.value = null
}

async function saveDraft () {
  if (!editorForm.value.patient_id || !editorForm.value.title || !editorForm.value.chief_complaint) {
    message.warning('请完善患者、病历标题和主诉')
    return false
  }

  saving.value = true
  try {
    const payload = buildPayload()
    let saved
    if (editorRecordId.value) {
      saved = await updateMedicalRecord(editorRecordId.value, payload)
    } else {
      saved = await createMedicalRecord({
        patient_id: editorForm.value.patient_id,
        conversation_id: editorForm.value.conversation_id,
        ...payload
      })
      editorRecordId.value = saved.id
      selectedRecordId.value = saved.id
    }
    editorRecordMeta.value = { ...(editorRecordMeta.value || {}), ...saved, status: saved.status || 'draft' }
    message.success('草稿已保存')
    await reloadAll()
    if (editorRecordId.value) {
      await openRecordById(editorRecordId.value)
    }
    return true
  } catch (error) {
    message.error('草稿保存失败')
    return false
  } finally {
    saving.value = false
  }
}

async function confirmRecord () {
  try {
    const saved = await saveDraft()
    if (!saved || !editorRecordId.value) return
    await updateMedicalRecordStatus(editorRecordId.value, 'confirmed')
    message.success('病历已确认，可按需归档')
    await reloadAll()
    await openRecordById(editorRecordId.value)
  } catch (error) {
    const detail = error?.response?.data?.detail
    message.error(typeof detail === 'string' ? detail : '病历确认失败')
  }
}

async function runQualityCheck () {
  if (!editorRecordId.value) return
  try {
    const result = await qualityCheckMedicalRecord(editorRecordId.value)
    const messages = [
      ...(result.blocking || []),
      ...(result.warnings || []),
      ...(result.suggestions || [])
    ]
    message.info(`${result.decision || 'AI 质检完成'}${messages.length ? `：${messages[0]}` : ''}`)
    await openRecordById(editorRecordId.value)
  } catch (error) {
    message.error('AI 质检失败')
  }
}

async function assistRecord () {
  if (!editorRecordId.value) return
  try {
    const result = await assistMedicalRecord(editorRecordId.value)
    const suggestions = result.suggestions || {}
    editorForm.value = {
      ...editorForm.value,
      present_illness: editorForm.value.present_illness || suggestions.present_illness || '',
      treatment_plan: editorForm.value.treatment_plan || suggestions.treatment_plan || '',
      medical_advice: editorForm.value.medical_advice || suggestions.medical_advice || '',
      follow_up: editorForm.value.follow_up || suggestions.follow_up || ''
    }
    message.success(Object.keys(suggestions).length ? '智能补全已填入空白字段，请医生核对后保存' : '暂无可补全字段')
  } catch (error) {
    message.error('智能补全失败')
  }
}

async function submitAgentFeedback (feedbackType) {
  if (!editorRecordId.value) return
  try {
    await submitMedicalRecordAgentFeedback(editorRecordId.value, {
      feedback_type: feedbackType,
      comment: ''
    })
    message.success('Agent 反馈已记录')
  } catch (error) {
    message.error('Agent 反馈保存失败')
  }
}

async function archiveRecord (recordId) {
  try {
    await archiveMedicalRecord(recordId)
    message.success('病历已归档')
    await reloadAll()
    await openRecordById(recordId)
  } catch (error) {
    message.error('病历归档失败')
  }
}

async function removeRecord (recordId) {
  try {
    await deleteMedicalRecord(recordId)
    message.success('草稿已删除')
    if (editorRecordId.value === recordId) {
      resetEditor()
    }
    await reloadAll()
  } catch (error) {
    message.error('草稿删除失败')
  }
}

function buildPayload () {
  const diagnosis = editorForm.value.preliminary_diagnosis
    ? [{ name: editorForm.value.preliminary_diagnosis, type: 'primary' }]
    : []

  return {
    title: editorForm.value.title,
    chief_complaint: editorForm.value.chief_complaint,
    present_illness: editorForm.value.present_illness,
    past_history: editorForm.value.past_history,
    physical_examination: editorForm.value.physical_examination,
    auxiliary_examination: editorForm.value.auxiliary_examination,
    diagnosis,
    treatment_plan: editorForm.value.treatment_plan,
    medical_advice: editorForm.value.medical_advice,
    follow_up: editorForm.value.follow_up,
    metadata: editorForm.value.metadata || {}
  }
}

function mapRecordToEditor (record) {
  return {
    patient_id: record.patient_id,
    conversation_id: record.conversation_id,
    title: record.title || '',
    chief_complaint: record.chief_complaint || '',
    present_illness: record.present_illness || '',
    past_history: record.past_history || '',
    physical_examination: record.physical_examination || '',
    auxiliary_examination: record.auxiliary_examination || '',
    preliminary_diagnosis: record.diagnosis?.[0]?.name || '',
    treatment_plan: record.treatment_plan || '',
    medical_advice: record.medical_advice || '',
    follow_up: record.follow_up || '',
    metadata: record.metadata || {}
  }
}

function getPatientName (patientId) {
  const selected = records.value.find((record) => record.patient_id === patientId && record.patient_name)
  if (selected?.patient_name) return selected.patient_name
  const patient = patientMap.value[patientId]
  return patient ? (patient.full_name || patient.username || `患者 #${patientId}`) : `患者 #${patientId}`
}

function parseNumeric (value) {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) ? parsed : null
}

function statusLabel (status) {
  return {
    draft: '草稿',
    confirmed: '已确认',
    reviewed: '已审核（历史）',
    archived: '已归档'
  }[status] || status
}

function truncateText (text, maxLength = 180) {
  const value = String(text || '').trim()
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
}

function formatDate (value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN')
}

const PROFILE_LABELS = {
  gender: '性别',
  birth_date: '出生日期',
  allergies: '过敏史',
  chronic_diseases: '慢病',
  long_term_medications: '长期用药',
  family_history: '家族史'
}
</script>

<style scoped>
.records-page {
  display: grid;
  gap: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.status-tabs {
  display: inline-flex;
  padding: 4px;
  border-radius: 999px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
  gap: 4px;
}

.status-tab {
  height: 34px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--c-text-sec);
  cursor: pointer;
  font-family: var(--f-body);
}

.status-tab.active {
  color: #081321;
  background: linear-gradient(135deg, #38bdf8, #67e8f9);
}

.create-btn,
.primary-btn,
.create-record-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: 10px;
  border: 0;
  background: linear-gradient(135deg, #38bdf8, #67e8f9);
  color: #081321;
  font-weight: 700;
  cursor: pointer;
}

.archive-btn {
  background: linear-gradient(135deg, #f59e0b, #facc15);
}

.archive-btn.inline {
  flex-shrink: 0;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stats-card {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
}

.stats-label {
  font-size: 12px;
  color: var(--c-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stats-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
  color: var(--c-text);
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.78fr) minmax(0, 1.55fr) minmax(300px, 0.95fr);
  gap: 18px;
}

.queue-panel,
.editor-panel,
.context-panel {
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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

.queue-list {
  display: grid;
  gap: 10px;
  padding: 16px;
}

.queue-item {
  width: 100%;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--transition), background var(--transition), transform var(--transition);
}

.queue-item:hover,
.queue-item.active {
  border-color: var(--c-primary-border);
  background: rgba(34, 211, 238, 0.05);
  transform: translateY(-1px);
}

.queue-top,
.queue-foot {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.queue-patient,
.queue-title {
  color: var(--c-text);
  font-weight: 700;
}

.queue-title {
  margin-top: 8px;
  font-size: 13px;
}

.queue-sub,
.queue-foot {
  margin-top: 6px;
  color: var(--c-text-sec);
  font-size: 12px;
}

.queue-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  border: 1px solid var(--c-border-subtle);
}

.status-draft {
  color: #bae6fd;
  border-color: rgba(56, 189, 248, 0.24);
  background: rgba(56, 189, 248, 0.12);
}

.status-confirmed {
  color: #fde68a;
  border-color: rgba(245, 158, 11, 0.24);
  background: rgba(245, 158, 11, 0.12);
}

.status-reviewed {
  color: #bbf7d0;
  border-color: rgba(52, 211, 153, 0.24);
  background: rgba(52, 211, 153, 0.12);
}

.status-archived {
  color: #cbd5e1;
  border-color: rgba(148, 163, 184, 0.24);
  background: rgba(148, 163, 184, 0.12);
}

.editor-subtitle {
  margin-top: 6px;
  color: var(--c-text);
  font-size: 14px;
  font-weight: 700;
}

.source-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--c-primary);
  border: 1px solid var(--c-primary-border);
  background: rgba(34, 211, 238, 0.08);
  margin-left: 8px;
}

.editor-actions,
.editor-footer {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ghost-btn,
.footer-btn {
  height: 38px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--c-text-sec);
  cursor: pointer;
  font-family: var(--f-body);
}

.footer-btn.warning {
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.22);
}

.footer-btn.danger {
  color: #fb7185;
  border-color: rgba(251, 113, 133, 0.22);
}

.editor-scroll,
.context-scroll {
  max-height: calc(100vh - 270px);
  overflow: auto;
}

.record-form {
  padding: 18px;
}

.record-status-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  margin-bottom: 16px;
  border-radius: 14px;
  border: 1px solid rgba(245, 158, 11, 0.24);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.14), rgba(34, 211, 238, 0.08));
}

.record-status-banner-title {
  color: var(--c-text);
  font-size: 14px;
  font-weight: 700;
}

.record-status-banner-text {
  margin-top: 6px;
  color: var(--c-text-sec);
  font-size: 12px;
  line-height: 1.7;
}

.form-grid {
  display: grid;
  gap: 14px;
}

.form-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel-empty {
  padding: 22px 18px;
  color: var(--c-text-muted);
  font-size: 13px;
}

.panel-empty.large {
  min-height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.context-scroll {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.context-block {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
}

.context-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.context-kv-list {
  display: grid;
  gap: 10px;
}

.context-kv {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
}

.context-key {
  color: var(--c-text-muted);
}

.context-val,
.context-text {
  color: var(--c-text-sec);
  line-height: 1.7;
  white-space: pre-wrap;
}

.context-highlight {
  color: var(--c-text);
  font-weight: 700;
  line-height: 1.7;
}

.triage-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 6px 10px;
  border-radius: 999px;
  color: var(--c-primary);
  border: 1px solid var(--c-primary-border);
  background: rgba(34, 211, 238, 0.08);
  font-size: 12px;
}

.report-mini-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.report-mini-item {
  padding: 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--c-border-subtle);
}

.report-mini-name {
  color: var(--c-text);
  font-size: 12px;
  font-weight: 700;
}

.report-mini-text {
  margin-top: 6px;
  color: var(--c-text-sec);
  font-size: 12px;
  line-height: 1.65;
}

.context-empty,
.wizard-tip {
  color: var(--c-text-muted);
  font-size: 12px;
  line-height: 1.7;
}

.feedback-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-btn {
  height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.04);
  color: var(--c-text-sec);
  cursor: pointer;
}

.feedback-btn.danger {
  color: #fb7185;
  border-color: rgba(251, 113, 133, 0.22);
}

.review-options {
  display: flex;
  gap: 12px;
}

.review-option {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 2px solid var(--c-border);
  cursor: pointer;
  transition: all var(--transition);
  font-weight: 600;
  font-size: 14px;
  color: var(--c-text-sec);
}

.review-option.selected {
  border-color: var(--c-primary);
  background: rgba(34, 211, 238, 0.06);
  color: var(--c-text);
}

.option-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
}

.option-icon.pass {
  background: rgba(52, 211, 153, 0.12);
  color: #34d399;
}

.option-icon.fail {
  background: rgba(251, 113, 133, 0.12);
  color: #fb7185;
}

@media (max-width: 1360px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .form-grid.two {
    grid-template-columns: 1fr;
  }

  .record-status-banner {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
