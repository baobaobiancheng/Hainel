// pages/login/login.js
const authApi = require('../../api/auth')

Page({
  data: {
    mode: 'login', // login | register
    form: { username: '', password: '', confirmPassword: '', fullName: '' },
    showPassword: false,
    loading: false,
    errorMsg: '',
  },

  onLoad(options) {
    if (options.mode) this.setData({ mode: options.mode })
    wx.setNavigationBarTitle({ title: '登录 / 注册' })
  },

  switchMode(e) {
    this.setData({
      mode: e.currentTarget.dataset.mode,
      errorMsg: '',
    })
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({
      [`form.${field}`]: e.detail.value,
      errorMsg: '',
    })
  },

  togglePassword() {
    this.setData({ showPassword: !this.data.showPassword })
  },

  validate() {
    const { form, mode } = this.data
    if (!form.username.trim()) {
      this.setData({ errorMsg: '请输入手机号或用户名' })
      return false
    }
    if (!form.password) {
      this.setData({ errorMsg: '请输入密码' })
      return false
    }
    if (form.password.length < 6) {
      this.setData({ errorMsg: '密码不能少于6位' })
      return false
    }
    if (mode === 'register' && form.password !== form.confirmPassword) {
      this.setData({ errorMsg: '两次密码输入不一致' })
      return false
    }
    return true
  },

  async submit() {
    if (!this.validate() || this.data.loading) return
    this.setData({ loading: true, errorMsg: '' })

    try {
      let result
      if (this.data.mode === 'login') {
        result = await authApi.login({
          username: this.data.form.username.trim(),
          password: this.data.form.password,
        })
      } else {
        result = await authApi.register({
          username: this.data.form.username.trim(),
          password: this.data.form.password,
          full_name: this.data.form.fullName.trim() || undefined,
        })
        // 注册成功后自动登录
        result = await authApi.login({
          username: this.data.form.username.trim(),
          password: this.data.form.password,
        })
      }

      // 保存 token 和用户信息
      const app = getApp()
      app.globalData.isLoggedIn = true
      app.globalData.token = result.access_token || result.token
      wx.setStorageSync('token', result.access_token || result.token)

      if (result.user) {
        app.globalData.userInfo = result.user
        wx.setStorageSync('userInfo', result.user)
      }

      wx.showToast({
        title: this.data.mode === 'login' ? '登录成功' : '注册成功',
        icon: 'success',
        duration: 1500,
      })

      setTimeout(() => {
        wx.switchTab({ url: '/src/pages/index/index' })
      }, 1500)
    } catch (err) {
      const msg = err?.message || '操作失败，请稍后重试'
      this.setData({ errorMsg: msg })
    } finally {
      this.setData({ loading: false })
    }
  },

  showTerms() {
    wx.showModal({
      title: '用户服务协议',
      content: '本系统仅供学术研究和辅助参考，不作为最终医疗诊断依据，请以专业医生意见为准。',
      showCancel: false,
    })
  },

  showPrivacy() {
    wx.showModal({
      title: '隐私政策',
      content: '我们严格保护您的个人健康信息，不会泄露给第三方。所有数据仅用于提供健康咨询服务。',
      showCancel: false,
    })
  },
})
