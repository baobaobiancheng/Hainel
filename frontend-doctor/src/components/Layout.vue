<template>
  <div class="shell" :class="{ collapsed }">
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="11" y="3" width="6" height="22" rx="3" fill="#22d3ee" />
            <rect x="3" y="11" width="22" height="6" rx="3" fill="#22d3ee" />
          </svg>
        </div>
        <div class="logo-text">
          <span class="logo-main">智能医疗</span>
          <span class="logo-sub">诊断平台</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-group-label">工作台</div>
        <router-link
          v-for="item in navItems"
          :key="item.key"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item) }"
        >
          <span class="nav-icon">
            <component :is="item.icon" />
          </span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-version">v2.4.1</div>
        <div class="user-row">
          <div class="user-avatar-sm">{{ userInitial }}</div>
          <div class="user-info">
            <div class="user-name">{{ username }}</div>
            <div class="user-role">{{ userRoleText }}</div>
          </div>
          <button class="logout-btn" @click="handleLogout" title="退出登录">
            <LogoutOutlined />
          </button>
        </div>
      </div>

      <button class="collapse-btn" @click="collapsed = !collapsed">
        <MenuFoldOutlined v-if="!collapsed" />
        <MenuUnfoldOutlined v-else />
      </button>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="page-breadcrumb">
          <span class="breadcrumb-root">医疗平台</span>
          <span class="breadcrumb-sep">/</span>
          <span class="breadcrumb-current">{{ currentPageTitle }}</span>
        </div>

        <div class="topbar-right">
          <div class="topbar-time">
            <span class="mono">{{ currentTime }}</span>
          </div>
          <div class="topbar-divider"></div>
          <a-dropdown placement="bottomRight">
            <button class="user-btn">
              <div class="user-btn-avatar">{{ userInitial }}</div>
              <span class="user-btn-name">{{ username }}</span>
              <DownOutlined style="font-size: 10px; opacity: 0.6" />
            </button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="handleLogout">
                  <LogoutOutlined style="margin-right: 8px" />
                  退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, notification } from 'ant-design-vue'
import {
  BookOutlined,
  DashboardOutlined,
  DownOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  LogoutOutlined,
  MedicineBoxOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MessageOutlined,
  SettingOutlined,
  UserOutlined,
  ApiOutlined
} from '@ant-design/icons-vue'
import { useAuthStore } from '../store/auth'
import wsService from '../utils/websocket'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const currentTime = ref('')
let timer = null
let removeWsMessageHandler = null
let removeWsOpenHandler = null
let removeWsErrorHandler = null

const navItems = computed(() => {
  const items = [
    { key: 'dashboard', path: '/dashboard', label: '仪表盘', icon: DashboardOutlined },
    { key: 'patients', path: '/patients', label: '患者管理', icon: UserOutlined },
    { key: 'conversations', path: '/conversations', label: '会话管理', icon: MessageOutlined },
    { key: 'diagnosis', path: '/diagnosis', label: '辅助诊断', icon: MedicineBoxOutlined },
    { key: 'knowledge', path: '/knowledge', label: '知识检索', icon: BookOutlined },
    { key: 'records', path: '/records', label: '病历管理', icon: FileTextOutlined }
  ]

  if (isAdmin.value) {
    items.push({ key: 'knowledge-admin', path: '/knowledge-admin', label: '知识库管理', icon: SettingOutlined })
    items.push({ key: 'rl-training', path: '/rl-training', label: '强化学习训练', icon: ExperimentOutlined })
    items.push({ key: 'model-center', path: '/model-center', label: '模型中心', icon: ApiOutlined })
  }

  return items
})

const pageTitles = {
  dashboard: '仪表盘',
  patients: '患者管理',
  conversations: '会话管理',
  diagnosis: '辅助诊断',
  knowledge: '知识检索',
  records: '病历管理',
  knowledgeadmin: '知识库管理',
  rltraining: '强化学习训练',
  modelcenter: '模型中心'
}

const currentPageTitle = computed(() => {
  const name = route.name?.toLowerCase() || ''
  return pageTitles[name] || '工作台'
})

const username = computed(() => authStore.userInfo?.username || '医生')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())
const isAdmin = computed(() => authStore.userInfo?.role === 'admin')
const userRoleText = computed(() => {
  const role = authStore.userInfo?.role
  if (role === 'admin') return '管理员'
  if (role === 'doctor') return '主治医生'
  return '医生'
})

const isActive = (item) => route.path === item.path

const updateTime = () => {
  currentTime.value = new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  initDoctorWebSocket()
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  cleanupDoctorWebSocket({ disconnect: true })
})

const handleLogout = () => {
  cleanupDoctorWebSocket({ disconnect: true, clearCallbacks: true })
  authStore.logout()
  message.success('已退出登录')
  router.push('/login')
}

const initDoctorWebSocket = () => {
  removeWsOpenHandler = wsService.onOpen(() => {
    console.log('Doctor WebSocket connected')
  })

  removeWsErrorHandler = wsService.onError((error) => {
    console.error('Doctor WebSocket error:', error)
  })

  removeWsMessageHandler = wsService.onMessage((data) => {
    if (data.type === 'new_session') {
      handleNewSession(data)
    }
  })

  wsService.connect()
}

const cleanupDoctorWebSocket = (options = {}) => {
  removeWsMessageHandler?.()
  removeWsOpenHandler?.()
  removeWsErrorHandler?.()
  removeWsMessageHandler = null
  removeWsOpenHandler = null
  removeWsErrorHandler = null

  if (options.disconnect) {
    wsService.disconnect({ clearCallbacks: Boolean(options.clearCallbacks) })
  }
}

const handleNewSession = (data) => {
  window.dispatchEvent(new CustomEvent('doctor:new-session', { detail: data }))

  const complaint = data.chief_complaint || '未知主诉'
  const departmentText = data.department ? ` · ${data.department}` : ''
  const urgencyText = data.urgency ? ` · ${getUrgencyText(data.urgency)}` : ''

  notification.info({
    message: '新会话通知',
    description: `收到新的咨询请求：${complaint.substring(0, 24)}${departmentText}${urgencyText}`,
    duration: 5,
    onClick: () => {
      if (data.conversation_id) {
        router.push(`/diagnosis?conversation_id=${data.conversation_id}`)
      }
    }
  })
}

const getUrgencyText = (urgency) =>
  ({
    emergency: '急诊',
    urgent: '加急',
    normal: '普通',
    low: '低优先级'
  }[urgency] || urgency)
</script>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--c-bg-base);
}

.sidebar {
  width: 232px;
  flex-shrink: 0;
  height: 100%;
  background: linear-gradient(180deg, #0a1527 0%, #080e1a 100%);
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  transition: width 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 20;
  overflow: hidden;
}

.shell.collapsed .sidebar {
  width: 64px;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 16px 20px;
  border-bottom: 1px solid var(--c-border-subtle);
  flex-shrink: 0;
}

.logo-mark {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  background: rgba(34, 211, 238, 0.08);
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  white-space: nowrap;
}

.logo-main {
  font-family: var(--f-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--c-text);
  line-height: 1.2;
}

.logo-sub {
  font-size: 10px;
  color: var(--c-primary);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 500;
}

.shell.collapsed .logo-text,
.shell.collapsed .nav-label,
.shell.collapsed .nav-group-label,
.shell.collapsed .sidebar-version,
.shell.collapsed .user-info {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-group-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--c-text-muted);
  padding: 6px 8px 10px;
  white-space: nowrap;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 8px;
  margin-bottom: 3px;
  color: var(--c-text-sec);
  text-decoration: none;
  transition: all var(--transition);
  position: relative;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: var(--c-text);
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(34, 211, 238, 0.12) 0%, rgba(34, 211, 238, 0.04) 100%);
  color: var(--c-primary);
  border: 1px solid rgba(34, 211, 238, 0.16);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 20%;
  bottom: 20%;
  width: 3px;
  background: var(--c-primary);
  border-radius: 0 3px 3px 0;
  box-shadow: 0 0 8px var(--c-primary);
}

.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}

.nav-label {
  font-size: 13.5px;
  font-weight: 500;
}

.sidebar-footer {
  padding: 12px 10px 14px;
  border-top: 1px solid var(--c-border-subtle);
  flex-shrink: 0;
}

.sidebar-version {
  font-family: var(--f-mono);
  font-size: 10px;
  color: var(--c-text-muted);
  margin-bottom: 10px;
  padding-left: 2px;
  white-space: nowrap;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar-sm,
.user-btn-avatar {
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
}

.user-avatar-sm {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  font-size: 14px;
}

.user-info {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  text-overflow: ellipsis;
  overflow: hidden;
}

.user-role {
  font-size: 11px;
  color: var(--c-primary);
  font-weight: 500;
}

.logout-btn {
  background: none;
  border: none;
  color: var(--c-text-muted);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  transition: all var(--transition);
}

.logout-btn:hover {
  color: var(--c-danger);
  background: rgba(248, 113, 113, 0.08);
}

.shell.collapsed .logout-btn {
  display: none;
}

.collapse-btn {
  position: absolute;
  bottom: 72px;
  right: -12px;
  width: 24px;
  height: 24px;
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: var(--c-text-sec);
  cursor: pointer;
  transition: all var(--transition);
  z-index: 10;
}

.collapse-btn:hover {
  background: var(--c-primary);
  color: #080e1a;
  border-color: var(--c-primary);
  box-shadow: 0 0 8px var(--c-primary-glow);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.topbar {
  height: 56px;
  flex-shrink: 0;
  background: rgba(13, 24, 41, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 10;
}

.page-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.breadcrumb-root {
  color: var(--c-text-muted);
}

.breadcrumb-sep {
  color: var(--c-border);
}

.breadcrumb-current {
  color: var(--c-text);
  font-weight: 600;
  font-size: 14px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-time .mono {
  font-family: var(--f-mono);
  font-size: 12px;
  color: var(--c-text-sec);
  letter-spacing: 0.04em;
}

.topbar-divider {
  width: 1px;
  height: 20px;
  background: var(--c-border);
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 5px 10px 5px 6px;
  cursor: pointer;
  color: var(--c-text);
  transition: all var(--transition);
}

.user-btn:hover {
  background: rgba(34, 211, 238, 0.06);
  border-color: var(--c-primary-border);
}

.user-btn-avatar {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  font-size: 12px;
}

.user-btn-name {
  font-size: 13px;
  font-weight: 500;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--c-bg-base);
}

.content-area > * {
  animation: fadeIn 0.18s ease;
}
</style>
