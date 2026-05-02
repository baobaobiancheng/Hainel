import request from './request'

// 获取本地存储的token
const getToken = () => {
  return localStorage.getItem('token')
}

export const login = (username, password) => {
  return request({
    url: '/v1/auth/login',
    method: 'post',
    data: { username, password }
  })
}

export const getCurrentUser = () => {
  return request({
    url: '/v1/auth/me',
    method: 'get'
  })
}

export const refreshToken = () => {
  return request({
    url: '/v1/auth/refresh',
    method: 'post'
  })
}

export { getToken }

