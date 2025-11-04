/**
 * 用户状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { UserInfo } from '@/types/api'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref<string>('')
  const refreshToken = ref<string>('')
  const userInfo = ref<UserInfo | null>(null)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => userInfo.value?.username || '')
  const avatar = computed(() => userInfo.value?.avatar_url || '')

  // 初始化（从 localStorage 恢复）
  function init() {
    const savedToken = localStorage.getItem('access_token')
    const savedRefreshToken = localStorage.getItem('refresh_token')
    const savedUserInfo = localStorage.getItem('user_info')

    if (savedToken) token.value = savedToken
    if (savedRefreshToken) refreshToken.value = savedRefreshToken
    if (savedUserInfo) {
      try {
        userInfo.value = JSON.parse(savedUserInfo)
      } catch (e) {
        console.error('Failed to parse user info:', e)
      }
    }
  }

  // 登录
  async function login(username_or_email: string, password: string) {
    try {
      const response = await authApi.login({ username_or_email, password })
      
      if (response.success && response.data) {
        token.value = response.data.access_token
        refreshToken.value = response.data.refresh_token
        
        // 保存到 localStorage
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('refresh_token', response.data.refresh_token)
        
        // 获取用户信息
        await fetchUserInfo()
        
        return true
      }
      return false
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  // 注册
  async function register(username: string, email: string, password: string) {
    try {
      const response = await authApi.register({ username, email, password })
      return response.success
    } catch (error) {
      console.error('Register failed:', error)
      return false
    }
  }

  // 获取用户信息
  async function fetchUserInfo() {
    try {
      const response = await authApi.getCurrentUser()
      if (response.success && response.data) {
        userInfo.value = response.data
        localStorage.setItem('user_info', JSON.stringify(response.data))
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error)
    }
  }

  // 登出
  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
  }

  // 更新用户信息
  function updateUserInfo(info: Partial<UserInfo>) {
    if (userInfo.value) {
      userInfo.value = { ...userInfo.value, ...info }
      localStorage.setItem('user_info', JSON.stringify(userInfo.value))
    }
  }

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    username,
    avatar,
    init,
    login,
    register,
    fetchUserInfo,
    logout,
    updateUserInfo,
  }
})

