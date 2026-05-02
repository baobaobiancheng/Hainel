import { createRouter, createWebHistory } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../store/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '仪表盘', requiresAuth: true }
      },
      {
        path: 'patients',
        name: 'Patients',
        component: () => import('../views/Patients.vue'),
        meta: { title: '患者管理', requiresAuth: true }
      },
      {
        path: 'conversations',
        name: 'Conversations',
        component: () => import('../views/Conversations.vue'),
        meta: { title: '会话管理', requiresAuth: true }
      },
      {
        path: 'diagnosis',
        name: 'Diagnosis',
        component: () => import('../views/Diagnosis.vue'),
        meta: { title: '辅助诊断', requiresAuth: true }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/Knowledge.vue'),
        meta: { title: '知识检索', requiresAuth: true }
      },
      {
        path: 'records',
        name: 'Records',
        component: () => import('../views/Records.vue'),
        meta: { title: '病历管理', requiresAuth: true }
      },
      {
        path: 'knowledge-admin',
        name: 'KnowledgeAdmin',
        component: () => import('../views/KnowledgeAdmin.vue'),
        meta: { title: '知识库管理', requiresAuth: true, requiresAdmin: true }
      },
      {
        path: 'rl-training',
        name: 'RLTraining',
        component: () => import('../views/RLTraining.vue'),
        meta: { title: '强化学习训练', requiresAuth: true, requiresAdmin: true }
      },
      {
        path: 'model-center',
        name: 'ModelCenter',
        component: () => import('../views/ModelCenter.vue'),
        meta: { title: '模型中心', requiresAuth: true, requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    next('/dashboard')
    return
  }

  if (to.meta.requiresAdmin) {
    try {
      const user = await authStore.ensureUserInfo()
      if (user?.role !== 'admin') {
        message.error('仅管理员可访问该页面')
        next('/dashboard')
        return
      }
    } catch (error) {
      next('/login')
      return
    }
  }

  next()
})

export default router
