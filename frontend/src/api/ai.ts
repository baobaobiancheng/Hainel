/**
 * AI 分析相关 API
 */
import { request } from '@/utils/request'
import type { ApiResponse } from '@/types/api'

export const aiApi = {
  // 分析错题
  analyzeError(questionId: string, analysisTypes: string[]): Promise<ApiResponse<any>> {
    return request.post('/v1/ai/analyze', {
      question_id: questionId,
      analysis_types: analysisTypes,
    })
  },

  // 查找相似题
  findSimilarQuestions(questionId: string, limit: number = 5): Promise<ApiResponse<any>> {
    return request.post('/v1/ai/similar', null, {
      params: { question_id: questionId, limit },
    })
  },

  // 生成解题思路
  generateExplanation(questionId: string): Promise<ApiResponse<any>> {
    return request.post('/v1/ai/explain', null, {
      params: { question_id: questionId },
    })
  },
}

