// pages/index/index.js
const conversationsApi = require('../../api/conversations')
const authApi = require('../../api/auth')
const { formatRelativeTime } = require('../../utils/helpers')

const HEALTH_TIPS = [
  '每天保持7-8小时的充足睡眠，有助于提高免疫力和修复身体。',
  '适量饮水，成人每天建议饮水1500-2000毫升，有助于代谢废物。',
  '每周进行150分钟中等强度有氧运动，如步行、游泳，可降低心血管疾病风险。',
  '保持均衡饮食，多吃蔬菜水果，减少高糖高脂食物的摄入。',
  '定期体检，早发现、早治疗，是维护健康最有效的方法。',
  '保持积极乐观的心态，适当减压，有助于增强免疫力。',
  '规律作息，尽量在晚上11点前入睡，让身体得到充分休息。',
]

Page({
  data: {
    userInfo: null,
    greeting: '',
    avatarChar: '医',
    avatarUrl: '',
    recentConversations: [],
    stats: { conversations: 0, reminders: 0, reports: 0 },
    healthTip: '',
  },

  onLoad() {
    this.setData({
      greeting: this.getGreeting(),
      healthTip: HEALTH_TIPS[Math.floor(Math.random() * HEALTH_TIPS.length)],
    })
    this.loadUserInfo()
    this.loadRecentConversations()
    this.loadStats()
  },

  onShow() {
    this.loadUserInfo()
    this.loadRecentConversations()
    this.loadStats()
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 })
    }
  },

  getGreeting() {
    const hour = new Date().getHours()
    if (hour < 6)  return '夜深了'
    if (hour < 9)  return '早上好'
    if (hour < 12) return '上午好'
    if (hour < 14) return '中午好'
    if (hour < 18) return '下午好'
    return '晚上好'
  },

  loadUserInfo() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo) {
      const char = (userInfo.full_name || userInfo.username || 'U').charAt(0).toUpperCase()
      this.setData({
        userInfo,
        avatarChar: char,
        avatarUrl: this.normalizeAvatarUrl(userInfo.avatar_url),
      })
    }
  },

  normalizeAvatarUrl(url) {
    if (!url) return ''
    if (/^https?:\/\//.test(url)) return url
    const app = getApp()
    const apiBase = (app.globalData.apiBaseUrl || '').replace(/\/$/, '')
    return `${apiBase}${url.startsWith('/') ? url : `/${url}`}`
  },

  async loadRecentConversations() {
    try {
      const res = await conversationsApi.getConversations({ skip: 0, limit: 3, include_total: true })
      const conversations = (res.items || []).slice(0, 3).map(conv => ({
        ...conv,
        relativeTime: formatRelativeTime(conv.updated_at || conv.created_at),
      }))
      this.setData({
        recentConversations: conversations,
      })
    } catch (err) {
      console.error('加载会话失败:', err)
    }
  },

  async loadStats() {
    try {
      const res = await authApi.getCurrentUserStats()
      const stats = {
        conversations: res.conversation_count || 0,
        reminders: res.today_reminder_count || 0,
        reports: res.report_count || 0,
      }
      wx.setStorageSync('userStats', stats)
      this.setData({ stats })
    } catch (err) {
      const stats = wx.getStorageSync('userStats') || { conversations: 0, reminders: 0, reports: 0 }
      this.setData({ stats })
    }
  },

  startNewConsultation() {
    // consultation 是 tabBar 页面，必须用 switchTab
    wx.removeStorageSync('pendingConversationId')
    wx.switchTab({ url: '/src/pages/consultation/consultation' })
  },

  viewConversation(e) {
    // tabBar 页面无法通过 URL 传参，先写入缓存再跳转
    wx.setStorageSync('pendingConversationId', e.currentTarget.dataset.id)
    wx.switchTab({ url: '/src/pages/consultation/consultation' })
  },

  viewHistory() {
    wx.navigateTo({ url: '/src/pages/history/history' })
  },

  goToProfile() {
    wx.switchTab({ url: '/src/pages/profile/profile' })
  },
})
