/**
 * WebSocket 服务
 * 医生端WebSocket连接管理
 */

import { getToken } from '@/api/auth'

class WebSocketService {
  constructor() {
    this.ws = null
    this.url = ''
    this.reconnectInterval = 3000 // 重连间隔（毫秒）
    this.reconnectTimer = null
    this.messageCallbacks = []
    this.errorCallbacks = []
    this.closeCallbacks = []
    this.openCallbacks = []
    this.isConnected = false
    this.heartbeatTimer = null
    this.heartbeatInterval = 30000 // 心跳间隔（30秒）
    this.manualClose = false
  }

  /**
   * 连接到WebSocket服务器
   * @param {string} baseUrl - WebSocket服务器地址
   */
  connect(baseUrl = '') {
    if (this.ws && [WebSocket.OPEN, WebSocket.CONNECTING].includes(this.ws.readyState)) {
      console.log('WebSocket已连接或正在连接')
      return
    }

    // 获取token
    const token = getToken()
    if (!token) {
      console.error('未登录，无法建立WebSocket连接')
      return
    }

    // 构建WebSocket URL
    const wsUrl = baseUrl || this._buildWsUrl()
    console.log('正在连接WebSocket:', wsUrl)
    this.manualClose = false

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = (event) => {
        console.log('WebSocket连接已打开')
        this.isConnected = true

        // 发送认证消息
        this.send({
          type: 'auth',
          token: token
        })

        // 启动心跳
        this._startHeartbeat()

        // 触发连接成功回调
        this.openCallbacks.forEach(cb => cb(event))
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
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
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        this.errorCallbacks.forEach(cb => cb(error))
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket连接已关闭', event.code, event.reason)
        this.isConnected = false

        // 停止心跳
        this._stopHeartbeat()

        // 触发关闭回调
        this.closeCallbacks.forEach(cb => cb(event))

        // 自动重连
        if (!this.manualClose) {
          this._reconnect()
        }
      }
    } catch (error) {
      console.error('创建WebSocket失败:', error)
    }
  }

  /**
   * 断开WebSocket连接
   */
  disconnect(options = {}) {
    const { clearCallbacks = false } = options
    this.manualClose = true

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this._stopHeartbeat()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnected = false

    if (clearCallbacks) {
      this._clearCallbacks()
    }
  }

  /**
   * 发送消息
   * @param {object} data - 消息数据
   */
  send(data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，无法发送消息')
      return false
    }

    try {
      this.ws.send(JSON.stringify(data))
      return true
    } catch (error) {
      console.error('发送WebSocket消息失败:', error)
      return false
    }
  }

  /**
   * 注册消息回调
   * @param {function} callback - 回调函数
   */
  onMessage(callback) {
    if (!this.messageCallbacks.includes(callback)) {
      this.messageCallbacks.push(callback)
    }
    return () => this.offMessage(callback)
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
    if (!this.errorCallbacks.includes(callback)) {
      this.errorCallbacks.push(callback)
    }
    return () => this.offError(callback)
  }

  /**
   * 移除错误回调
   * @param {function} callback - 回调函数
   */
  offError(callback) {
    const index = this.errorCallbacks.indexOf(callback)
    if (index > -1) {
      this.errorCallbacks.splice(index, 1)
    }
  }

  /**
   * 注册关闭回调
   * @param {function} callback - 回调函数
   */
  onClose(callback) {
    if (!this.closeCallbacks.includes(callback)) {
      this.closeCallbacks.push(callback)
    }
    return () => this.offClose(callback)
  }

  /**
   * 移除关闭回调
   * @param {function} callback - 回调函数
   */
  offClose(callback) {
    const index = this.closeCallbacks.indexOf(callback)
    if (index > -1) {
      this.closeCallbacks.splice(index, 1)
    }
  }

  /**
   * 注册连接成功回调
   * @param {function} callback - 回调函数
   */
  onOpen(callback) {
    if (!this.openCallbacks.includes(callback)) {
      this.openCallbacks.push(callback)
    }
    return () => this.offOpen(callback)
  }

  /**
   * 移除连接成功回调
   * @param {function} callback - 回调函数
   */
  offOpen(callback) {
    const index = this.openCallbacks.indexOf(callback)
    if (index > -1) {
      this.openCallbacks.splice(index, 1)
    }
  }

  /**
   * 构建WebSocket URL
   */
  _buildWsUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws/doctor`
  }

  /**
   * 启动心跳
   */
  _startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'heartbeat' })
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
   * 清理所有回调，避免重新登录后重复通知。
   */
  _clearCallbacks() {
    this.messageCallbacks = []
    this.errorCallbacks = []
    this.closeCallbacks = []
    this.openCallbacks = []
  }

  /**
   * 自动重连
   */
  _reconnect() {
    if (this.reconnectTimer) {
      return
    }

    console.log(`将在 ${this.reconnectInterval / 1000} 秒后尝试重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, this.reconnectInterval)
  }
}

// 创建全局WebSocket服务实例
const wsService = new WebSocketService()

export default wsService
