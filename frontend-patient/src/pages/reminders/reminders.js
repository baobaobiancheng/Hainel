// pages/reminders/reminders.js
const remindersApi = require('../../api/reminders')

const TYPE_TO_UI = {
  medication: 'medication',
  examination: 'checkup',
  follow_up: 'followup',
}

Page({
  data: {
    reminders: [],
    loading: false,
    activeTab: 'active',
    todayStr: '',
    todayTotal: 0,
    todayDone: 0,
    todayPending: 0,
  },

  onLoad() {
    this.setData({ todayStr: this.formatToday() })
    this.loadReminders()
  },

  onShow() {
    this.loadReminders()
    this.startAutoRefresh()
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
  },

  onHide() {
    this.stopAutoRefresh()
  },

  onUnload() {
    this.stopAutoRefresh()
  },

  startAutoRefresh() {
    this.stopAutoRefresh()
    this.autoRefreshTimer = setInterval(() => {
      this.loadReminders()
    }, 30000)
  },

  stopAutoRefresh() {
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer)
      this.autoRefreshTimer = null
    }
  },

  formatToday() {
    const d = new Date()
    const w = ['周日','周一','周二','周三','周四','周五','周六'][d.getDay()]
    return `${d.getMonth()+1}月${d.getDate()}日 ${w}`
  },

  switchReminderFilter(e) {
    this.setData({ activeTab: e.currentTarget.dataset.tab })
    this.loadReminders()
  },

  async loadReminders() {
    this.setData({ loading: true })
    try {
      const params = {}
      if (this.data.activeTab !== 'all') {
        params.status = this.data.activeTab === 'active' ? 'active' : 'completed'
      }
      const [res, statsRes] = await Promise.all([
        remindersApi.getReminders(params),
        remindersApi.getReminders({ page_size: 100 }),
      ])
      const allItems = res.items || []
      const statsItems = statsRes.items || []

      const mapped = allItems.map(r => {
        const description = r.notes || [r.medication_name, r.dosage].filter(Boolean).join(' ')
        return {
          ...r,
          description,
          type: TYPE_TO_UI[r.reminder_type] || 'medication',
          timeStr: r.remind_time
          ? r.remind_time.substring(0, 5)
          : '--:--',
          nextDateStr: r.start_date
            ? new Date(r.start_date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
            : '今天',
        }
      })

      // 今日统计（不管 tab）
      const today = statsItems.filter(r => {
        const now = new Date()
        const start = r.start_date ? new Date(r.start_date) : null
        const end = r.end_date ? new Date(r.end_date) : null
        return (!start || start <= now) && (!end || end >= now)
      })
      const done = today.filter(r => r.status === 'completed').length

      this.setData({
        reminders: mapped,
        loading: false,
        todayTotal: today.length,
        todayDone: done,
        todayPending: today.length - done,
      })
    } catch (err) {
      console.error('加载提醒失败:', err)
      // 降级：使用本地模拟数据
      this.loadMockData()
    }
  },

  loadMockData() {
    const mockData = [
      {
        id: 1, title: '服用降压药', description: '每日一次，每次1片（硝苯地平）',
        type: 'medication', status: 'active', timeStr: '08:00', nextDateStr: '今天',
      },
      {
        id: 2, title: '测量血压', description: '早晚各一次，记录数值',
        type: 'checkup', status: 'active', timeStr: '20:00', nextDateStr: '今天',
      },
      {
        id: 3, title: '心内科复诊', description: '带上近三个月血压记录',
        type: 'followup', status: 'active', timeStr: '09:30', nextDateStr: '明天',
      },
    ]
    const filtered = this.data.activeTab === 'all'
      ? mockData
      : mockData.filter(r => r.status === this.data.activeTab)

    this.setData({
      reminders: filtered,
      loading: false,
      todayTotal: 2,
      todayDone: 0,
      todayPending: 2,
    })
  },

  createReminder() {
    wx.navigateTo({ url: '/src/pages/reminder-form/reminder-form' })
  },

  editReminder(e) {
    wx.navigateTo({ url: `/src/pages/reminder-form/reminder-form?id=${e.currentTarget.dataset.id}` })
  },

  async markComplete(e) {
    const id = e.currentTarget.dataset.id
    try {
      await remindersApi.updateReminder(id, { status: 'completed' })
      wx.showToast({ title: '已标记完成', icon: 'success' })
      this.loadReminders()
    } catch {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  deleteReminder(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条提醒吗？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await remindersApi.deleteReminder(id)
          wx.showToast({ title: '已删除', icon: 'success' })
          this.loadReminders()
        } catch {
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      },
    })
  },
})
