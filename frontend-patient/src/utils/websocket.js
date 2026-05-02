/**
 * WebSocket 服务
 * 微信小程序WebSocket连接管理
 */

const authApi = require('../api/auth')

class WebSocketService {
  constructor() {
    this.socketTask = null
    this.isConnected = false
    this.isConnecting = false
    this.reconnectInterval = 3000 // 重连间隔（毫秒）
    this.reconnectTimer = null
    this.messageCallbacks = []
    this.errorCallbacks = []
    this.closeCallbacks = []
    this.openCallbacks = []
    this.heartbeatTimer = null
    this.heartbeatInterval = 30000 // 心跳间隔（30秒）
    this.currentConversationId = null
  }

  /**
   * 连接到WebSocket服务器
   * @param {number} conversationId - 会话ID
   * @param {string} baseUrl - WebSocket服务器地址（可选）
   */
  connect(conversationId, baseUrl = '') {
    // 防止重复连接
    if (this.isConnecting) {
      console.log('WebSocket正在连接中，跳过')
      return
    }

    // 如果已有连接，先断开
    if (this.socketTask && this.isConnected) {
      console.log('WebSocket已连接，正在关闭现有连接...')
      this.disconnect()
      // 等待断开完成
      return this._delayedConnect(conversationId, baseUrl)
    }

    this.isConnecting = true
    this.currentConversationId = conversationId

    // 获取token
    const token = authApi.getToken()
    if (!token) {
      console.error('未登录，无法建立WebSocket连接')
      this.isConnecting = false
      return
    }

    // 构建WebSocket URL
    const wsUrl = baseUrl || this._buildWsUrl()
    console.log('正在连接WebSocket:', wsUrl)

    try {
      this.socketTask = wx.connectSocket({
        url: wsUrl,
        header: {
          'Authorization': 'Bearer ' + token
        }
      })

      this.socketTask.onOpen((res) => {
        console.log('WebSocket连接已打开', res)
        this.isConnected = true
        this.isConnecting = false

        // 发送认证消息
        this.send({
          type: 'auth',
          token: token
        })

        // 启动心跳
        this._startHeartbeat()

        // 触发连接成功回调
        this.openCallbacks.forEach(cb => cb(res))
      })

      this.socketTask.onMessage((res) => {
        try {
          const data = JSON.parse(res.data)
          console.log('收到WebSocket消息:', data)

          // 处理认证响应
          if (data.type === 'connected') {
            console.log('WebSocket认证成功:', data)
            return
          }

          // 处理心跳响应
          if (data.type === 'heartbeat_ack') {
            console.log('心跳响应:', data)
            return
          }

          // 触发消息回调
          this.messageCallbacks.forEach(cb => cb(data))
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
        }
      })

      this.socketTask.onError((res) => {
        console.error('WebSocket错误:', res)
        this.errorCallbacks.forEach(cb => cb(res))
      })

      this.socketTask.onClose((res) => {
        console.log('WebSocket连接已关闭', res)
        this.isConnected = false

        // 停止心跳
        this._stopHeartbeat()

        // 触发关闭回调
        this.closeCallbacks.forEach(cb => cb(res))

        // 自动重连
        this._reconnect()
      })
    } catch (error) {
      console.error('创建WebSocket失败:', error)
    }
  }

  /**
   * 断开WebSocket连接
   */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this._stopHeartbeat()

    if (this.socketTask) {
      try {
        wx.closeSocket()
      } catch (e) {
        console.warn('关闭WebSocket失败:', e)
      }
      this.socketTask = null
    }

    this.isConnected = false
    this.isConnecting = false
    this.currentConversationId = null
  }

  /**
   * 发送消息
   * @param {object} data - 消息数据
   * @returns {Promise}
   */
  send(data) {
    if (!this.socketTask || !this.isConnected) {
      console.warn('WebSocket未连接，无法发送消息')
      return Promise.reject(new Error('WebSocket未连接'))
    }

    return new Promise((resolve, reject) => {
      this.socketTask.send({
        data: JSON.stringify(data),
        success: () => {
          console.log('WebSocket消息发送成功')
          resolve()
        },
        fail: (err) => {
          console.error('WebSocket消息发送失败:', err)
          reject(err)
        }
      })
    })
  }

  /**
   * 注册消息回调
   * @param {function} callback - 回调函数
   */
  onMessage(callback) {
    this.messageCallbacks.push(callback)
  }

  /**
   * 移除消息回调
   * @param {function} callback - 回调函数
   */
  offMessage(callback) {
    const index = this.messageCallbacks.indexOf(callback)
    if (index > -1) {
      this.messageCallbacks.splice(index, 1)
    }
  }

  /**
   * 注册错误回调
   * @param {function} callback - 回调函数
   */
  onError(callback) {
    this.errorCallbacks.push(callback)
  }

  /**
   * 注册关闭回调
   * @param {function} callback - 回调函数
   */
  onClose(callback) {
    this.closeCallbacks.push(callback)
  }

  /**
   * 注册连接成功回调
   * @param {function} callback - 回调函数
   */
  onOpen(callback) {
    this.openCallbacks.push(callback)
  }

  /**
   * 构建WebSocket URL
   */
  _buildWsUrl() {
    // 获取当前环境配置的基础URL
    // 开发环境使用ws://localhost:8001，生产环境需要配置
    const app = getApp()
    const isDev = app.globalData.apiBaseUrl && app.globalData.apiBaseUrl.includes('localhost')

    let host = 'localhost:8001'
    if (!isDev) {
      // 生产环境需要配置实际的WebSocket服务器地址
      host = 'your-production-server.com'
    }

    return `ws://${host}/ws/consultation`
  }

  /**
   * 启动心跳
   */
  _startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'heartbeat' }).catch(() => {
          console.error('发送心跳失败')
        })
      }
    }, this.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 延迟重连
   */
  _delayedConnect(conversationId, baseUrl) {
    setTimeout(() => {
      this.connect(conversationId, baseUrl)
    }, 500)
  }

  /**
   * 自动重连
   */
  _reconnect() {
    if (this.reconnectTimer) {
      return
    }

    if (!this.currentConversationId) {
      console.log('无会话ID，不进行重连')
      return
    }

    console.log(`将在 ${this.reconnectInterval / 1000} 秒后尝试重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect(this.currentConversationId)
    }, this.reconnectInterval)
  }
}

// 创建全局WebSocket服务实例
const wsService = new WebSocketService()

module.exports = wsService
