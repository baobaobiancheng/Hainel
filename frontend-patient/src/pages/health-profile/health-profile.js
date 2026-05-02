const authApi = require('../../api/auth')

const DEFAULT_FORM = {
  birth_date: '',
  gender: '',
  height_cm: '',
  weight_kg: '',
  past_history: '',
  allergies: '',
  long_term_medications: '',
  chronic_diseases: '',
  family_history: '',
  surgery_history: '',
  pregnancy_status: '',
}

Page({
  data: {
    form: { ...DEFAULT_FORM },
    loading: false,
    saving: false,
    errorMsg: '',
    genderOptions: ['男', '女', '其他/不便透露'],
    pregnancyOptions: ['无', '备孕', '妊娠中', '哺乳期', '不适用'],
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: '健康档案' })
    this.loadProfile()
  },

  async loadProfile() {
    this.setData({ loading: true, errorMsg: '' })
    try {
      const userInfo = await authApi.getCurrentUser()
      const profile = userInfo.health_profile || {}
      this.setData({
        form: { ...DEFAULT_FORM, ...profile },
        loading: false,
      })
    } catch (err) {
      const cached = wx.getStorageSync('userInfo') || {}
      this.setData({
        form: { ...DEFAULT_FORM, ...(cached.health_profile || {}) },
        loading: false,
      })
    }
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({
      [`form.${field}`]: e.detail.value,
      errorMsg: '',
    })
  },

  onGenderChange(e) {
    this.setData({
      'form.gender': this.data.genderOptions[e.detail.value],
      errorMsg: '',
    })
  },

  onPregnancyChange(e) {
    this.setData({
      'form.pregnancy_status': this.data.pregnancyOptions[e.detail.value],
      errorMsg: '',
    })
  },

  onBirthDateChange(e) {
    this.setData({
      'form.birth_date': e.detail.value,
      errorMsg: '',
    })
  },

  validate() {
    const { height_cm, weight_kg } = this.data.form
    if (height_cm && (Number(height_cm) < 30 || Number(height_cm) > 250)) {
      this.setData({ errorMsg: '请填写合理的身高' })
      return false
    }
    if (weight_kg && (Number(weight_kg) < 2 || Number(weight_kg) > 300)) {
      this.setData({ errorMsg: '请填写合理的体重' })
      return false
    }
    return true
  },

  async save() {
    if (this.data.saving) return
    if (!this.validate()) return

    const healthProfile = {}
    Object.keys(this.data.form).forEach((key) => {
      const value = String(this.data.form[key] || '').trim()
      if (value) healthProfile[key] = value
    })

    this.setData({ saving: true, errorMsg: '' })
    try {
      await authApi.updateCurrentUser({ health_profile: healthProfile })
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 800)
    } catch (err) {
      this.setData({ errorMsg: (err && err.message) || '保存失败，请重试' })
    } finally {
      this.setData({ saving: false })
    }
  },

  reset() {
    this.setData({ form: { ...DEFAULT_FORM }, errorMsg: '' })
  },
})
