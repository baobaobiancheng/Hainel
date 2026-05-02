import request from './request'

export const getDiagnosisContext = (conversationId) => {
  return request({
    url: `/v1/conversations/${conversationId}/diagnosis-context`,
    method: 'get'
  })
}

export const submitDiagnosisAgentFeedback = (conversationId, data) => {
  return request({
    url: `/v1/conversations/${conversationId}/agent-feedback`,
    method: 'post',
    data
  })
}
