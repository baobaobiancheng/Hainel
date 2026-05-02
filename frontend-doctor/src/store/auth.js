import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getCurrentUser, login as loginApi } from '../api/auth'

const USER_INFO_KEY = 'doctor_user_info'

const readStoredUserInfo = () => {
  const raw = localStorage.getItem(USER_INFO_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw)
  } catch (error) {
    localStorage.removeItem(USER_INFO_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(readStoredUserInfo())

  const isAuthenticated = computed(() => !!token.value)

  function setToken(newToken) {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('token', newToken)
    } else {
      localStorage.removeItem('token')
    }
  }

  function setUserInfo(info) {
    userInfo.value = info
    if (info) {
      localStorage.setItem(USER_INFO_KEY, JSON.stringify(info))
    } else {
      localStorage.removeItem(USER_INFO_KEY)
    }
  }

  async function ensureUserInfo() {
    if (!token.value) return null
    if (userInfo.value?.role) return userInfo.value

    try {
      const response = await getCurrentUser()
      setUserInfo(response)
      return response
    } catch (error) {
      logout()
      throw error
    }
  }

  async function login(username, password) {
    try {
      const response = await loginApi(username, password)
      setToken(response.access_token)
      setUserInfo(response.user)
      return { success: true }
    } catch (error) {
      return { success: false, message: error.message || '登录失败' }
    }
  }

  function logout() {
    setToken('')
    setUserInfo(null)
  }

  return {
    token,
    userInfo,
    isAuthenticated,
    setToken,
    setUserInfo,
    ensureUserInfo,
    login,
    logout
  }
})

