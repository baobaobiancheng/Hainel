// pages/profile/profile.js
const authApi = require('../../api/auth')

Page({
  data: {
    userInfo: null,
    isLoggedIn: false,
    avatarChar: 'U',
    avatarUrl: '',
    stats: { consultations: 0, reports: 0, reminders: 0, days: 0 },
    settingMenus: [
      { icon: '👤', title: '个人信息',  iconBg: '#E0F5F3', action: 'editProfile' },
      { icon: '🩺', title: '健康档案',  iconBg: '#DBEAFE', action: 'healthProfile' },
      { icon: '🔒', title: '修改密码',  iconBg: '#FEF3C7', action: 'changePassword' },
      { icon: 'ℹ️', title: '关于系统',  iconBg: '#F3F4F6', action: 'about' },
    ],
  },

  onLoad() {
    this.checkLogin()
  },

  onShow() {
    this.checkLogin()
    if (this.data.isLoggedIn) this.loadUserInfo()
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
  },

  checkLogin() {
    const app = getApp()
    const isLoggedIn = app.globalData.isLoggedIn || !!wx.getStorageSync('token')
    this.setData({ isLoggedIn })
  },

  async loadUserInfo() {
    try {
      const userInfo = await authApi.getCurrentUser()
      const statsRes = await authApi.getCurrentUserStats().catch(() => ({}))
      const char = (userInfo.full_name || userInfo.username || 'U').charAt(0).toUpperCase()
      const created = new Date(userInfo.created_at || Date.now())
      const days = Math.floor((Date.now() - created.getTime()) / (1000 * 60 * 60 * 24))
      this.setData({
        userInfo,
        avatarChar: char,
        avatarUrl: this.normalizeAvatarUrl(userInfo.avatar_url),
        stats: {
          consultations: statsRes.conversation_count || 0,
          reports: statsRes.report_count || 0,
          reminders: statsRes.today_reminder_count || 0,
          days: days || 0,
        },
      })
      wx.setStorageSync('userInfo', userInfo)
    } catch (err) {
      const cached = wx.getStorageSync('userInfo')
      if (cached) {
        const char = (cached.full_name || cached.username || 'U').charAt(0).toUpperCase()
        this.setData({
          userInfo: cached,
          avatarChar: char,
          avatarUrl: this.normalizeAvatarUrl(cached.avatar_url),
        })
      }
    }
  },

  normalizeAvatarUrl(url) {
    if (!url) return ''
    if (/^https?:\/\//.test(url)) return url
    const app = getApp()
    const apiBase = (app.globalData.apiBaseUrl || '').replace(/\/$/, '')
    return `${apiBase}${url.startsWith('/') ? url : `/${url}`}`
  },

  chooseAvatar() {
    if (!this.data.isLoggedIn) return

    const choose = wx.chooseMedia
      ? (success) => wx.chooseMedia({
          count: 1,
          mediaType: ['image'],
          sourceType: ['album', 'camera'],
          sizeType: ['compressed'],
          success,
        })
      : (success) => wx.chooseImage({
          count: 1,
          sizeType: ['compressed'],
          sourceType: ['album', 'camera'],
          success,
        })

    choose(async (res) => {
      const filePath = res.tempFiles?.[0]?.tempFilePath || res.tempFilePaths?.[0]
      if (!filePath) return

      wx.showLoading({ title: '上传中...', mask: true })
      try {
        const userInfo = await authApi.uploadAvatar(filePath)
        const char = (userInfo.full_name || userInfo.username || 'U').charAt(0).toUpperCase()
        this.setData({
          userInfo,
          avatarChar: char,
          avatarUrl: this.normalizeAvatarUrl(userInfo.avatar_url),
        })
        wx.showToast({ title: '头像已更新', icon: 'success' })
      } catch (err) {
        wx.showToast({ title: err.message || '头像上传失败', icon: 'none' })
      } finally {
        wx.hideLoading()
      }
    })
  },

  onMenuTap(e) {
    const item = e.currentTarget.dataset.item
    if (item.action) {
      this.handleAction(item.action)
    }
  },

  handleAction(action) {
    switch (action) {
      case 'editProfile':
        this.editProfile()
        break
      case 'changePassword':
        wx.navigateTo({ url: '/src/pages/change-password/change-password' })
        break
      case 'healthProfile':
        wx.navigateTo({ url: '/src/pages/health-profile/health-profile' })
        break
      case 'about':
        wx.showModal({
          title: '关于智慧健康助手',
          content: [
            '基于多智能体协同的医疗健康咨询与辅助诊断系统',
            '',
            '核心能力',
            '1. 智能咨询：围绕症状描述、健康档案和历史对话，生成结构化问诊建议。',
            '2. 辅助诊断：多智能体从症状分析、风险识别、检查建议等角度协同推理。',
            '3. 报告识别：支持上传检查报告，结合 OCR 提取关键信息辅助分析。',
            '4. 用药提醒：管理用药、复诊和检查计划，帮助形成连续健康管理闭环。',
            '',
            '温馨提示',
            '本系统提供健康咨询与辅助判断，不替代医生面诊、诊断和处方。若出现胸痛、呼吸困难、意识异常、严重出血等急症表现，请立即线下就医或拨打急救电话。',
            '',
            '版本：1.0.0',
          ].join('\n'),
          showCancel: false,
          confirmText: '我知道了',
        })
        break
    }
  },

  editProfile() {
    wx.navigateTo({
      url: '/src/pages/profile-edit/profile-edit',
      fail: (err) => {
        console.error('打开个人信息编辑页失败:', err)
        wx.showToast({ title: '页面打开失败', icon: 'none' })
      },
    })
  },

  goLogin() {
    wx.navigateTo({ url: '/src/pages/login/login' })
  },

  logout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await authApi.logout()
        } catch { /* ignore */ }
        const app = getApp()
        app.globalData.isLoggedIn = false
        app.globalData.token = null
        app.globalData.userInfo = null
        wx.removeStorageSync('token')
        wx.removeStorageSync('userInfo')
        this.setData({ isLoggedIn: false, userInfo: null })
        wx.showToast({ title: '已退出登录', icon: 'success' })
      },
    })
  },
})
