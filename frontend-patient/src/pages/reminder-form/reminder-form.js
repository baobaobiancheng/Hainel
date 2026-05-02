// pages/reminder-form/reminder-form.js
const remindersApi = require('../../api/reminders')

const TYPE_TO_API = {
  medication: 'medication',
  checkup: 'examination',
  followup: 'follow_up',
}

const TYPE_TO_UI = {
  medication: 'medication',
  examination: 'checkup',
  follow_up: 'followup',
}

function formatDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`
}

function buildDateTime(dateStr, timeStr) {
  if (!dateStr || !timeStr) return null
  const date = new Date(`${dateStr}T${timeStr}:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

Page({
  data: {
    isEdit: false,
    reminderId: null,
    saving: false,
    errorMsg: '',

    selectedType: 'medication',
    typeOptions: [
      { value: 'medication', icon: '💊', label: '用药' },
      { value: 'checkup',    icon: '🔬', label: '检查' },
      { value: 'followup',   icon: '🏥', label: '复诊' },
    ],

    form: {
      title: '',
      description: '',
      remindDate: '',
      remindTime: '',
      frequency: 'daily',
      weekdays: [],
    },

    frequencyOptions: [
      { value: 'once',    label: '仅一次' },
      { value: 'daily',   label: '每天' },
      { value: 'weekly',  label: '每周' },
      { value: 'custom',  label: '自定义' },
    ],

    weekdays: [
      { value: 1, label: '一' },
      { value: 2, label: '二' },
      { value: 3, label: '三' },
      { value: 4, label: '四' },
      { value: 5, label: '五' },
      { value: 6, label: '六' },
      { value: 0, label: '日' },
    ],
    todayDate: '',
  },

  onLoad(options) {
    const todayDate = formatDate(new Date())
    this.setData({ todayDate })
    if (options.id) {
      this.setData({ isEdit: true, reminderId: parseInt(options.id) })
      wx.setNavigationBarTitle({ title: '编辑提醒' })
      this.loadReminder(parseInt(options.id))
    } else {
      wx.setNavigationBarTitle({ title: '添加提醒' })
      this.setData({ 'form.remindDate': todayDate })
    }
  },

  async loadReminder(id) {
    wx.showLoading({ title: '加载中...' })
    try {
      const r = await remindersApi.getReminder(id)
      this.setData({
        selectedType: TYPE_TO_UI[r.reminder_type] || 'medication',
        'form.title': r.title || '',
        'form.description': r.notes || [r.medication_name, r.dosage].filter(Boolean).join(' '),
        'form.remindDate': r.start_date ? r.start_date.substring(0, 10) : '',
        'form.remindTime': r.remind_time ? r.remind_time.substring(0, 5) : '',
        'form.frequency': r.frequency || 'daily',
        'form.weekdays': r.weekdays || [],
      })
    } catch {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: e.detail.value, errorMsg: '' })
  },

  selectType(e) {
    this.setData({ selectedType: e.currentTarget.dataset.value })
  },

  selectFreq(e) {
    this.setData({ 'form.frequency': e.currentTarget.dataset.value })
  },

  toggleWeekday(e) {
    const val = parseInt(e.currentTarget.dataset.value)
    const weekdays = [...this.data.form.weekdays]
    const idx = weekdays.indexOf(val)
    if (idx > -1) weekdays.splice(idx, 1)
    else weekdays.push(val)
    this.setData({ 'form.weekdays': weekdays })
  },

  onDateChange(e) {
    this.setData({ 'form.remindDate': e.detail.value, errorMsg: '' })
  },

  onTimeChange(e) {
    this.setData({ 'form.remindTime': e.detail.value, errorMsg: '' })
  },

  validate() {
    const { form } = this.data
    if (!form.title.trim()) {
      this.setData({ errorMsg: '请输入提醒名称' })
      return false
    }
    if (!form.remindDate) {
      this.setData({ errorMsg: '请选择开始日期' })
      return false
    }
    if (!form.remindTime) {
      this.setData({ errorMsg: '请选择提醒时间' })
      return false
    }
    const todayDate = formatDate(new Date())
    if (form.remindDate < todayDate) {
      this.setData({ errorMsg: '开始日期不能早于当前日期' })
      return false
    }
    const remindAt = buildDateTime(form.remindDate, form.remindTime)
    if (!remindAt) {
      this.setData({ errorMsg: '提醒时间格式不正确' })
      return false
    }
    if (remindAt <= new Date()) {
      this.setData({ errorMsg: '开始日期和提醒时间必须晚于当前时间' })
      return false
    }
    return true
  },

  async save() {
    if (!this.validate() || this.data.saving) return
    this.setData({ saving: true })

    const payload = {
      title: this.data.form.title.trim(),
      notes: this.data.form.description.trim() || undefined,
      reminder_type: TYPE_TO_API[this.data.selectedType] || 'medication',
      start_date: this.data.form.remindDate ? `${this.data.form.remindDate}T00:00:00` : undefined,
      remind_time: this.data.form.remindTime,
      frequency: this.data.form.frequency,
    }

    try {
      if (this.data.isEdit) {
        await remindersApi.updateReminder(this.data.reminderId, payload)
        wx.showToast({ title: '修改成功', icon: 'success' })
      } else {
        await remindersApi.createReminder(payload)
        wx.showToast({ title: '添加成功', icon: 'success' })
      }
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (err) {
      this.setData({ errorMsg: '保存失败，请重试' })
    } finally {
      this.setData({ saving: false })
    }
  },

  cancel() {
    if (!this.data.isEdit) { wx.navigateBack(); return }
    wx.showModal({
      title: '删除提醒',
      content: '确定要删除这条提醒吗？',
      confirmColor: '#EF4444',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await remindersApi.deleteReminder(this.data.reminderId)
          wx.showToast({ title: '已删除', icon: 'success' })
          setTimeout(() => wx.navigateBack(), 1500)
        } catch {
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      },
    })
  },
})
