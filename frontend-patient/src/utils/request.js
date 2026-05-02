/**
 * 网络请求工具
 * 封装微信小程序的request API，统一处理认证、错误等
 */

const app = getApp()

// 并发请求计数器，防止多个请求同时操作 loading 导致配对警告
let _loadingCount = 0

function _showLoading(text) {
  if (_loadingCount === 0) {
    wx.showLoading({ title: text || '加载中...', mask: true })
  }
  _loadingCount++
}

function _hideLoading() {
  _loadingCount = Math.max(0, _loadingCount - 1)
  if (_loadingCount === 0) {
    wx.hideLoading()
  }
}

/**
 * 发起网络请求
 * @param {Object} options 请求配置
 * @returns {Promise}
 */
function request(options) {
  return new Promise((resolve, reject) => {
    // 获取token
    const token = wx.getStorageSync('token') || app.globalData.token
    
    // 构建完整URL
    const url = options.url.startsWith('http') 
      ? options.url 
      : `${app.globalData.apiBaseUrl}${options.url}`
    
    // 构建请求头
    const header = {
      'Content-Type': 'application/json',
      ...options.header,
    }
    
    // 添加认证token
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }
    
    // 显示加载提示
    if (options.loading !== false) {
      _showLoading(options.loadingText)
    }
    
    // 发起请求
    wx.request({
      url,
      method: options.method || 'GET',
      data: options.data || {},
      header,
      timeout: options.timeout || 30000, // 默认30秒超时，特殊接口可单独覆盖
      success: (res) => {
        // HTTP状态码检查
        if (res.statusCode >= 200 && res.statusCode < 300) {
          // 业务状态码检查
          if (res.data) {
            resolve(res.data)
          } else {
            resolve(res)
          }
        } else if (res.statusCode === 401) {
          // 未授权，清除登录信息并跳转到登录页
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          app.globalData.isLoggedIn = false
          app.globalData.token = null
          app.globalData.userInfo = null
          
          wx.showToast({
            title: '登录已过期，请重新登录',
            icon: 'none',
            duration: 2000,
          })
          
          // 跳转到登录页（如果有）
          setTimeout(() => {
            wx.reLaunch({
              url: '/src/pages/profile/profile',
            })
          }, 2000)
          
          reject(new Error('未授权'))
        } else {
          // 其他错误
          const errorMsg = res.data?.detail || res.data?.message || `请求失败 (${res.statusCode})`
          wx.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 2000,
          })
          reject(new Error(errorMsg))
        }
      },
      fail: (err) => {
        console.error('请求失败:', err)
        
        let errorMsg = '网络请求失败'
        if (err.errMsg) {
          if (err.errMsg.includes('timeout')) {
            errorMsg = '请求超时，请检查网络'
          } else if (err.errMsg.includes('fail')) {
            errorMsg = '网络连接失败，请检查网络设置'
          }
        }
        
        wx.showToast({
          title: errorMsg,
          icon: 'none',
          duration: 2000,
        })
        
        reject(err)
      },
      complete: () => {
        if (options.loading !== false) {
          _hideLoading()
        }
      },
    })
  })
}

/**
 * GET请求
 */
function get(url, data = {}, options = {}) {
  return request({
    url,
    method: 'GET',
    data,
    ...options,
  })
}

/**
 * POST请求
 */
function post(url, data = {}, options = {}) {
  return request({
    url,
    method: 'POST',
    data,
    ...options,
  })
}

/**
 * PUT请求
 */
function put(url, data = {}, options = {}) {
  return request({
    url,
    method: 'PUT',
    data,
    ...options,
  })
}

/**
 * DELETE请求
 */
function del(url, data = {}, options = {}) {
  return request({
    url,
    method: 'DELETE',
    data,
    ...options,
  })
}

/**
 * PATCH请求
 */
function patch(url, data = {}, options = {}) {
  return request({
    url,
    method: 'PATCH',
    data,
    ...options,
  })
}

module.exports = {
  request,
  get,
  post,
  put,
  del,
  patch,
}

