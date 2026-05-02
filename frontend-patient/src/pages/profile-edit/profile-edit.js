// pages/profile-edit/profile-edit.js
const authApi = require('../../api/auth')

Page({
  data: {
    form: {
      full_name: '',
      email: '',
      phone: '',
    },
    originalForm: {},
    loading: false,
    saving: false,
    errorMsg: '',
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: '个人信息' })
    this.loadUserInfo()
  },

  async loadUserInfo() {
    this.setData({ loading: true })
    try {
      const userInfo = await authApi.getCurrentUser()
      const form = {
        full_name: userInfo.full_name || '',
        email: userInfo.email || '',
        phone: userInfo.phone || '',
      }
      this.setData({ form, originalForm: { ...form }, loading: false })
    } catch {
      const cached = wx.getStorageSync('userInfo')
      if (cached) {
        const form = {
          full_name: cached.full_name || '',
          email: cached.email || '',
          phone: cached.phone || '',
        }
        this.setData({ form, originalForm: { ...form } })
      }
      this.setData({ loading: false })
    }
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({
      [`form.${field}`]: e.detail.value,
      errorMsg: '',
    })
  },

  validate() {
    const { full_name, email, phone } = this.data.form
    if (!full_name.trim()) {
      this.setData({ errorMsg: '请填写姓名' })
      return false
    }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      this.setData({ errorMsg: '邮箱格式不正确' })
      return false
    }
    if (phone && !/^1[3-9]\d{9}$/.test(phone)) {
      this.setData({ errorMsg: '手机号格式不正确' })
      return false
    }
    return true
  },

  async save() {
    if (this.data.saving) return
    if (!this.validate()) return

    this.setData({ saving: true, errorMsg: '' })
    try {
      await authApi.updateCurrentUser({
        full_name: this.data.form.full_name.trim(),
        email: this.data.form.email.trim() || undefined,
        phone: this.data.form.phone.trim() || undefined,
      })
      wx.showToast({ title: '保存成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1200)
    } catch (err) {
      const msg = (err && err.message) || '保存失败，请重试'
      this.setData({ errorMsg: msg })
    } finally {
      this.setData({ saving: false })
    }
  },

  reset() {
    this.setData({ form: { ...this.data.originalForm }, errorMsg: '' })
  },
})
