import request from './request'

export const searchKnowledge = (params) => {
  return request({
    url: '/v1/knowledge/search',
    method: 'get',
    params
  })
}

export const getKnowledgeGraph = (entity, params = {}) => {
  return request({
    url: '/v1/knowledge/graph',
    method: 'get',
    params: { entity, ...params }
  })
}

export const getClinicalGuidelines = (params) => {
  return request({
    url: '/v1/knowledge/guidelines',
    method: 'get',
    params
  })
}

// 知识库管理接口
export const importDocument = (formData) => {
  return request({
    url: '/v1/knowledge/import/file',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export const importDirectory = (params) => {
  return request({
    url: '/v1/knowledge/import/directory',
    method: 'post',
    params
  })
}

export const getKnowledgeStats = () => {
  return request({
    url: '/v1/knowledge/stats',
    method: 'get'
  })
}

