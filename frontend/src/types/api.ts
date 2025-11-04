/**
 * API 类型定义
 */

// 通用响应
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data: T
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 用户相关
export interface UserInfo {
  id: string
  username: string
  email: string
  nickname?: string
  avatar_url?: string
  bio?: string
  role: 'student' | 'teacher' | 'admin'
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login_at?: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface LoginRequest {
  username_or_email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// 错题相关
export interface ErrorQuestion {
  id: string
  user_id: string
  subject: string
  chapter?: string
  question_text?: string
  question_image_url?: string
  correct_answer?: string
  user_answer?: string
  explanation?: string
  difficulty: 'easy' | 'medium' | 'hard'
  error_type: 'concept' | 'calculation' | 'careless' | 'method' | 'other'
  tags?: string[]
  review_count: number
  mastery_level: number
  last_reviewed_at?: string
  next_review_at?: string
  is_archived: boolean
  is_favorite: boolean
  created_at: string
  updated_at: string
}

export interface ErrorQuestionCreate {
  subject: string
  chapter?: string
  question_text?: string
  question_image_url?: string
  correct_answer?: string
  user_answer?: string
  explanation?: string
  difficulty?: 'easy' | 'medium' | 'hard'
  error_type?: 'concept' | 'calculation' | 'careless' | 'method' | 'other'
  tags?: string[]
}

export interface ErrorQuestionUpdate extends Partial<ErrorQuestionCreate> {
  is_favorite?: boolean
  is_archived?: boolean
}

export interface ErrorQuestionQuery {
  page?: number
  page_size?: number
  subject?: string
  chapter?: string
  difficulty?: string
  error_type?: string
  is_favorite?: boolean
  is_archived?: boolean
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

