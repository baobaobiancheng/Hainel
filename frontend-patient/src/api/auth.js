/**
 * 认证相关API
 */

const { post, get, put } = require('../utils/request')

/**
 * 用户注册
 * @param {Object} data 注册数据
 * @returns {Promise}
 */
function register(data) {
  return post('/auth/register', data)
}

/**
 * 用户登录
 * @param {Object} data 登录数据 {username/email/phone, password}
 * @returns {Promise}
 */
function login(data) {
  return post('/auth/login', data).then(res => {
    // 保存token和用户信息
    if (res.access_token) {
      wx.setStorageSync('token', res.access_token)
      wx.setStorageSync('userInfo', res.user)
      
      const app = getApp()
      app.globalData.token = res.access_token
      app.globalData.userInfo = res.user
      app.globalData.isLoggedIn = true
    }
    return res
  })
}

/**
 * 用户登出
 * @returns {Promise}
 */
function logout() {
  return post('/auth/logout').finally(() => {
    // 清除本地存储
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
    
    const app = getApp()
    app.globalData.token = null
    app.globalData.userInfo = null
    app.globalData.isLoggedIn = false
  })
}

/**
 * 获取当前用户信息
 * @returns {Promise}
 */
function getCurrentUser() {
  return get('/auth/me').then(res => {
    // 更新用户信息
    wx.setStorageSync('userInfo', res)
    
    const app = getApp()
    app.globalData.userInfo = res
    return res
  })
}

/**
 * 获取当前用户统计数据
 * @returns {Promise}
 */
function getCurrentUserStats() {
  return get('/auth/me/stats', {}, { loading: false })
}

/**
 * 更新当前用户信息
 * @param {Object} data 更新数据
 * @returns {Promise}
 */
function updateCurrentUser(data) {
  return put('/auth/me', data).then(res => {
    // 更新用户信息
    wx.setStorageSync('userInfo', res)
    
    const app = getApp()
    app.globalData.userInfo = res
    return res
  })
}

/**
 * 修改密码
 * @param {Object} data {old_password, new_password}
 * @returns {Promise}
 */
function changePassword(data) {
  return post('/auth/change-password', data)
}

/**
 * 上传当前用户头像
 * @param {string} filePath 本地临时文件路径
 * @returns {Promise}
 */
function uploadAvatar(filePath) {
  return new Promise((resolve, reject) => {
    const app = getApp()
    const token = wx.getStorageSync('token') || app.globalData.token

    wx.uploadFile({
      url: `${app.globalData.apiBaseUrl}/auth/me/avatar`,
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          const data = JSON.parse(res.data || '{}')
          wx.setStorageSync('userInfo', data)
          app.globalData.userInfo = data
          resolve(data)
        } else {
          let message = `上传失败 (${res.statusCode})`
          try {
            const data = JSON.parse(res.data || '{}')
            message = data.detail || data.message || message
          } catch { /* ignore */ }
          reject(new Error(message))
        }
      },
      fail: reject,
    })
  })
}

/**
 * 获取token
 * @returns {string|null}
 */
function getToken() {
  return wx.getStorageSync('token')
}

module.exports = {
  register,
  login,
  logout,
  getCurrentUser,
  getCurrentUserStats,
  updateCurrentUser,
  uploadAvatar,
  changePassword,
  getToken,
}

