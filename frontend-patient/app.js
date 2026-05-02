// app.js
App({
  onLaunch() {
    // 初始化应用
    console.log('医疗健康咨询小程序启动')
    
    // 检查登录状态
    this.checkLoginStatus()
    
    // 初始化全局数据
    this.initGlobalData()
  },

  onShow() {
    // 应用显示时
  },

  onHide() {
    // 应用隐藏时
  },

  onError(msg) {
    console.error('应用错误:', msg)
  },

  /**
   * 检查登录状态
   */
  checkLoginStatus() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    
    if (token && userInfo) {
      // 验证token是否有效
      this.globalData.isLoggedIn = true
      this.globalData.userInfo = userInfo
      this.globalData.token = token
    } else {
      this.globalData.isLoggedIn = false
    }
  },

  /**
   * 初始化全局数据
   */
  initGlobalData() {
    // 设置API基础URL
    const env = 'dev' // dev, prod
    if (env === 'dev') {
      this.globalData.apiBaseUrl = 'http://localhost:8001/api/v1'
    } else {
      this.globalData.apiBaseUrl = 'https://your-domain.com/api/v1'
    }
  },

  /**
   * 全局数据
   */
  globalData: {
    isLoggedIn: false,
    userInfo: null,
    token: null,
    apiBaseUrl: '',
    currentConversationId: null,
  }
})

