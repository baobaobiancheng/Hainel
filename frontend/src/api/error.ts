/**
 * 错题相关 API
 */
import { request } from '@/utils/request'
import type {
  ErrorQuestion,
  ErrorQuestionCreate,
  ErrorQuestionUpdate,
  ErrorQuestionQuery,
  PaginatedResponse,
  ApiResponse,
} from '@/types/api'

export const errorApi = {
  // 获取错题列表
  getErrorQuestions(
    params: ErrorQuestionQuery
  ): Promise<ApiResponse<PaginatedResponse<ErrorQuestion>>> {
    return request.get('/v1/errors', { params })
  },

  // 获取错题详情
  getErrorQuestion(id: string): Promise<ApiResponse<ErrorQuestion>> {
    return request.get(`/v1/errors/${id}`)
  },

  // 创建错题
  createErrorQuestion(data: ErrorQuestionCreate): Promise<ApiResponse<ErrorQuestion>> {
    return request.post('/v1/errors', data)
  },

  // 更新错题
  updateErrorQuestion(
    id: string,
    data: ErrorQuestionUpdate
  ): Promise<ApiResponse<ErrorQuestion>> {
    return request.put(`/v1/errors/${id}`, data)
  },

  // 删除错题
  deleteErrorQuestion(id: string): Promise<ApiResponse<null>> {
    return request.delete(`/v1/errors/${id}`)
  },

  // OCR 识别错题
  ocrErrorQuestion(file: File): Promise<ApiResponse<ErrorQuestion>> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/v1/errors/ocr', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

