// custom-tab-bar/index.js
Component({
  data: {
    selected: 0,
    tabs: [
      { key: 'home',    text: '首页',   path: '/src/pages/index/index' },
      { key: 'chat',    text: '咨询',   path: '/src/pages/consultation/consultation' },
      { key: 'bell',    text: '提醒',   path: '/src/pages/reminders/reminders' },
      { key: 'profile', text: '我的',   path: '/src/pages/profile/profile' },
    ],
  },

  methods: {
    switchTab(e) {
      const path = e.currentTarget.dataset.path
      const index = parseInt(e.currentTarget.dataset.index)
      this.setData({ selected: index })
      wx.switchTab({ url: path })
    },
  },
})
