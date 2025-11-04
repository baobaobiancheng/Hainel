/**
 * 认证相关 API
 */
import { request } from '@/utils/request'
import type {
  LoginRequest,
  RegisterRequest,
  LoginResponse,
  UserInfo,
  ApiResponse,
} from '@/types/api'

export const authApi = {
  // 用户注册
  register(data: RegisterRequest): Promise<ApiResponse<UserInfo>> {
    return request.post('/v1/auth/register', data)
  },

  // 用户登录
  login(data: LoginRequest): Promise<ApiResponse<LoginResponse>> {
    return request.post('/v1/auth/login', data)
  },

  // 获取当前用户信息
  getCurrentUser(): Promise<ApiResponse<UserInfo>> {
    return request.get('/v1/auth/me')
  },

  // 刷新 Token
  refreshToken(refreshToken: string): Promise<ApiResponse<LoginResponse>> {
    return request.post('/v1/auth/refresh', { refresh_token: refreshToken })
  },

  // 登出
  logout(): Promise<ApiResponse<null>> {
    return request.post('/v1/auth/logout')
  },
}

