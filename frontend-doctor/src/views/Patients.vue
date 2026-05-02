<template>
  <div class="page-wrap">
    <div class="page-header">
      <div>
        <div class="section-label">PATIENT MANAGEMENT</div>
        <h1 class="page-title-text">患者 <span>纵向档案</span></h1>
      </div>
      <div class="header-actions">
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索姓名 / 手机号"
          style="width: 260px"
          @search="handleSearch"
          allow-clear
        />
      </div>
    </div>

    <div class="table-card glass-card">
      <a-table
        :columns="columns"
        :data-source="patients"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
        :scroll="{ x: 980 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'full_name'">
            <div class="name-cell">
              <div class="name-avatar">{{ (record.full_name || record.username || '?')[0] }}</div>
              <span>{{ record.full_name || record.username }}</span>
            </div>
          </template>
          <template v-else-if="column.key === 'id'">
            <span class="mono id-text">#{{ record.id }}</span>
          </template>
          <template v-else-if="column.key === 'conversation_count'">
            <span class="mono badge-num">{{ record.conversation_count || 0 }}</span>
          </template>
          <template v-else-if="column.key === 'is_active'">
            <div class="status-pill" :class="record.is_active ? 'active' : 'inactive'">
              <span class="status-dot-sm"></span>
              {{ record.is_active ? '正常' : '停用' }}
            </div>
          </template>
          <template v-else-if="column.key === 'last_conversation_at'">
            <span class="mono time-text">{{ record.last_conversation_at ? formatDate(record.last_conversation_at) : '—' }}</span>
          </template>
          <template v-else-if="column.key === 'created_at'">
            <span class="mono time-text">{{ formatDate(record.created_at) }}</span>
          </template>
          <template v-else-if="column.key === 'action'">
            <div class="action-btns">
              <button class="act-btn primary" @click="viewDetail(record.id)">查看</button>
              <button class="act-btn ghost" @click="viewConversations(record.id)">会话记录</button>
              <button class="act-btn success" @click="openRecordWorkspace(record.id)">新建病历</button>
            </div>
          </template>
        </template>
      </a-table>
    </div>

    <a-drawer
      v-model:open="drawerVisible"
      title="患者详情"
      width="760"
    >
      <a-spin :spinning="detailLoading">
        <template v-if="currentPatientDetail">
          <div class="drawer-grid">
            <div class="drawer-main">
              <div class="glass-section">
                <div class="drawer-patient-header">
                  <div class="drawer-avatar">
                    {{ (currentPatientDetail.patient.full_name || currentPatientDetail.patient.username || '?')[0] }}
                  </div>
                  <div>
                    <div class="drawer-patient-name">
                      {{ currentPatientDetail.patient.full_name || currentPatientDetail.patient.username }}
                    </div>
                    <div class="drawer-patient-sub">
                      <span class="mono">ID: #{{ currentPatientDetail.patient.id }}</span>
                      <span class="status-pill sm" :class="currentPatientDetail.patient.is_active ? 'active' : 'inactive'">
                        <span class="status-dot-sm"></span>
                        {{ currentPatientDetail.patient.is_active ? '正常' : '停用' }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="info-grid">
                  <div class="info-item">
                    <div class="info-label">手机号</div>
                    <div class="info-value mono">{{ currentPatientDetail.patient.phone || '未填写' }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">邮箱</div>
                    <div class="info-value">{{ currentPatientDetail.patient.email || '未填写' }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">注册时间</div>
                    <div class="info-value mono">{{ formatDate(currentPatientDetail.patient.created_at) }}</div>
                  </div>
                </div>
              </div>

              <div class="glass-section">
                <div class="drawer-section-title">患者活动趋势（30 天）</div>
                <div class="mini-trend">
                  <div
                    v-for="item in trendBars"
                    :key="item.date"
                    class="trend-day"
                    :title="`${item.date}｜会话 ${item.consultations}｜病历 ${item.records}`"
                  >
                    <div class="trend-stack">
                      <span class="trend-bar consultation" :style="{ height: `${item.consultationHeight}%` }"></span>
                      <span class="trend-bar record" :style="{ height: `${item.recordHeight}%` }"></span>
                    </div>
                    <span class="trend-label">{{ item.date.slice(5) }}</span>
                  </div>
                </div>
              </div>

              <div class="glass-section">
                <div class="drawer-section-title">最近会话</div>
                <template v-if="currentPatientDetail.recent_conversations?.length">
                  <div
                    v-for="item in currentPatientDetail.recent_conversations"
                    :key="item.id"
                    class="mini-conv-item"
                    @click="openConversation(item.id)"
                  >
                    <div class="mini-conv-id mono">#{{ item.id }}</div>
                    <div class="mini-conv-info">
                      <div class="mini-conv-title">{{ item.title || `会话 #${item.id}` }}</div>
                      <div class="mini-conv-sub">{{ item.chief_complaint || '暂无主诉' }}</div>
                    </div>
                    <span class="conv-status-badge" :class="item.status">{{ getStatusText(item.status) }}</span>
                  </div>
                </template>
                <a-empty v-else :image="null" description="暂无会话记录" />
              </div>
            </div>

            <div class="drawer-side">
              <div class="glass-section">
                <div class="drawer-section-title">会话统计</div>
                <div class="stats-mini-grid">
                  <div class="stats-mini-card" v-for="(val, key) in currentPatientDetail.conversation_stats" :key="key">
                    <div class="stats-mini-val mono">{{ val }}</div>
                    <div class="stats-mini-label">{{ statsLabel[key] || key }}</div>
                  </div>
                </div>
              </div>

              <div class="glass-section">
                <div class="drawer-section-title">病历统计</div>
                <div class="stats-mini-grid compact">
                  <div class="stats-mini-card" v-for="(val, key) in currentPatientDetail.medical_record_stats" :key="key">
                    <div class="stats-mini-val mono">{{ val }}</div>
                    <div class="stats-mini-label">{{ recordStatsLabel[key] || key }}</div>
                  </div>
                </div>
              </div>

              <div class="glass-section">
                <div class="drawer-section-title">健康档案摘要</div>
                <div v-if="healthProfileItems.length" class="health-list">
                  <div v-for="item in healthProfileItems" :key="item.key" class="health-item">
                    <div class="health-label">{{ item.label }}</div>
                    <div class="health-value">{{ item.value }}</div>
                  </div>
                </div>
                <div v-else class="empty-side">暂无健康档案信息。</div>
              </div>

              <button class="create-record-btn" @click="openRecordWorkspace(currentPatientDetail.patient.id)">
                进入病历工作台
              </button>
            </div>
          </div>
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { getPatients, getPatientDetail } from '../api/patients'

const router = useRouter()

const loading = ref(false)
const detailLoading = ref(false)
const searchText = ref('')
const patients = ref([])
const currentPatientDetail = ref(null)
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
  { title: '姓名', key: 'full_name', ellipsis: true },
  { title: '手机号', dataIndex: 'phone', key: 'phone', width: 130 },
  { title: '会话数', key: 'conversation_count', width: 90, align: 'center' },
  { title: '最近会话', key: 'last_conversation_at', width: 170 },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '注册时间', key: 'created_at', width: 170 },
  { title: '操作', key: 'action', width: 220, fixed: 'right' }
]

const statsLabel = {
  total: '全部',
  active: '进行中',
  completed: '已完成',
  pending: '待处理',
  cancelled: '已取消'
}

const recordStatsLabel = {
  total: '全部',
  draft: '草稿',
  confirmed: '已确认',
  reviewed: '已审核（历史）',
  archived: '已归档'
}

const STATUS_TEXT_MAP = {
  active: '进行中',
  pending: '待处理',
  completed: '已完成',
  cancelled: '已取消',
  paused: '已暂停',
  closed: '已关闭'
}

const PROFILE_LABELS = {
  gender: '性别',
  birth_date: '出生日期',
  allergies: '过敏史',
  chronic_diseases: '慢病',
  long_term_medications: '长期用药',
  family_history: '家族史'
}

const healthProfileItems = computed(() => {
  const profile = currentPatientDetail.value?.patient?.health_profile || {}
  return Object.entries(profile)
    .filter(([, value]) => value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length))
    .map(([key, value]) => ({
      key,
      label: PROFILE_LABELS[key] || key,
      value: Array.isArray(value) ? value.join('、') : String(value)
    }))
})

const trendBars = computed(() => {
  const trend = currentPatientDetail.value?.activity_trend || []
  const maxValue = Math.max(1, ...trend.map((item) => Math.max(item.consultations || 0, item.records || 0)))
  return trend.map((item) => ({
    ...item,
    consultationHeight: Math.max(10, ((item.consultations || 0) / maxValue) * 100),
    recordHeight: Math.max(10, ((item.records || 0) / maxValue) * 100)
  }))
})

onMounted(() => {
  loadPatients()
})

const loadPatients = async () => {
  loading.value = true
  try {
    const params = { page: pagination.value.current, page_size: pagination.value.pageSize }
    if (searchText.value) params.search = searchText.value
    const data = await getPatients(params)
    patients.value = Array.isArray(data) ? data : (data?.items || [])
    pagination.value.total = Array.isArray(data) ? data.length : (data?.total || 0)
  } catch (error) {
    message.error('加载患者列表失败')
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  loadPatients()
}

const handleSearch = () => {
  pagination.value.current = 1
  loadPatients()
}

const viewDetail = async (id) => {
  drawerVisible.value = true
  detailLoading.value = true
  try {
    currentPatientDetail.value = await getPatientDetail(id)
  } catch (error) {
    message.error('加载患者详情失败')
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

const viewConversations = (patientId) => {
  router.push(`/conversations?patient_id=${patientId}`)
}

const openRecordWorkspace = (patientId) => {
  router.push({
    path: '/records',
    query: { patient_id: String(patientId), create: '1' }
  })
}

const openConversation = (conversationId) => {
  drawerVisible.value = false
  router.push(`/conversations?id=${conversationId}`)
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

const getStatusText = (status) => STATUS_TEXT_MAP[status] || status
</script>

<style scoped>
.table-card {
  border-radius: var(--radius);
  overflow: hidden;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 9px;
}

.name-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0e7490, #1d4ed8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.id-text {
  color: var(--c-text-muted);
  font-size: 12px;
}

.badge-num {
  background: rgba(34, 211, 238, 0.08);
  color: var(--c-primary);
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
}

.time-text {
  font-size: 12px;
  color: var(--c-text-sec);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 20px;
  letter-spacing: 0.03em;
}

.status-pill.active {
  background: rgba(52, 211, 153, 0.1);
  color: var(--c-success);
  border: 1px solid rgba(52, 211, 153, 0.2);
}

.status-pill.inactive {
  background: rgba(100, 116, 139, 0.1);
  color: var(--c-text-muted);
  border: 1px solid rgba(100, 116, 139, 0.2);
}

.status-pill.sm {
  font-size: 10px;
  padding: 2px 7px;
}

.status-dot-sm {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-pill.active .status-dot-sm {
  background: var(--c-success);
  box-shadow: 0 0 5px var(--c-success);
}

.status-pill.inactive .status-dot-sm {
  background: var(--c-text-muted);
}

.action-btns {
  display: flex;
  gap: 6px;
}

.act-btn {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid;
  cursor: pointer;
  transition: all var(--transition);
}

.act-btn.primary {
  background: rgba(34, 211, 238, 0.1);
  border-color: rgba(34, 211, 238, 0.2);
  color: var(--c-primary);
}

.act-btn.primary:hover {
  background: rgba(34, 211, 238, 0.18);
}

.act-btn.ghost {
  background: transparent;
  border-color: var(--c-border);
  color: var(--c-text-sec);
}

.act-btn.ghost:hover {
  border-color: var(--c-text-sec);
}

.act-btn.success {
  background: rgba(52, 211, 153, 0.1);
  border-color: rgba(52, 211, 153, 0.2);
  color: #34d399;
}

.act-btn.success:hover {
  background: rgba(52, 211, 153, 0.18);
}

.drawer-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(260px, 0.9fr);
  gap: 18px;
}

.drawer-main,
.drawer-side {
  display: grid;
  gap: 16px;
  align-content: start;
}

.glass-section {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid var(--c-border-subtle);
  background: rgba(255, 255, 255, 0.03);
}

.drawer-patient-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
}

.drawer-avatar {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.drawer-patient-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 6px;
}

.drawer-patient-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--c-text-muted);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.info-item {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border-subtle);
  border-radius: 10px;
  padding: 12px 14px;
}

.info-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--c-text-muted);
  text-transform: uppercase;
  margin-bottom: 5px;
}

.info-value {
  font-size: 13px;
  color: var(--c-text);
}

.drawer-section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 12px;
}

.stats-mini-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.stats-mini-grid.compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.stats-mini-card {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border-subtle);
  border-radius: 10px;
  padding: 12px 8px;
  text-align: center;
}

.stats-mini-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--c-primary);
  margin-bottom: 4px;
}

.stats-mini-label {
  font-size: 11px;
  color: var(--c-text-sec);
}

.mini-trend {
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  gap: 8px;
}

.trend-day {
  display: grid;
  gap: 6px;
  align-items: end;
}

.trend-stack {
  height: 80px;
  display: flex;
  align-items: end;
  justify-content: center;
  gap: 4px;
}

.trend-bar {
  width: 8px;
  border-radius: 999px 999px 2px 2px;
}

.trend-bar.consultation {
  background: #38bdf8;
}

.trend-bar.record {
  background: #34d399;
}

.trend-label {
  font-size: 10px;
  color: var(--c-text-muted);
  text-align: center;
}

.mini-conv-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
}

.mini-conv-item:last-child {
  border-bottom: 0;
}

.mini-conv-id {
  color: var(--c-text-muted);
  font-size: 12px;
}

.mini-conv-info {
  flex: 1;
}

.mini-conv-title {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
}

.mini-conv-sub {
  margin-top: 4px;
  color: var(--c-text-sec);
  font-size: 12px;
}

.conv-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--c-text-sec);
  border: 1px solid var(--c-border-subtle);
}

.conv-status-badge.active {
  color: var(--c-primary);
  border-color: var(--c-primary-border);
}

.health-list {
  display: grid;
  gap: 10px;
}

.health-item {
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--c-border-subtle);
}

.health-label {
  font-size: 11px;
  color: var(--c-text-muted);
  margin-bottom: 5px;
}

.health-value {
  color: var(--c-text-sec);
  font-size: 13px;
  line-height: 1.7;
}

.empty-side {
  color: var(--c-text-muted);
  font-size: 13px;
}

.create-record-btn {
  height: 42px;
  border-radius: 12px;
  border: 0;
  background: linear-gradient(135deg, #38bdf8, #67e8f9);
  color: #081321;
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 1024px) {
  .drawer-grid {
    grid-template-columns: 1fr;
  }

  .stats-mini-grid,
  .stats-mini-grid.compact {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .mini-trend {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}
</style>
