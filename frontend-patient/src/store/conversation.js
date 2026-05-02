/**
 * 会话状态管理
 */

const conversationsApi = require('../api/conversations')
const messagesApi = require('../api/messages')

// 状态
const state = {
  conversations: [], // 会话列表
  currentConversation: null, // 当前会话
  messages: [], // 当前会话的消息列表
  unreadCount: 0, // 未读消息数
  loading: false, // 加载状态
}

// 获取器
const getters = {
  // 获取会话列表
  getConversations: (state) => state.conversations,
  
  // 获取当前会话
  getCurrentConversation: (state) => state.currentConversation,
  
  // 获取消息列表
  getMessages: (state) => state.messages,
  
  // 获取未读消息数
  getUnreadCount: (state) => state.unreadCount,
  
  // 获取加载状态
  isLoading: (state) => state.loading,
}

// 操作
const actions = {
  /**
   * 加载会话列表
   */
  async loadConversations({ commit }, params = {}) {
    commit('setLoading', true)
    try {
      const res = await conversationsApi.getConversations(params)
      commit('setConversations', res.items || [])
      return res
    } catch (err) {
      console.error('加载会话列表失败:', err)
      throw err
    } finally {
      commit('setLoading', false)
    }
  },

  /**
   * 创建会话
   */
  async createConversation({ commit, dispatch }, data) {
    try {
      const conversation = await conversationsApi.createConversation(data)
      // 重新加载会话列表
      await dispatch('loadConversations')
      return conversation
    } catch (err) {
      console.error('创建会话失败:', err)
      throw err
    }
  },

  /**
   * 加载会话详情
   */
  async loadConversation({ commit }, conversationId) {
    commit('setLoading', true)
    try {
      const conversation = await conversationsApi.getConversation(conversationId)
      commit('setCurrentConversation', conversation)
      return conversation
    } catch (err) {
      console.error('加载会话详情失败:', err)
      throw err
    } finally {
      commit('setLoading', false)
    }
  },

  /**
   * 加载消息列表
   */
  async loadMessages({ commit }, { conversationId, params = {} }) {
    commit('setLoading', true)
    try {
      const res = await messagesApi.getMessages(conversationId, params)
      commit('setMessages', res.items || [])
      return res
    } catch (err) {
      console.error('加载消息列表失败:', err)
      throw err
    } finally {
      commit('setLoading', false)
    }
  },

  /**
   * 发送消息
   */
  async sendMessage({ commit, state }, { conversationId, content, messageType = 'text' }) {
    try {
      const message = await messagesApi.sendMessage({
        conversation_id: conversationId,
        content,
        role: 'user',
        message_type: messageType,
      })
      
      // 添加到消息列表
      commit('addMessage', message)
      return message
    } catch (err) {
      console.error('发送消息失败:', err)
      throw err
    }
  },

  /**
   * 添加消息（用于WebSocket推送）
   */
  addMessage({ commit }, message) {
    commit('addMessage', message)
  },

  /**
   * 更新消息
   */
  updateMessage({ commit }, message) {
    commit('updateMessage', message)
  },

  /**
   * 标记消息为已读
   */
  async markMessagesAsRead({ commit }, messageIds) {
    try {
      await messagesApi.markMessagesAsRead(messageIds)
      commit('markMessagesAsRead', messageIds)
    } catch (err) {
      console.error('标记消息已读失败:', err)
      throw err
    }
  },

  /**
   * 加载未读消息数
   */
  async loadUnreadCount({ commit }, conversationId) {
    try {
      const res = await messagesApi.getUnreadCount(conversationId)
      commit('setUnreadCount', res.unread_count || 0)
      return res.unread_count || 0
    } catch (err) {
      console.error('加载未读消息数失败:', err)
      throw err
    }
  },

  /**
   * 清空当前会话
   */
  clearCurrentConversation({ commit }) {
    commit('setCurrentConversation', null)
    commit('setMessages', [])
  },
}

// 变更
const mutations = {
  setConversations(state, conversations) {
    state.conversations = conversations
  },

  setCurrentConversation(state, conversation) {
    state.currentConversation = conversation
  },

  setMessages(state, messages) {
    state.messages = messages
  },

  addMessage(state, message) {
    // 检查消息是否已存在
    const index = state.messages.findIndex(m => m.id === message.id)
    if (index === -1) {
      state.messages.push(message)
      // 按时间排序
      state.messages.sort((a, b) => {
        const timeA = new Date(a.created_at || 0).getTime()
        const timeB = new Date(b.created_at || 0).getTime()
        return timeA - timeB
      })
    }
  },

  updateMessage(state, message) {
    const index = state.messages.findIndex(m => m.id === message.id)
    if (index !== -1) {
      state.messages[index] = { ...state.messages[index], ...message }
    }
  },

  markMessagesAsRead(state, messageIds) {
    state.messages.forEach(message => {
      if (messageIds.includes(message.id)) {
        message.is_read = true
      }
    })
  },

  setUnreadCount(state, count) {
    state.unreadCount = count
  },

  setLoading(state, loading) {
    state.loading = loading
  },
}

module.exports = {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}

