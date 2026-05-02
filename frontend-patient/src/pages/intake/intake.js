const DEFAULT_FORM = {
  main_symptom: '',
  duration: '',
  accompanying_symptoms: '',
  pain_location: '',
  pain_level: '',
  fever: '',
  recent_medication: '',
  red_flag_notes: '',
}

Page({
  data: {
    form: { ...DEFAULT_FORM },
    feverOptions: ['无发热', '低热', '高热', '不确定'],
    painOptions: ['无疼痛', '轻度', '中度', '重度', '难以忍受'],
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: '本次问诊信息' })
    const cached = wx.getStorageSync('pendingStructuredIntake')
    if (cached) {
      this.setData({ form: { ...DEFAULT_FORM, ...cached } })
    }
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onFeverChange(e) {
    this.setData({ 'form.fever': this.data.feverOptions[e.detail.value] })
  },

  onPainChange(e) {
    this.setData({ 'form.pain_level': this.data.painOptions[e.detail.value] })
  },

  save() {
    const intake = {}
    Object.keys(this.data.form).forEach((key) => {
      const value = String(this.data.form[key] || '').trim()
      if (value) intake[key] = value
    })
    wx.setStorageSync('pendingStructuredIntake', intake)
    wx.showToast({ title: '已保存', icon: 'success' })
    setTimeout(() => wx.navigateBack(), 600)
  },

  clear() {
    wx.removeStorageSync('pendingStructuredIntake')
    this.setData({ form: { ...DEFAULT_FORM } })
  },
})
