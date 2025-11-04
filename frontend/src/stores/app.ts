/**
 * 应用全局状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useUserStore } from './user'

export const useAppStore = defineStore('app', () => {
  // 状态
  const loading = ref(false)
  const sidebarCollapsed = ref(false)
  const theme = ref<'light' | 'dark'>('light')

  // 初始化应用
  function initApp() {
    // 初始化用户状态
    const userStore = useUserStore()
    userStore.init()
    
    // 初始化主题
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
    if (savedTheme) {
      theme.value = savedTheme
      applyTheme(savedTheme)
    }
    
    // 初始化侧边栏状态
    const savedSidebarState = localStorage.getItem('sidebar_collapsed')
    if (savedSidebarState) {
      sidebarCollapsed.value = savedSidebarState === 'true'
    }
  }

  // 切换侧边栏
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed.value))
  }

  // 切换主题
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', theme.value)
    applyTheme(theme.value)
  }

  // 应用主题
  function applyTheme(newTheme: 'light' | 'dark') {
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  // 设置加载状态
  function setLoading(value: boolean) {
    loading.value = value
  }

  return {
    loading,
    sidebarCollapsed,
    theme,
    initApp,
    toggleSidebar,
    toggleTheme,
    setLoading,
  }
})

