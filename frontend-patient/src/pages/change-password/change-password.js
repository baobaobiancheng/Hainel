// pages/change-password/change-password.js
const authApi = require('../../api/auth')

Page({
  data: {
    form: {
      old_password: '',
      new_password: '',
      confirm_password: '',
    },
    showOld: false,
    showNew: false,
    showConfirm: false,
    saving: false,
    errorMsg: '',
    successMsg: '',
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: '修改密码' })
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({
      [`form.${field}`]: e.detail.value,
      errorMsg: '',
      successMsg: '',
    })
  },

  toggleShow(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [field]: !this.data[field] })
  },

  validate() {
    const { old_password, new_password, confirm_password } = this.data.form
    if (!old_password) {
      this.setData({ errorMsg: '请输入当前密码' })
      return false
    }
    if (!new_password) {
      this.setData({ errorMsg: '请输入新密码' })
      return false
    }
    if (new_password.length < 6) {
      this.setData({ errorMsg: '新密码长度不能少于6位' })
      return false
    }
    if (new_password === old_password) {
      this.setData({ errorMsg: '新密码不能与当前密码相同' })
      return false
    }
    if (new_password !== confirm_password) {
      this.setData({ errorMsg: '两次输入的新密码不一致' })
      return false
    }
    return true
  },

  async save() {
    if (this.data.saving) return
    if (!this.validate()) return

    this.setData({ saving: true, errorMsg: '', successMsg: '' })
    try {
      await authApi.changePassword({
        old_password: this.data.form.old_password,
        new_password: this.data.form.new_password,
      })
      this.setData({
        successMsg: '密码修改成功',
        form: { old_password: '', new_password: '', confirm_password: '' },
      })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (err) {
      const msg = (err && err.message) || '修改失败，请检查当前密码是否正确'
      this.setData({ errorMsg: msg })
    } finally {
      this.setData({ saving: false })
    }
  },
})
