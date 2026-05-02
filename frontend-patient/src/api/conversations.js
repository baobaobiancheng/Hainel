/**
 * 会话相关API
 */

const { get, post, put, patch, del } = require('../utils/request')

/**
 * 创建会话
 * @param {Object} data 会话数据
 * @returns {Promise}
 */
function createConversation(data) {
  return post('/conversations', data)
}

/**
 * 获取会话列表
 * @param {Object} params 查询参数
 * @returns {Promise}
 */
function getConversations(params = {}) {
  return get('/conversations', params)
}

/**
 * 获取会话详情
 * @param {Number} conversationId 会话ID
 * @returns {Promise}
 */
function getConversation(conversationId) {
  return get(`/conversations/${conversationId}`)
}

/**
 * 更新会话
 * @param {Number} conversationId 会话ID
 * @param {Object} data 更新数据
 * @returns {Promise}
 */
function updateConversation(conversationId, data) {
  return put(`/conversations/${conversationId}`, data)
}

/**
 * 更新会话状态
 * @param {Number} conversationId 会话ID
 * @param {Object} data 状态数据
 * @returns {Promise}
 */
function updateConversationStatus(conversationId, data) {
  return patch(`/conversations/${conversationId}/status`, data)
}

/**
 * 删除会话
 * @param {Number} conversationId 会话ID
 * @returns {Promise}
 */
function deleteConversation(conversationId) {
  return del(`/conversations/${conversationId}`)
}

module.exports = {
  createConversation,
  getConversations,
  getConversation,
  updateConversation,
  updateConversationStatus,
  deleteConversation,
}

