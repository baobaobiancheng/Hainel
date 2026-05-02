// pages/consultation/consultation.js
const conversationsApi = require('../../api/conversations')
const messagesApi = require('../../api/messages')
const pollManager = require('../../utils/poll')
const wsService = require('../../utils/websocket')
const { formatRelativeTime } = require('../../utils/helpers')

const SUGGESTS = [
  '我最近头痛，感觉头部持续胀痛...',
  '我有高血压，想了解用药注意事项',
  '胸口有点不舒服，有时心跳加速',
  '血糖偏高，饮食上需要注意什么？',
]

const WAITING_REPLY_CONTENT = '正在进行智能分析，请稍候。'
const WAITING_TIMEOUT_CONTENT = '当前分析耗时较长，请稍候；如症状明显加重或情况紧急，请及时线下就医。'
const WAITING_REPLY_TIMEOUT = 45000
const ANALYSIS_DONE_STATUSES = ['completed', 'active']
const RED_FLAG_KEYWORDS = ['胸痛', '胸闷', '呼吸困难', '喘不上气', '意识不清', '昏厥', '抽搐', '剧烈头痛', '大出血', '咯血', '呕血']

Page({
  data: {
    conversationId: null,
    conversation: null,
    messages: [],
    inputText: '',
    inputFocus: false,
    sending: false,
    loading: false,
    pollConnected: false,
    wsConnected: false,
    aiTyping: false,
    scrollTarget: '',
    avatarChar: '我',
    avatarUrl: '',
    suggests: SUGGESTS,
    keyboardShow: false,
    // 状态推送相关
    currentStatus: 'idle', // idle, analyzing, reviewing, completed
    statusMessage: '',
    waitingMessageId: '',
    healthProfileSummary: '',
    structuredIntake: null,
    structuredIntakeSummary: '',
    pendingImage: null,
  },

  onLoad(options) {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo) {
      const char = (userInfo.full_name || userInfo.username || 'U').charAt(0).toUpperCase()
      this.setData({
        avatarChar: char,
        avatarUrl: this.normalizeAvatarUrl(userInfo.avatar_url),
        healthProfileSummary: this.buildHealthProfileSummary(userInfo.health_profile),
      })
    }

    wx.setNavigationBarTitle({ title: '智能健康咨询' })

    // 支持直接 URL 传参（非 tabBar 场景）
    const conversationId = options.conversationId
    if (conversationId) {
      this.setData({ conversationId: parseInt(conversationId) })
      this.loadConversation()
      this.loadMessages()
      this.connectWs()
      this.connectPoll()
    }
  },

  normalizeAvatarUrl(url) {
    if (!url) return ''
    if (/^https?:\/\//.test(url)) return url
    const app = getApp()
    const apiBase = (app.globalData.apiBaseUrl || '').replace(/\/$/, '')
    return `${apiBase}${url.startsWith('/') ? url : `/${url}`}`
  },

  normalizeFileUrl(url) {
    if (!url) return ''
    if (/^https?:\/\//.test(url)) return url
    const app = getApp()
    const apiBase = (app.globalData.apiBaseUrl || '').replace(/\/$/, '')
    const origin = apiBase.replace(/\/api\/v\d+$/, '')
    if (url.startsWith('/api/')) return `${origin}${url}`
    return `${apiBase}${url.startsWith('/') ? url : `/${url}`}`
  },

  onShow() {
    this.refreshIntakeContext()
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }

    // 读取由首页/历史页通过缓存传来的会话ID
    const pendingId = wx.getStorageSync('pendingConversationId')
    if (pendingId) {
      wx.removeStorageSync('pendingConversationId')
      const id = parseInt(pendingId)
      if (id !== this.data.conversationId) {
        this.setData({
          conversationId: id,
          messages: [],
          conversation: null,
          inputText: '',
        })
        this.loadConversation()
        this.loadMessages()
        this.connectWs()
        this.connectPoll()
        return
      }
    }

    const pendingReportAnalysis = wx.getStorageSync('pendingReportAnalysis')
    if (pendingReportAnalysis && pendingReportAnalysis.conversationId === this.data.conversationId) {
      wx.removeStorageSync('pendingReportAnalysis')
      this.setData({
        inputText: pendingReportAnalysis.prompt || '请结合我刚上传的报告进行分析。',
      })
      setTimeout(() => this.sendMessage(), 300)
      return
    }

    if (this.data.conversationId) {
      this.connectWs()
      this.connectPoll()
    }
  },

  onHide() {
    this.disconnectWs()
    this.disconnectPoll()
    this.clearWaitingTimer()
  },
  onUnload() {
    this.disconnectWs()
    this.disconnectPoll()
    this.clearWaitingTimer()
  },

  onFocus()  { this.setData({ keyboardShow: true }) },
  onBlur()   { this.setData({ keyboardShow: false, inputFocus: false }) },

  refreshIntakeContext() {
    const userInfo = wx.getStorageSync('userInfo') || {}
    const structuredIntake = wx.getStorageSync('pendingStructuredIntake') || null
    this.setData({
      healthProfileSummary: this.buildHealthProfileSummary(userInfo.health_profile),
      structuredIntake,
      structuredIntakeSummary: this.buildStructuredIntakeSummary(structuredIntake),
    })
  },

  buildHealthProfileSummary(profile) {
    if (!profile) return ''
    const parts = []
    if (profile.gender) parts.push(profile.gender)
    const age = profile.birth_date ? this.getAge(profile.birth_date) : ''
    if (age) parts.push(`${age}岁`)
    if (profile.past_history) parts.push(`病史: ${profile.past_history}`)
    if (profile.allergies) parts.push(`过敏: ${profile.allergies}`)
    if (profile.long_term_medications) parts.push(`用药: ${profile.long_term_medications}`)
    return parts.slice(0, 4).join('，')
  },

  getAge(birthDate) {
    const birth = new Date(birthDate)
    if (Number.isNaN(birth.getTime())) return ''
    const now = new Date()
    let age = now.getFullYear() - birth.getFullYear()
    const monthDelta = now.getMonth() - birth.getMonth()
    if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < birth.getDate())) age--
    return age > 0 ? age : ''
  },

  buildStructuredIntakeSummary(intake) {
    if (!intake) return ''
    return [
      intake.main_symptom,
      intake.duration,
      intake.accompanying_symptoms,
      intake.fever,
      intake.pain_level,
    ].filter(Boolean).slice(0, 4).join('，')
  },

  openIntake() {
    wx.navigateTo({ url: '/src/pages/intake/intake' })
  },

  openHealthProfile() {
    wx.navigateTo({ url: '/src/pages/health-profile/health-profile' })
  },

  async loadConversation() {
    try {
      const conversation = await conversationsApi.getConversation(this.data.conversationId)
      this.setData({ conversation })
      wx.setNavigationBarTitle({ title: conversation.title || '智能健康咨询' })
    } catch (err) {
      console.error('加载会话失败:', err)
    }
  },

  async loadMessages() {
    this.setData({ loading: true })
    try {
      const res = await messagesApi.getMessages(this.data.conversationId, { skip: 0, limit: 100 })
      const messages = (res.items || []).map(msg => this.normalizeMessage(msg))
      this.setData({ messages, loading: false })
      this.scrollToBottom()
    } catch (err) {
      console.error('加载消息失败:', err)
      this.setData({ loading: false })
    }
  },

  connectPoll() {
    if (!this.data.conversationId) return
    if (pollManager.isConnected() && pollManager.conversationId === this.data.conversationId) {
      return
    }
    if (pollManager.isConnected()) {
      pollManager.close()
    }
    pollManager.connect(
      this.data.conversationId,
      (data) => this.handlePollMessage(data),
      ()     => this.setData({ pollConnected: true }),
      ()     => this.setData({ pollConnected: false }),
      ()     => this.setData({ pollConnected: false }),
    )
  },

  disconnectPoll() {
    pollManager.close()
    this.setData({ pollConnected: false })
  },

  // WebSocket连接
  connectWs() {
    if (!this.data.conversationId) return
    this.realtimeActive = true

    if (!this._wsHandlersBound) {
      // 监听连接成功
      wsService.onOpen(() => {
        console.log('WebSocket连接成功')
        this.setData({ wsConnected: true })
      })

      // 监听消息
      wsService.onMessage((data) => {
        console.log('收到WebSocket消息:', data)
        this.handleWsMessage(data)
      })

      // 监听错误
      wsService.onError((error) => {
        console.error('WebSocket错误:', error)
        this.setData({ wsConnected: false })
        if (this.realtimeActive) this.connectPoll()
      })

      // 监听关闭
      wsService.onClose(() => {
        console.log('WebSocket连接关闭')
        this.setData({ wsConnected: false })
        if (this.realtimeActive) this.connectPoll()
      })

      this._wsHandlersBound = true
    }

    // 连接WebSocket，长轮询会作为兜底同步消息
    wsService.connect(this.data.conversationId)
  },

  disconnectWs() {
    this.realtimeActive = false
    wsService.disconnect()
    this.setData({ wsConnected: false })
  },

  // 处理WebSocket消息
  handleWsMessage(data) {
    // 处理状态更新 - 改为对话气泡形式
    if (data.type === 'status_update') {
      this.handleStatusUpdate(data)
      return
    }

    // 处理普通消息
    if (data.type === 'new_message') {
      this.appendIncomingMessage(data.message)
    } else if (data.type === 'typing') {
      this.setData({ aiTyping: true })
    }
  },

  // 处理状态更新消息 - 对话气泡形式
  handleStatusUpdate(data) {
    const isDoneStatus = ANALYSIS_DONE_STATUSES.includes(data.status)
    if (isDoneStatus) {
      this.lastAnalysisSettledAt = Date.now()
    }

    // 更新顶部状态栏（可选保留）
    this.setData({
      currentStatus: isDoneStatus ? 'completed' : data.status,
      statusMessage: isDoneStatus ? '' : data.message
    })

    const statusMsg = {
      id: `status-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role: 'assistant',
      message_type: 'status',
      status: data.status,
      content: data.message,
      agent_name: '系统',
      timestamp: new Date().toISOString(),
      relativeTime: '刚刚',
    }

    this.clearWaitingTimer()
    // 使用浅拷贝创建新数组，避免直接修改原始数据
    const messagesWithoutWaiting = this.data.messages.filter(msg => {
      if (msg.id === this.data.waitingMessageId) return false
      return isDoneStatus ? !this.isWaitingPlaceholder(msg) : true
    })
    const existingStatusIndex = messagesWithoutWaiting.findIndex(
      m => m.message_type === 'status'
    )

    if (existingStatusIndex >= 0) {
      // 更新现有状态消息
      messagesWithoutWaiting[existingStatusIndex] = statusMsg
    } else {
      // 添加新状态消息
      messagesWithoutWaiting.push(statusMsg)
    }

    this.setData({
      messages: messagesWithoutWaiting,
      aiTyping: false,
      waitingMessageId: '',
    })
    this.scrollToBottom()

    // 诊断完成时刷新消息列表（清除状态消息，显示真实AI回复）
    if (isDoneStatus) {
      // 显示完成提示
      wx.showModal({
        title: '诊断完成',
        content: '您的诊断结果已生成，请查看详情',
        showCancel: false,
        confirmText: '查看结果'
      })
      // 延迟刷新消息列表
      setTimeout(() => {
        this.loadMessages()
      }, 2000)
    }
  },

  handlePollMessage(data) {
    if (data.type === 'new_message') {
      this.appendIncomingMessage(data.message)
    } else if (data.type === 'typing') {
      this.setData({ aiTyping: true })
    } else if (data.type === 'connected') {
      this.setData({ pollConnected: true })
    }
  },

  normalizeMessage(msg) {
    const role = typeof msg.role === 'string' ? msg.role.toLowerCase() : msg.role
    const messageType = typeof msg.message_type === 'string'
      ? msg.message_type.toLowerCase()
      : msg.message_type

    const normalized = {
      ...msg,
      role,
      message_type: messageType,
      file_url: this.normalizeFileUrl(msg.file_url),
      relativeTime: msg.relativeTime || (msg.created_at ? formatRelativeTime(msg.created_at) : '刚刚'),
    }
    const metadata = msg.metadata || msg.extra_metadata || {}
    if (role === 'assistant' && metadata.action_checklist) {
      normalized.actionChecklistSections = this.formatActionChecklist(metadata.action_checklist)
    }
    if (role === 'assistant' && metadata.red_flags && metadata.red_flags.length) {
      normalized.redFlags = metadata.red_flags
    }

    if (role === 'assistant' && messageType === 'text' && msg.content) {
      normalized.markdownHtml = this.markdownToHtml(msg.content)
    }

    return normalized
  },

  formatActionChecklist(checklist) {
    const labels = {
      observe: '需要观察',
      exams: '建议检查',
      when_to_seek_care: '何时就医',
      lifestyle: '生活注意事项',
    }
    return Object.keys(labels).map((key) => ({
      key,
      title: labels[key],
      items: Array.isArray(checklist[key]) ? checklist[key] : [],
    })).filter(section => section.items.length > 0)
  },

  appendIncomingMessage(rawMessage) {
    const incoming = this.normalizeMessage(rawMessage)
    const isUserMessage = incoming.role === 'user'
    let messages = [...this.data.messages]

    if (incoming.id && messages.some(msg => msg.id === incoming.id)) {
      return
    }

    if (isUserMessage) {
      const pendingUserIndex = messages.findIndex(
        msg => String(msg.id).startsWith('tmp-user-') && msg.content === incoming.content
      )
      if (pendingUserIndex >= 0) {
        messages[pendingUserIndex] = incoming
      } else {
        messages.push(incoming)
      }
    } else {
      if (incoming.role === 'assistant') {
        this.lastAnalysisSettledAt = Date.now()
      }
      messages = messages.filter(msg => {
        if (msg.id === this.data.waitingMessageId) return false
        if (incoming.role === 'assistant') return !this.isWaitingPlaceholder(msg)
        return true
      })
      messages.push(incoming)
      this.clearWaitingTimer()
      this.setData({
        aiTyping: false,
        waitingMessageId: '',
        currentStatus: incoming.role === 'assistant' ? 'completed' : this.data.currentStatus,
        statusMessage: incoming.role === 'assistant' ? '' : this.data.statusMessage,
      })
    }

    this.setData({ messages })
    this.scrollToBottom()
  },

  isWaitingPlaceholder(msg) {
    return Boolean(
      msg.isTemporary ||
      msg.content === WAITING_REPLY_CONTENT ||
      msg.content === WAITING_TIMEOUT_CONTENT ||
      msg.content === '正在智能分析您的问题，请稍候...'
    )
  },

  appendWaitingMessage(waitingMessageId) {
    if (this.lastAnalysisSettledAt && this.currentSendStartedAt && this.lastAnalysisSettledAt >= this.currentSendStartedAt) {
      return
    }

    const waitingMessage = {
      id: waitingMessageId,
      role: 'assistant',
      message_type: 'status',
      status: 'analyzing',
      content: WAITING_REPLY_CONTENT,
      agent_name: '健康助手',
      relativeTime: '刚刚',
      isTemporary: true,
    }

    const messages = [
      ...this.data.messages.filter(msg => msg.id !== this.data.waitingMessageId),
      waitingMessage,
    ]

    this.setData({
      messages,
      waitingMessageId,
      aiTyping: true,
      currentStatus: 'analyzing',
      statusMessage: '智能分析中...',
    })
    this.startWaitingTimer(waitingMessageId)
    this.scrollToBottom()
  },

  startWaitingTimer(waitingMessageId) {
    this.clearWaitingTimer()
    this.waitingTimer = setTimeout(() => {
      if (this.data.waitingMessageId !== waitingMessageId) return

      const messages = this.data.messages.map(msg => {
        if (msg.id !== waitingMessageId) return msg
        return {
          ...msg,
          content: WAITING_TIMEOUT_CONTENT,
          status: 'analyzing',
          relativeTime: '刚刚',
        }
      })

      this.setData({
        messages,
        aiTyping: false,
        currentStatus: 'analyzing',
        statusMessage: '智能分析仍在处理中...',
      })
      this.scrollToBottom()
    }, WAITING_REPLY_TIMEOUT)
  },

  clearWaitingTimer() {
    if (this.waitingTimer) {
      clearTimeout(this.waitingTimer)
      this.waitingTimer = null
    }
  },

  escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  },

  renderInlineMarkdown(text) {
    return this.escapeHtml(text)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/__([^_]+)__/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
  },

  markdownToHtml(content) {
    const lines = String(content || '').replace(/\r\n/g, '\n').split('\n')
    const html = []
    let paragraph = []
    let listItems = []
    let codeLines = []
    let inCodeBlock = false

    const flushParagraph = () => {
      if (!paragraph.length) return
      html.push(`<p>${paragraph.map(line => this.renderInlineMarkdown(line)).join('<br/>')}</p>`)
      paragraph = []
    }

    const flushList = () => {
      if (!listItems.length) return
      html.push(`<ul>${listItems.map(item => `<li>${this.renderInlineMarkdown(item)}</li>`).join('')}</ul>`)
      listItems = []
    }

    lines.forEach((line) => {
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          html.push(`<pre><code>${this.escapeHtml(codeLines.join('\n'))}</code></pre>`)
          codeLines = []
          inCodeBlock = false
        } else {
          flushParagraph()
          flushList()
          inCodeBlock = true
        }
        return
      }

      if (inCodeBlock) {
        codeLines.push(line)
        return
      }

      const trimmed = line.trim()
      if (!trimmed) {
        flushParagraph()
        flushList()
        return
      }

      const headingMatch = trimmed.match(/^#{1,6}\s+(.+)$/)
      if (headingMatch) {
        flushParagraph()
        flushList()
        html.push(`<p><strong>${this.renderInlineMarkdown(headingMatch[1])}</strong></p>`)
        return
      }

      const listMatch = trimmed.match(/^[-*]\s+(.+)$/)
      if (listMatch) {
        flushParagraph()
        listItems.push(listMatch[1])
        return
      }

      flushList()
      paragraph.push(trimmed)
    })

    if (inCodeBlock && codeLines.length) {
      html.push(`<pre><code>${this.escapeHtml(codeLines.join('\n'))}</code></pre>`)
    }
    flushParagraph()
    flushList()

    return html.join('')
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  useSuggest(e) {
    this.setData({ inputText: e.currentTarget.dataset.text, inputFocus: true })
  },

  hasRedFlagText(text) {
    return RED_FLAG_KEYWORDS.some(keyword => String(text || '').includes(keyword))
  },

  confirmRedFlagIfNeeded(text) {
    const intakeText = this.data.structuredIntake
      ? Object.values(this.data.structuredIntake).join(' ')
      : ''
    if (!this.hasRedFlagText(`${text} ${intakeText}`)) {
      return Promise.resolve(true)
    }
    return new Promise((resolve) => {
      wx.showModal({
        title: '可能存在急症风险',
        content: '您输入的信息包含胸痛、呼吸困难、意识异常、剧烈头痛或出血等红旗症状。建议优先线下急诊或拨打急救电话。是否仍继续提交给智能分析？',
        confirmText: '继续提交',
        cancelText: '先不提交',
        success: (res) => resolve(Boolean(res.confirm)),
        fail: () => resolve(false),
      })
    })
  },

  // 等待WebSocket连接成功的辅助方法
  async awaitWebSocketConnected() {
    return new Promise((resolve) => {
      // 如果已经连接，直接resolve
      if (this.data.wsConnected) {
        console.log('WebSocket已连接，直接发送消息')
        resolve()
        return
      }

      // 监听连接成功事件
      const onOpenHandler = () => {
        console.log('WebSocket连接已建立，等待发送消息')
        resolve()
      }

      // 保存原来的回调并添加新的
      const originalCallbacks = [...wsService.openCallbacks]
      wsService.openCallbacks = [...originalCallbacks, onOpenHandler]

      // 如果还没有连接，触发连接
      if (!wsService.isConnected && this.data.conversationId) {
        console.log('开始连接WebSocket...')
        this.connectWs()
      }

      // 最多等待5秒超时
      setTimeout(() => {
        console.log('WebSocket连接等待超时，继续发送消息')
        resolve()
      }, 5000)
    })
  },

  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text || this.data.sending) return

    const shouldContinue = await this.confirmRedFlagIfNeeded(text)
    if (!shouldContinue) return

    const sendStartedAt = Date.now()
    this.currentSendStartedAt = sendStartedAt
    const structuredIntake = this.data.structuredIntake || wx.getStorageSync('pendingStructuredIntake') || null

    let conversationId = this.data.conversationId
    if (!conversationId) {
      try {
        const conv = await conversationsApi.createConversation({
          title: text.substring(0, 30),
          chief_complaint: text,
          extra_metadata: structuredIntake ? { structured_intake: structuredIntake } : undefined,
        })
        conversationId = conv.id
        this.setData({ conversationId, conversation: conv })
        // 先连接WebSocket并等待连接成功
        this.connectWs()
        this.connectPoll()
        // 等待WebSocket连接成功后再发送消息
        await this.awaitWebSocketConnected()
      } catch {
        wx.showToast({ title: '创建会话失败', icon: 'none' })
        return
      }
    } else {
      if (structuredIntake) {
        const currentMetadata = this.data.conversation && (this.data.conversation.metadata || this.data.conversation.extra_metadata) || {}
        conversationsApi.updateConversation(conversationId, {
          extra_metadata: {
            ...currentMetadata,
            structured_intake: structuredIntake,
          },
        }).catch(err => console.warn('更新本次问诊信息失败:', err))
      }
      // 已有会话，确保WebSocket已连接
      if (!this.data.wsConnected) {
        this.connectWs()
        this.connectPoll()
        await this.awaitWebSocketConnected()
      } else {
        this.connectPoll()
      }
    }

    const pendingImage = this.data.pendingImage

    // 本地预显示用户消息（保存 tempMsg 的 ID 用于失败时删除）
    const tempMsgId = `tmp-user-${Date.now()}`
    const waitingMessageId = `tmp-waiting-${Date.now()}`
    const tempMsg = {
      id: tempMsgId,
      role: 'user',
      content: text,
      message_type: 'text',
      relativeTime: '刚刚',
    }
    this.setData({
      sending: true,
      inputText: '',
      pendingImage: null,
      messages: [...this.data.messages, tempMsg],
      currentStatus: 'analyzing',
      statusMessage: '正在提交...'
    })
    this.scrollToBottom()

    let imageUploaded = false
    let imageMessage = null
    let imageOcrText = ''
    try {
      if (pendingImage) {
        imageMessage = await messagesApi.uploadImage(conversationId, pendingImage.tempPath)
        imageOcrText = imageMessage.metadata?.ocr_result?.text || ''
        const normalizedImage = this.normalizeMessage(imageMessage)
        const withoutTempText = this.data.messages.filter(msg => msg.id !== tempMsgId)
        imageUploaded = true
        this.setData({
          messages: [...withoutTempText, normalizedImage, tempMsg],
        })
      }

      await messagesApi.sendMessage({
        conversation_id: conversationId,
        content: text,
        role: 'user',
        message_type: 'text',
        metadata: imageMessage ? {
          symptom_image_message_id: imageMessage.id,
          symptom_image_ocr_text: imageOcrText,
        } : undefined,
      })
      if (!this.lastAnalysisSettledAt || this.lastAnalysisSettledAt < sendStartedAt) {
        this.appendWaitingMessage(waitingMessageId)
      }
    } catch (err) {
      wx.showToast({ title: '发送失败', icon: 'none' })
      // 删除临时消息，恢复输入框内容
      this.clearWaitingTimer()
      const messages = this.data.messages.filter(
        msg => msg.id !== tempMsgId && msg.id !== waitingMessageId
      )
      this.setData({
        inputText: text,
        pendingImage: imageUploaded ? null : pendingImage,
        messages,
        waitingMessageId: '',
        aiTyping: false,
        currentStatus: 'idle',
        statusMessage: '',
      })
    } finally {
      this.setData({ sending: false })
    }
  },

  scrollToBottom() {
    setTimeout(() => {
      this.setData({ scrollTarget: 'msg-bottom' })
    }, 80)
  },

  async ensureConversationForUpload() {
    if (this.data.conversationId) return this.data.conversationId

    const conv = await conversationsApi.createConversation({
      title: '症状图片咨询',
      chief_complaint: '上传症状图片咨询',
    })
    this.setData({ conversationId: conv.id, conversation: conv })
    this.connectWs()
    this.connectPoll()
    return conv.id
  },

  chooseImage() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFile = res.tempFiles?.[0] || {}
        const tempPath = res.tempFilePaths?.[0] || tempFile.path || tempFile.tempFilePath
        if (!tempPath) return

        this.setData({
          pendingImage: {
            tempPath,
            name: tempFile.name || '症状图片',
            size: tempFile.size || 0,
          },
          inputFocus: true,
        })
      },
    })
  },

  removePendingImage() {
    this.setData({ pendingImage: null })
  },

  async uploadReport() {
    let conversationId = this.data.conversationId

    // 如果没有会话，先创建一个新会话
    if (!conversationId) {
      try {
        wx.showLoading({ title: '创建会话...' })
        const res = await conversationsApi.createConversation({
          title: '医疗报告咨询',
          chief_complaint: '上传报告咨询',
        })
        conversationId = res.id
        wx.hideLoading()

        // 更新当前会话ID
        this.setData({ conversationId, conversation: res })
      } catch (err) {
        wx.hideLoading()
        wx.showToast({ title: '创建会话失败', icon: 'none' })
        console.error('创建会话失败:', err)
        return
      }
    }

    wx.navigateTo({ url: `/src/pages/upload/upload?conversationId=${conversationId}` })
  },

  previewImage(e) {
    wx.previewImage({ urls: [e.currentTarget.dataset.url] })
  },
})
