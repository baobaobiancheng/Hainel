/**
 * HTTP 长轮询工具
 * 封装微信小程序的 HTTP 请求，用于实时消息推送（替代 WebSocket）
 */

const app = getApp()

class PollManager {
  constructor() {
    this.conversationId = null
    this.isPolling = false
    this.lastMessageId = null
    this.pollTimer = null
    this.pollTimeout = 30 // 长轮询超时时间（秒）
    this.retryDelay = 1000 // 重试延迟（毫秒）
    this.maxRetryDelay = 5000 // 最大重试延迟（毫秒）
    this.currentRetryDelay = this.retryDelay
    this.messageHandlers = []
    this.onConnectCallback = null
    this.onErrorCallback = null
    this.onCloseCallback = null
  }

  /**
   * 开始轮询
   * @param {Number} conversationId 会话ID
   * @param {Function} onMessage 消息回调
   * @param {Function} onConnect 连接成功回调
   * @param {Function} onError 错误回调
   * @param {Function} onClose 关闭回调
   */
  connect(conversationId, onMessage, onConnect, onError, onClose) {
    if (this.isPolling) {
      console.log('轮询已在进行中')
      return
    }

    const token = wx.getStorageSync('token') || app.globalData.token
    if (!token) {
      console.error('未找到token，无法开始轮询')
      if (onError) onError(new Error('未找到token'))
      return
    }

    this.conversationId = conversationId
    this.lastMessageId = null
    this.currentRetryDelay = this.retryDelay

    // 回调存储
    this._onMessage = onMessage
    this._onConnect = onConnect
    this._onError = onError
    this._onClose = onClose

    console.log('开始长轮询，会话ID:', conversationId)

    this.isPolling = true

    // 首次连接回调
    if (onConnect) onConnect()

    // 开始轮询
    this._startPolling()
  }

  /**
   * 开始轮询
   */
  _startPolling() {
    if (!this.isPolling || !this.conversationId) {
      return
    }

    const token = wx.getStorageSync('token') || app.globalData.token

    // 首先获取初始消息
    this._fetchMessages(token, true)
  }

  /**
   * 获取消息
   * @param {String} token 认证token
   * @param {Boolean} isInitial 是否是初始请求
   */
  _fetchMessages(token, isInitial = false) {
    if (!this.isPolling) {
      return
    }

    const url = `${app.globalData.apiBaseUrl}/poll/conversation/${this.conversationId}/messages`
    const params = new Object()

    if (this.lastMessageId !== null) {
      params.last_message_id = this.lastMessageId
    }

    wx.request({
      url: url,
      method: 'GET',
      data: params,
      timeout: 35000,
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200) {
          const data = res.data
          if (data.messages && data.messages.length > 0) {
            // 更新最后消息ID
            const messages = data.messages
            this.lastMessageId = messages[messages.length - 1].id

            console.log('获取到新消息:', messages.length, '条')

            // 回调消息
            messages.forEach(msg => {
              const messageData = {
                type: 'new_message',
                conversation_id: this.conversationId,
                message: msg
              }

              if (this._onMessage) {
                this._onMessage(messageData)
              }

              // 调用所有注册的消息处理器
              this.messageHandlers.forEach(handler => {
                try {
                  handler(messageData)
                } catch (err) {
                  console.error('消息处理器执行错误:', err)
                }
              })
            })

            // 重置重试延迟
            this.currentRetryDelay = this.retryDelay
          }

          // 立即发起下一次轮询
          this._longPoll()
        } else {
          console.error('获取消息失败:', res.statusCode, res.data)
          this._handleError(res)
        }
      },
      fail: (err) => {
        console.error('请求失败:', err)
        this._handleError(err)
      }
    })
  }

  /**
   * 长轮询
   */
  _longPoll() {
    if (!this.isPolling || !this.conversationId) {
      return
    }

    const token = wx.getStorageSync('token') || app.globalData.token
    const url = `${app.globalData.apiBaseUrl}/poll/conversation/${this.conversationId}`

    wx.request({
      url: url,
      method: 'POST',
      data: {
        last_message_id: this.lastMessageId,
        timeout: this.pollTimeout
      },
      timeout: 35000,
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200) {
          const data = res.data

          if (data.type === 'new_message' && data.has_new) {
            // 有新消息，立即获取
            console.log('收到新消息通知')
            this._fetchMessages(token)
          } else if (data.type === 'timeout') {
            // 超时，继续轮询
            this._longPoll()
          } else {
            // 其他情况，继续轮询
            this._longPoll()
          }
        } else if (res.statusCode === 403 || res.statusCode === 401) {
          // 认证失败，停止轮询
          console.error('认证失败，停止轮询')
          this._handleError({ message: '认证失败' })
        } else {
          console.error('轮询失败:', res.statusCode)
          this._handleError(res)
        }
      },
      fail: (err) => {
        console.error('轮询请求失败:', err)
        this._handleError(err)
      }
    })
  }

  /**
   * 处理错误
   * @param {Object} err 错误信息
   */
  _handleError(err) {
    if (!this.isPolling) {
      return
    }

    // 指数退避
    const delay = this.currentRetryDelay
    this.currentRetryDelay = Math.min(this.currentRetryDelay * 2, this.maxRetryDelay)

    console.log(`轮询错误，${delay/1000}秒后重试...`)

    if (this._onError) {
      this._onError(err)
    }

    // 延迟后重试
    setTimeout(() => {
      if (this.isPolling) {
        this._longPoll()
      }
    }, delay)
  }

  /**
   * 发送消息（通过 HTTP API）
   * @param {Object} message 消息内容
   * @returns {Promise} 发送结果
   */
  sendMessage(message) {
    return new Promise((resolve, reject) => {
      if (!this.conversationId) {
        reject(new Error('未连接到会话'))
        return
      }

      const token = wx.getStorageSync('token') || app.globalData.token
      const url = `${app.globalData.apiBaseUrl}/messages`

      wx.request({
        url: url,
        method: 'POST',
        data: {
          conversation_id: this.conversationId,
          content: message.content || message,
          message_type: message.message_type || 'text'
        },
        header: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.statusCode === 200 || res.statusCode === 201) {
            console.log('消息发送成功')
            resolve(res.data)
          } else {
            console.error('消息发送失败:', res.statusCode, res.data)
            reject(res.data)
          }
        },
        fail: (err) => {
          console.error('消息发送请求失败:', err)
          reject(err)
        }
      })
    })
  }

  /**
   * 发送消息（别名方法）
   * @param {Object} data 消息数据
   */
  send(data) {
    return this.sendMessage(data)
  }

  /**
   * 关闭轮询
   */
  close() {
    console.log('关闭轮询')

    this.isPolling = false
    this.conversationId = null
    this.lastMessageId = null
    this.currentRetryDelay = this.retryDelay

    if (this._onClose) {
      this._onClose()
    }

    // 清理回调
    this._onMessage = null
    this._onConnect = null
    this._onError = null
    this._onClose = null
  }

  /**
   * 注册消息处理器
   * @param {Function} handler 消息处理函数
   */
  onMessage(handler) {
    if (typeof handler === 'function') {
      this.messageHandlers.push(handler)
    }
  }

  /**
   * 移除消息处理器
   * @param {Function} handler 消息处理函数
   */
  offMessage(handler) {
    const index = this.messageHandlers.indexOf(handler)
    if (index > -1) {
      this.messageHandlers.splice(index, 1)
    }
  }

  /**
   * 获取连接状态
   * @returns {Boolean} 是否正在轮询
   */
  isConnected() {
    return this.isPolling
  }
}

// 创建单例
const pollManager = new PollManager()

module.exports = pollManager
