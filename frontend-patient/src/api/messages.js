/**
 * 消息相关API
 */

const { get, post, put, del, post: postRequest } = require('../utils/request')

/**
 * 发送消息
 * @param {Object} data 消息数据
 * @returns {Promise}
 */
function sendMessage(data) {
  return post('/messages', data, { timeout: 60000 })
}

/**
 * 上传症状图片消息
 * @param {Number} conversationId 会话ID
 * @param {string} filePath 图片临时路径
 * @returns {Promise}
 */
function uploadImage(conversationId, filePath) {
  return new Promise((resolve, reject) => {
    const app = getApp()
    const token = wx.getStorageSync('token') || app.globalData.token

    wx.uploadFile({
      url: `${app.globalData.apiBaseUrl}/messages/image`,
      filePath,
      name: 'file',
      formData: { conversation_id: conversationId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(JSON.parse(res.data || '{}'))
          return
        }

        let message = `图片上传失败 (${res.statusCode})`
        try {
          const data = JSON.parse(res.data || '{}')
          message = data.detail || data.message || message
        } catch { /* ignore */ }
        reject(new Error(message))
      },
      fail: reject,
    })
  })
}

/**
 * 获取会话消息列表
 * @param {Number} conversationId 会话ID
 * @param {Object} params 查询参数
 * @returns {Promise}
 */
function getMessages(conversationId, params = {}) {
  return get(`/messages/conversation/${conversationId}`, params)
}

/**
 * 获取消息详情
 * @param {Number} messageId 消息ID
 * @returns {Promise}
 */
function getMessage(messageId) {
  return get(`/messages/${messageId}`)
}

/**
 * 更新消息
 * @param {Number} messageId 消息ID
 * @param {Object} data 更新数据
 * @returns {Promise}
 */
function updateMessage(messageId, data) {
  return put(`/messages/${messageId}`, data)
}

/**
 * 标记消息为已读
 * @param {Array} messageIds 消息ID数组
 * @returns {Promise}
 */
function markMessagesAsRead(messageIds) {
  return postRequest('/messages/mark-read', { message_ids: messageIds })
}

/**
 * 获取未读消息数量
 * @param {Number} conversationId 会话ID
 * @returns {Promise}
 */
function getUnreadCount(conversationId) {
  return get(`/messages/conversation/${conversationId}/unread-count`)
}

/**
 * 删除消息
 * @param {Number} messageId 消息ID
 * @returns {Promise}
 */
function deleteMessage(messageId) {
  return del(`/messages/${messageId}`)
}

module.exports = {
  sendMessage,
  uploadImage,
  getMessages,
  getMessage,
  updateMessage,
  markMessagesAsRead,
  getUnreadCount,
  deleteMessage,
}

