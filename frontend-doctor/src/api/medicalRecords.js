import request from './request'

export const getMedicalRecords = (params) => {
  return request({
    url: '/v1/medical-records',
    method: 'get',
    params
  })
}

export const getMedicalRecordDetail = (id) => {
  return request({
    url: `/v1/medical-records/${id}`,
    method: 'get'
  })
}

export const createMedicalRecord = (data) => {
  return request({
    url: '/v1/medical-records',
    method: 'post',
    data
  })
}

export const updateMedicalRecord = (id, data) => {
  return request({
    url: `/v1/medical-records/${id}`,
    method: 'put',
    data
  })
}

export const updateMedicalRecordStatus = (id, status) => {
  return request({
    url: `/v1/medical-records/${id}/status`,
    method: 'patch',
    data: { status }
  })
}

export const reviewMedicalRecord = (id, data) => {
  return request({
    url: `/v1/medical-records/${id}/review`,
    method: 'post',
    data
  })
}

export const archiveMedicalRecord = (id) => {
  return request({
    url: `/v1/medical-records/${id}/archive`,
    method: 'post'
  })
}

export const qualityCheckMedicalRecord = (id) => {
  return request({
    url: `/v1/medical-records/${id}/quality-check`,
    method: 'post'
  })
}

export const assistMedicalRecord = (id) => {
  return request({
    url: `/v1/medical-records/${id}/assist`,
    method: 'post'
  })
}

export const submitMedicalRecordAgentFeedback = (id, data) => {
  return request({
    url: `/v1/medical-records/${id}/agent-feedback`,
    method: 'post',
    data
  })
}

export const deleteMedicalRecord = (id) => {
  return request({
    url: `/v1/medical-records/${id}`,
    method: 'delete'
  })
}

export const getMedicalRecordDraft = (conversationId) => {
  return request({
    url: `/v1/conversations/${conversationId}/medical-record-draft`,
    method: 'get'
  })
}
