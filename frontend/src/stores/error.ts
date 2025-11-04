/**
 * 错题状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { errorApi } from '@/api/error'
import type { ErrorQuestion, ErrorQuestionQuery } from '@/types/api'
import { ElMessage } from 'element-plus'

export const useErrorStore = defineStore('error', () => {
  // 状态
  const errorList = ref<ErrorQuestion[]>([])
  const currentError = ref<ErrorQuestion | null>(null)
  const total = ref(0)
  const loading = ref(false)

  // 获取错题列表
  async function fetchErrorList(query: ErrorQuestionQuery = {}) {
    try {
      loading.value = true
      const response = await errorApi.getErrorQuestions(query)
      
      if (response.success && response.data) {
        errorList.value = response.data.items
        total.value = response.data.total
      }
    } catch (error) {
      console.error('Failed to fetch error list:', error)
      ElMessage.error('获取错题列表失败')
    } finally {
      loading.value = false
    }
  }

  // 获取错题详情
  async function fetchErrorDetail(id: string) {
    try {
      loading.value = true
      const response = await errorApi.getErrorQuestion(id)
      
      if (response.success && response.data) {
        currentError.value = response.data
        return response.data
      }
    } catch (error) {
      console.error('Failed to fetch error detail:', error)
      ElMessage.error('获取错题详情失败')
    } finally {
      loading.value = false
    }
  }

  // 创建错题
  async function createError(data: any) {
    try {
      loading.value = true
      const response = await errorApi.createErrorQuestion(data)
      
      if (response.success) {
        ElMessage.success('创建成功')
        return response.data
      }
    } catch (error) {
      console.error('Failed to create error:', error)
      ElMessage.error('创建失败')
    } finally {
      loading.value = false
    }
  }

  // 更新错题
  async function updateError(id: string, data: any) {
    try {
      loading.value = true
      const response = await errorApi.updateErrorQuestion(id, data)
      
      if (response.success) {
        ElMessage.success('更新成功')
        return response.data
      }
    } catch (error) {
      console.error('Failed to update error:', error)
      ElMessage.error('更新失败')
    } finally {
      loading.value = false
    }
  }

  // 删除错题
  async function deleteError(id: string) {
    try {
      loading.value = true
      const response = await errorApi.deleteErrorQuestion(id)
      
      if (response.success) {
        ElMessage.success('删除成功')
        // 从列表中移除
        errorList.value = errorList.value.filter(item => item.id !== id)
        total.value--
        return true
      }
    } catch (error) {
      console.error('Failed to delete error:', error)
      ElMessage.error('删除失败')
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    errorList,
    currentError,
    total,
    loading,
    fetchErrorList,
    fetchErrorDetail,
    createError,
    updateError,
    deleteError,
  }
})

