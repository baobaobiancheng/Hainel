import request from './request'

/**
 * 获取医生负责的患者列表
 * 后端路由: GET /api/v1/doctors/patients
 * 支持参数: page, page_size, search, status(会话状态过滤)
 */
export const getPatients = (params) => {
  return request({
    url: '/v1/doctors/patients',
    method: 'get',
    params
  })
}

/**
 * 获取患者详情摘要（含会话统计）
 * 后端路由: GET /api/v1/doctors/patients/{id}/summary
 * 返回结构: { patient: {...}, conversation_stats: {...}, recent_conversations: [...] }
 */
export const getPatientDetail = (id) => {
  return request({
    url: `/v1/doctors/patients/${id}/summary`,
    method: 'get'
  })
}

export const updatePatient = (id, data) => {
  return request({
    url: `/v1/doctors/patients/${id}`,
    method: 'put',
    data
  })
}
