import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

NProgress.configure({ showSpinner: false })

const routes: RouteRecordRaw[] = [
  {
    path: '/auth',
    name: 'Auth',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      {
        path: 'login',
        name: 'Login',
        component: () => import('@/views/auth/Login.vue'),
        meta: { title: '登录' },
      },
      {
        path: 'register',
        name: 'Register',
        component: () => import('@/views/auth/Register.vue'),
        meta: { title: '注册' },
      },
    ],
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Dashboard.vue'),
        meta: { title: '工作台', icon: 'Dashboard' },
      },
      {
        path: 'errors',
        name: 'ErrorList',
        component: () => import('@/views/errors/ErrorList.vue'),
        meta: { title: '错题本', icon: 'Document' },
      },
      {
        path: 'errors/:id',
        name: 'ErrorDetail',
        component: () => import('@/views/errors/ErrorDetail.vue'),
        meta: { title: '错题详情', hidden: true },
      },
      {
        path: 'errors/add',
        name: 'AddError',
        component: () => import('@/views/errors/AddError.vue'),
        meta: { title: '添加错题', hidden: true },
      },
      {
        path: 'practice',
        name: 'Practice',
        component: () => import('@/views/practice/PracticeList.vue'),
        meta: { title: '智能练习', icon: 'Edit' },
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/knowledge/KnowledgeGraph.vue'),
        meta: { title: '知识图谱', icon: 'Connection' },
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/ReportView.vue'),
        meta: { title: '学习报告', icon: 'TrendCharts' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/NotFound.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  NProgress.start()
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 智能错题本` : '智能错题本'
  
  // 检查是否需要登录
  if (to.meta.requiresAuth) {
    const userStore = useUserStore()
    if (!userStore.isLoggedIn) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }
  
  // 如果已登录，不允许访问登录/注册页
  if (to.name === 'Login' || to.name === 'Register') {
    const userStore = useUserStore()
    if (userStore.isLoggedIn) {
      next({ name: 'Dashboard' })
      return
    }
  }
  
  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router

