// pages/history/history.js
const conversationsApi = require('../../api/conversations')
const { formatRelativeTime } = require('../../utils/helpers')

const PAGE_SIZE = 15

Page({
  data: {
    conversations: [],
    allConversations: [],
    loading: false,
    hasMore: false,
    searchText: '',
    activeFilter: 'all',
    page: 1,
    filters: [
      { value: 'all',       icon: '📋', label: '全部',   count: 0 },
      { value: 'active',    icon: '🟢', label: '进行中', count: 0 },
      { value: 'pending',   icon: '🟡', label: '等待中', count: 0 },
      { value: 'completed', icon: '✅', label: '已完成', count: 0 },
    ],
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: '咨询历史' })
    this.loadConversations(true)
  },

  onShow() {
    this.loadConversations(true)
  },

  async loadConversations(reset = false) {
    if (this.data.loading) return
    this.setData({ loading: true })

    const page = reset ? 1 : this.data.page
    const skip = (page - 1) * PAGE_SIZE

    try {
      const params = { skip, limit: PAGE_SIZE, include_total: true }
      if (this.data.activeFilter !== 'all') {
        params.status = this.data.activeFilter
      }

      const res = await conversationsApi.getConversations(params)
      const items = (res.items || []).map(c => ({
        ...c,
        relativeTime: formatRelativeTime(c.updated_at || c.created_at),
      }))

      const conversations = reset ? items : [...this.data.conversations, ...items]
      const total = res.total || 0

      // 更新 filter badge counts（首次加载全量统计）
      if (reset) this.updateFilterCounts(res)

      this.setData({
        conversations,
        allConversations: conversations,
        loading: false,
        hasMore: conversations.length < total,
        page: reset ? 2 : page + 1,
      })

      if (this.data.searchText) this.applySearch(this.data.searchText)
    } catch (err) {
      console.error('加载会话失败:', err)
      this.setData({ loading: false })
    }
  },

  updateFilterCounts(res) {
    const items = res.items || []
    const counts = { all: res.total || items.length, active: 0, pending: 0, completed: 0 }
    items.forEach(c => { if (counts[c.status] !== undefined) counts[c.status]++ })

    const filters = this.data.filters.map(f => ({
      ...f,
      count: counts[f.value] || 0,
    }))
    this.setData({ filters })
  },

  setFilter(e) {
    const value = e.currentTarget.dataset.value
    this.setData({ activeFilter: value, searchText: '' })
    this.loadConversations(true)
  },

  onSearch(e) {
    const text = e.detail.value
    this.setData({ searchText: text })
    this.applySearch(text)
  },

  applySearch(text) {
    if (!text) {
      this.setData({ conversations: this.data.allConversations })
      return
    }
    const lower = text.toLowerCase()
    const filtered = this.data.allConversations.filter(c =>
      (c.title || '').toLowerCase().includes(lower) ||
      (c.chief_complaint || '').toLowerCase().includes(lower)
    )
    this.setData({ conversations: filtered })
  },

  clearSearch() {
    this.setData({ searchText: '' })
    this.setData({ conversations: this.data.allConversations })
  },

  loadMore() {
    this.loadConversations(false)
  },

  openConversation(e) {
    // consultation 是 tabBar 页面，通过缓存传递会话ID
    wx.setStorageSync('pendingConversationId', e.currentTarget.dataset.id)
    wx.switchTab({ url: '/src/pages/consultation/consultation' })
  },

  startNew() {
    wx.removeStorageSync('pendingConversationId')
    wx.switchTab({ url: '/src/pages/consultation/consultation' })
  },
})
