import axios from 'axios'
import request from './request'

export const buildTrainingDataset = (payload) => {
  return request({
    url: '/v1/agents/training/dataset/build',
    method: 'post',
    data: payload
  })
}

export const listTrainingDatasets = () => {
  return request({
    url: '/v1/agents/training/datasets',
    method: 'get'
  })
}

export const getTrainingDataset = (datasetId) => {
  return request({
    url: `/v1/agents/training/datasets/${datasetId}`,
    method: 'get'
  })
}

export const runTraining = (payload) => {
  const data = {
    agent_type: payload.agent_type,
    dataset_id: payload.dataset_id,
    limit: payload.limit,
    activate: Boolean(payload.auto_activate)
  }

  return request({
    url: '/v1/agents/training/run',
    method: 'post',
    data
  })
}

export const evaluateTraining = (payload) => {
  return request({
    url: '/v1/agents/training/evaluate',
    method: 'post',
    data: payload
  })
}

export const getTrainingRunStatus = (runId) => {
  return request({
    url: `/v1/agents/training/runs/${runId}`,
    method: 'get'
  })
}

export const activatePolicy = (policyType, payload) => {
  return request({
    url: `/v1/agents/policies/${policyType}/activate`,
    method: 'post',
    data: {
      version: payload.policy_version
    }
  })
}

export const listPolicyVersions = (policyType) => {
  return request({
    url: `/v1/agents/policies/${policyType}/versions`,
    method: 'get'
  })
}

export const getModelConfig = () => {
  return request({
    url: '/v1/agents/models/config',
    method: 'get'
  })
}

export const updateModelConfig = (payload) => {
  return request({
    url: '/v1/agents/models/config',
    method: 'patch',
    data: payload
  })
}

export const testModelConnection = (payload) => {
  return request({
    url: '/v1/agents/models/test',
    method: 'post',
    data: payload
  })
}

export const getModelTokenUsage = (params) => {
  return request({
    url: '/v1/agents/models/token-usage',
    method: 'get',
    params
  })
}

export const downloadTrainingExport = async (fileName) => {
  const token = localStorage.getItem('token')
  const response = await axios({
    url: `/api/v1/agents/training/exports/${encodeURIComponent(fileName)}`,
    method: 'get',
    responseType: 'blob',
    headers: token
      ? {
          Authorization: `Bearer ${token}`
        }
      : {}
  })

  return response.data
}
