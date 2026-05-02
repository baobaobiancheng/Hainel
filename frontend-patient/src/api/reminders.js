/**
 * 用药提醒 API
 */
const { get, post, put, del } = require('../utils/request')

/**
 * 获取提醒列表
 * @param {Object} params - { status, skip, limit, reminder_type }
 */
function getReminders(params = {}) {
  return get('/reminders/', params, { loading: false })
}

/**
 * 获取单条提醒
 * @param {number} id
 */
function getReminder(id) {
  return get(`/reminders/${id}`)
}

/**
 * 创建提醒
 * @param {Object} data - { title, notes, reminder_type, start_date, remind_time, frequency }
 */
function createReminder(data) {
  return post('/reminders/', data)
}

/**
 * 更新提醒
 * @param {number} id
 * @param {Object} data
 */
function updateReminder(id, data) {
  return put(`/reminders/${id}`, data)
}

/**
 * 删除提醒
 * @param {number} id
 */
function deleteReminder(id) {
  return del(`/reminders/${id}`)
}

/**
 * 标记提醒为已完成
 * @param {number} id
 */
function markComplete(id) {
  return put(`/reminders/${id}`, { status: 'completed' })
}

module.exports = {
  getReminders,
  getReminder,
  createReminder,
  updateReminder,
  deleteReminder,
  markComplete,
}
