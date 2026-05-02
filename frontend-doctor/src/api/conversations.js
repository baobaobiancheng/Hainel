import request from './request'

/**
 * 获取医生负责的会话列表（包含 patient_name 等完整信息）
 * 使用 /doctors/conversations 接口，比通用接口返回更多医生视角数据
 */
export const getConversations = (params) => {
  return request({
    url: '/v1/doctors/conversations',
    method: 'get',
    params
  })
}

export const getConversationDetail = (id) => {
  return request({
    url: `/v1/conversations/${id}`,
    method: 'get'
  })
}

/**
 * 获取会话消息列表
 * 后端路由: GET /api/v1/messages/conversation/{conversation_id}
 */
export const getConversationMessages = (id, params) => {
  return request({
    url: `/v1/messages/conversation/${id}`,
    method: 'get',
    params
  })
}

/**
 * 更新会话状态
 * 后端路由: PATCH /api/v1/conversations/{id}/status
 */
export const updateConversationStatus = (id, status) => {
  return request({
    url: `/v1/conversations/${id}/status`,
    method: 'patch',
    data: { status }
  })
}
