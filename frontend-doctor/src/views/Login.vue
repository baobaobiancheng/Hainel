<template>
  <div class="login-scene">
    <!-- Background grid -->
    <div class="bg-grid"></div>
    <!-- Ambient glows -->
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>

    <div class="login-wrapper">
      <!-- Left: Branding panel -->
      <div class="brand-panel">
        <div class="brand-inner">
          <!-- Medical cross -->
          <div class="cross-mark">
            <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
              <rect x="22" y="4" width="12" height="48" rx="6" fill="#22d3ee"/>
              <rect x="4" y="22" width="48" height="12" rx="6" fill="#22d3ee"/>
              <rect x="22" y="4" width="12" height="48" rx="6" fill="url(#gv)"/>
              <defs>
                <linearGradient id="gv" x1="28" y1="4" x2="28" y2="52" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stop-color="#67e8f9"/>
                  <stop offset="100%" stop-color="#0891b2"/>
                </linearGradient>
              </defs>
            </svg>
            <div class="cross-ring ring-1"></div>
            <div class="cross-ring ring-2"></div>
          </div>

          <h1 class="brand-title">智能医疗<br/>诊断平台</h1>
          <p class="brand-subtitle">Smart Medical Diagnosis Platform</p>
          <p class="brand-desc">
            基于多智能体协同技术，为医生提供<br/>
            专业的辅助诊断与健康咨询服务
          </p>

          <!-- Feature list -->
          <div class="feature-list">
            <div class="feature-item" v-for="(f, i) in features" :key="i" :style="{ animationDelay: `${0.6 + i * 0.12}s` }">
              <span class="feature-dot"></span>
              <span>{{ f }}</span>
            </div>
          </div>

          <!-- Scan line animation -->
          <div class="scan-line"></div>
        </div>
      </div>

      <!-- Right: Login form -->
      <div class="form-panel">
        <div class="form-inner">
          <div class="form-header">
            <div class="form-logo">
              <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
                <rect x="11" y="3" width="6" height="22" rx="3" fill="#22d3ee"/>
                <rect x="3" y="11" width="22" height="6" rx="3" fill="#22d3ee"/>
              </svg>
            </div>
            <div>
              <h2 class="form-title">医生登录</h2>
              <p class="form-caption">Doctor Portal · Login</p>
            </div>
          </div>

          <a-form
            :model="loginForm"
            :rules="rules"
            @finish="handleLogin"
            layout="vertical"
          >
            <a-form-item name="username" class="custom-form-item">
              <div class="field-label">用户名</div>
              <a-input
                v-model:value="loginForm.username"
                size="large"
                placeholder="请输入用户名"
                class="custom-input"
              >
                <template #prefix>
                  <UserOutlined class="input-icon" />
                </template>
              </a-input>
            </a-form-item>

            <a-form-item name="password" class="custom-form-item">
              <div class="field-label">密码</div>
              <a-input-password
                v-model:value="loginForm.password"
                size="large"
                placeholder="请输入密码"
                class="custom-input"
              >
                <template #prefix>
                  <LockOutlined class="input-icon" />
                </template>
              </a-input-password>
            </a-form-item>

            <div class="form-options">
              <a-checkbox>记住登录状态</a-checkbox>
              <a class="forgot-link">忘记密码？</a>
            </div>

            <a-form-item style="margin-top: 24px; margin-bottom: 0">
              <button
                type="submit"
                class="login-btn"
                :class="{ loading }"
                :disabled="loading"
              >
                <span v-if="!loading" class="btn-text">
                  <span>登录系统</span>
                  <span class="btn-arrow">→</span>
                </span>
                <span v-else class="btn-loading">
                  <span class="dot-1">·</span>
                  <span class="dot-2">·</span>
                  <span class="dot-3">·</span>
                </span>
              </button>
            </a-form-item>
          </a-form>

          <div class="form-footer">
            <span class="footer-line"></span>
            <span class="footer-text">安全加密连接</span>
            <span class="footer-line"></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const loginForm = reactive({ username: '', password: '' })

const features = [
  'AI 多智能体协同诊断',
  '结构化病历智能生成',
  '知识图谱辅助决策',
  '患者健康全程管理',
]

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名长度至少3位', trigger: 'blur' },
    { max: 20, message: '用户名长度不能超过20位', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' },
    { max: 32, message: '密码长度不能超过32位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  loading.value = true
  try {
    const result = await authStore.login(loginForm.username, loginForm.password)
    if (result.success) {
      message.success('登录成功')
      router.push('/dashboard')
    } else {
      message.error(result.message || '登录失败')
    }
  } catch (error) {
    message.error('登录失败，请检查网络连接')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ─── Scene ─── */
.login-scene {
  min-height: 100vh;
  background: #060c18;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

/* Background grid */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(34,211,238,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34,211,238,0.04) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 0%, transparent 100%);
}

/* Ambient glows */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
}
.glow-1 {
  width: 500px;
  height: 500px;
  left: -100px;
  top: -100px;
  background: radial-gradient(circle, rgba(34,211,238,0.08) 0%, transparent 70%);
  animation: pulse-ring 8s ease-in-out infinite;
}
.glow-2 {
  width: 400px;
  height: 400px;
  right: -80px;
  bottom: -80px;
  background: radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 70%);
  animation: pulse-ring 10s ease-in-out infinite reverse;
}

/* ─── Wrapper ─── */
.login-wrapper {
  display: flex;
  width: 960px;
  max-width: calc(100vw - 40px);
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(34,211,238,0.12);
  box-shadow: 0 40px 120px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.03);
  position: relative;
  z-index: 1;
  animation: fadeUp 0.6s ease both;
}

/* ─── Brand panel ─── */
.brand-panel {
  flex: 1;
  background: linear-gradient(145deg, #0a1829 0%, #060f1e 100%);
  border-right: 1px solid rgba(34,211,238,0.1);
  padding: 60px 48px;
  position: relative;
  overflow: hidden;
}
.brand-panel::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, #22d3ee, transparent);
}

.brand-inner {
  position: relative;
  z-index: 1;
  animation: fadeUp 0.7s 0.1s ease both;
}

/* Cross mark */
.cross-mark {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 36px;
}
.cross-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(34,211,238,0.2);
  animation: pulse-ring 4s ease-in-out infinite;
}
.ring-1 { width: 80px; height: 80px; animation-delay: 0s; }
.ring-2 { width: 110px; height: 110px; animation-delay: 1.5s; border-color: rgba(34,211,238,0.1); }

.brand-title {
  font-family: var(--f-display);
  font-size: 36px;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.25;
  margin-bottom: 10px;
  letter-spacing: -0.01em;
}
.brand-subtitle {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--c-primary);
  font-weight: 500;
  margin-bottom: 20px;
}
.brand-desc {
  font-size: 14px;
  color: #64748b;
  line-height: 1.8;
  margin-bottom: 36px;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #94a3b8;
  animation: fadeUp 0.5s ease both;
}
.feature-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--c-primary);
  flex-shrink: 0;
  box-shadow: 0 0 6px var(--c-primary);
}

/* Scan line */
.scan-line {
  position: absolute;
  left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(34,211,238,0.4), transparent);
  animation: scanline 6s linear infinite;
  pointer-events: none;
}

/* ─── Form panel ─── */
.form-panel {
  width: 400px;
  flex-shrink: 0;
  background: #080f1e;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
}
.form-inner {
  width: 100%;
  animation: fadeUp 0.7s 0.2s ease both;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 40px;
}
.form-logo {
  width: 44px;
  height: 44px;
  background: rgba(34,211,238,0.08);
  border: 1px solid rgba(34,211,238,0.18);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.form-title {
  font-family: var(--f-display);
  font-size: 22px;
  font-weight: 600;
  color: #f1f5f9;
  margin: 0 0 3px;
  line-height: 1.2;
}
.form-caption {
  font-size: 11px;
  color: var(--c-primary);
  letter-spacing: 0.1em;
  font-weight: 500;
  margin: 0;
}

/* Form fields */
.custom-form-item {
  margin-bottom: 20px;
}
.field-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: #64748b;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.custom-input {
  height: 46px !important;
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(34,211,238,0.12) !important;
  border-radius: 10px !important;
  font-size: 14px !important;
  transition: all var(--transition) !important;
}
.custom-input:hover { border-color: rgba(34,211,238,0.28) !important; }
.custom-input:focus, :deep(.ant-input-affix-wrapper-focused) {
  border-color: var(--c-primary) !important;
  box-shadow: 0 0 0 3px rgba(34,211,238,0.08) !important;
  background: rgba(34,211,238,0.03) !important;
}
.input-icon { color: var(--c-primary); font-size: 15px; }

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.forgot-link {
  font-size: 13px;
  color: var(--c-primary);
  cursor: pointer;
  transition: color var(--transition);
}
.forgot-link:hover { color: #67e8f9; }

/* Login button */
.login-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(135deg, #0e7490, #22d3ee);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all var(--transition);
  letter-spacing: 0.02em;
  font-family: var(--f-body);
}
.login-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0);
  transition: background var(--transition);
}
.login-btn:hover:not(:disabled)::before { background: rgba(255,255,255,0.08); }
.login-btn:hover:not(:disabled) { box-shadow: 0 8px 24px rgba(34,211,238,0.3), 0 0 0 1px rgba(34,211,238,0.4); }
.login-btn:active:not(:disabled) { transform: translateY(1px); }
.login-btn:disabled { opacity: 0.7; cursor: not-allowed; }
.btn-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.btn-arrow {
  transition: transform 0.2s;
}
.login-btn:hover .btn-arrow { transform: translateX(4px); }

.btn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 28px;
  line-height: 1;
  letter-spacing: -0.1em;
}
.dot-1, .dot-2, .dot-3 {
  animation: dotPulse 1.2s infinite;
  opacity: 0.3;
}
.dot-2 { animation-delay: 0.2s; }
.dot-3 { animation-delay: 0.4s; }
@keyframes dotPulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

.form-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 28px;
}
.footer-line { flex: 1; height: 1px; background: rgba(255,255,255,0.06); }
.footer-text { font-size: 11px; color: #334155; white-space: nowrap; letter-spacing: 0.05em; }

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .login-wrapper { flex-direction: column; }
  .brand-panel { padding: 40px 28px; }
  .brand-title { font-size: 28px; }
  .form-panel { width: 100%; padding: 40px 28px; }
}
</style>
