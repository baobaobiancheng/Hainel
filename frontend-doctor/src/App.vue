<template>
  <a-config-provider :theme="antTheme">
    <router-view />
  </a-config-provider>
</template>

<script setup>
import { onMounted } from 'vue'
import { theme } from 'ant-design-vue'
import { useAuthStore } from './store/auth'

const authStore = useAuthStore()

const antTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#22d3ee',
    colorSuccess: '#34d399',
    colorWarning: '#fbbf24',
    colorError: '#f87171',
    colorInfo: '#818cf8',
    colorBgBase: '#080e1a',
    colorBgLayout: '#080e1a',
    colorBgContainer: '#111c30',
    colorBgElevated: '#172540',
    colorBgSpotlight: '#1a2d4a',
    colorText: '#e2e8f0',
    colorTextSecondary: '#94a3b8',
    colorTextTertiary: '#64748b',
    colorBorder: 'rgba(34, 211, 238, 0.14)',
    colorBorderSecondary: 'rgba(255,255,255,0.06)',
    fontFamily: "'Noto Sans SC', -apple-system, sans-serif",
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    fontSize: 14,
    lineHeight: 1.6,
    colorLink: '#22d3ee',
    colorLinkHover: '#67e8f9',
    colorLinkActive: '#06b6d4',
    controlHeight: 36,
    controlHeightLG: 44,
  },
  components: {
    Table: {
      headerBg: '#172540',
      rowHoverBg: 'rgba(34,211,238,0.06)',
      borderColor: 'rgba(34,211,238,0.10)',
    },
    Card: {
      colorBorderSecondary: 'rgba(34,211,238,0.12)',
    },
    Menu: {
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
      darkItemSelectedBg: 'rgba(34,211,238,0.12)',
      darkItemSelectedColor: '#22d3ee',
      darkItemColor: '#94a3b8',
      darkItemHoverColor: '#e2e8f0',
      darkItemHoverBg: 'rgba(255,255,255,0.05)',
      itemMarginInline: 8,
      itemBorderRadius: 8,
    },
    Modal: {
      contentBg: '#111c30',
      headerBg: '#111c30',
    },
    Drawer: {
      colorBgElevated: '#111c30',
    },
  }
}

onMounted(() => {
  const token = localStorage.getItem('token')
  if (token) {
    authStore.setToken(token)
  }
})
</script>

<style>
/* ─── Design Tokens ─── */
:root {
  --c-primary: #22d3ee;
  --c-primary-dim: rgba(34, 211, 238, 0.08);
  --c-primary-glow: rgba(34, 211, 238, 0.25);
  --c-primary-border: rgba(34, 211, 238, 0.18);
  --c-bg-base: #080e1a;
  --c-bg-surface: #0d1829;
  --c-bg-card: #111c30;
  --c-bg-elevated: #172540;
  --c-border: rgba(34, 211, 238, 0.12);
  --c-border-subtle: rgba(255, 255, 255, 0.05);
  --c-text: #e2e8f0;
  --c-text-sec: #94a3b8;
  --c-text-muted: #475569;
  --c-success: #34d399;
  --c-warning: #fbbf24;
  --c-danger: #f87171;
  --c-agent: #a78bfa;
  --c-agent-dim: rgba(167, 139, 250, 0.12);
  --f-display: 'Playfair Display', Georgia, serif;
  --f-mono: 'IBM Plex Mono', 'Courier New', monospace;
  --f-body: 'Noto Sans SC', -apple-system, sans-serif;
  --shadow-card: 0 4px 32px rgba(0, 0, 0, 0.5), 0 1px 6px rgba(0, 0, 0, 0.3);
  --shadow-glow: 0 0 24px rgba(34, 211, 238, 0.12);
  --radius: 10px;
  --radius-sm: 6px;
  --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ─── Reset ─── */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

html, body { height: 100%; background: var(--c-bg-base); }

body {
  font-family: var(--f-body);
  color: var(--c-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app { width: 100%; height: 100vh; overflow: hidden; }

/* ─── Scrollbar ─── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(34, 211, 238, 0.18); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(34, 211, 238, 0.36); }

/* ─── Ant Design global overrides ─── */
.ant-layout { background: var(--c-bg-base) !important; }
.ant-layout-content { background: var(--c-bg-base) !important; }

.ant-card {
  background: var(--c-bg-card) !important;
  border: 1px solid var(--c-border) !important;
  box-shadow: var(--shadow-card) !important;
}
.ant-card-head {
  border-bottom: 1px solid var(--c-border) !important;
  background: transparent !important;
}
.ant-card-head-title {
  font-family: var(--f-body);
  font-weight: 600;
  letter-spacing: 0.01em;
}

.ant-table {
  background: var(--c-bg-card) !important;
  border-radius: var(--radius) !important;
  overflow: hidden;
}
.ant-table-thead > tr > th {
  background: var(--c-bg-elevated) !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  color: var(--c-text-sec) !important;
  border-bottom: 1px solid var(--c-border) !important;
  padding: 12px 16px !important;
}
.ant-table-tbody > tr > td {
  border-bottom: 1px solid var(--c-border-subtle) !important;
  transition: background var(--transition) !important;
}
.ant-table-tbody > tr:hover > td {
  background: rgba(34, 211, 238, 0.04) !important;
}
.ant-table-tbody > tr:last-child > td { border-bottom: none !important; }

.ant-modal-content {
  background: var(--c-bg-card) !important;
  border: 1px solid var(--c-border) !important;
  box-shadow: 0 24px 80px rgba(0,0,0,0.7) !important;
}
.ant-modal-header {
  background: transparent !important;
  border-bottom: 1px solid var(--c-border) !important;
  padding: 20px 24px !important;
}
.ant-modal-title { font-family: var(--f-body); font-weight: 600; font-size: 16px; }
.ant-modal-footer { border-top: 1px solid var(--c-border) !important; }

.ant-drawer-content { background: var(--c-bg-card) !important; }
.ant-drawer-header {
  background: transparent !important;
  border-bottom: 1px solid var(--c-border) !important;
  padding: 20px 24px !important;
}
.ant-drawer-title { font-family: var(--f-body); font-weight: 600; font-size: 16px; }

.ant-tag {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  border-radius: 4px;
  padding: 1px 8px;
}

.ant-btn-primary {
  background: var(--c-primary) !important;
  border-color: var(--c-primary) !important;
  color: #080e1a !important;
  font-weight: 600 !important;
}
.ant-btn-primary:hover {
  background: #67e8f9 !important;
  border-color: #67e8f9 !important;
  box-shadow: 0 0 16px var(--c-primary-glow) !important;
}

.ant-input, .ant-input-affix-wrapper,
.ant-select-selector, .ant-picker {
  background: var(--c-bg-elevated) !important;
  border-color: var(--c-border) !important;
}
.ant-input:focus, .ant-input-affix-wrapper-focused,
.ant-select-focused .ant-select-selector {
  border-color: var(--c-primary) !important;
  box-shadow: 0 0 0 3px var(--c-primary-dim) !important;
}

.ant-descriptions-item-label {
  background: var(--c-bg-elevated) !important;
  color: var(--c-text-sec) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
}
.ant-descriptions-bordered .ant-descriptions-item-label,
.ant-descriptions-bordered .ant-descriptions-item-content {
  border-color: var(--c-border) !important;
}

.ant-statistic-title { color: var(--c-text-sec) !important; font-size: 12px !important; }
.ant-statistic-content { font-family: var(--f-mono) !important; }

.ant-divider { border-color: var(--c-border) !important; }
.ant-divider-inner-text { color: var(--c-text-sec) !important; font-size: 12px !important; font-weight: 500 !important; }

.ant-empty-description { color: var(--c-text-muted) !important; }

.ant-pagination .ant-pagination-item {
  background: var(--c-bg-elevated) !important;
  border-color: var(--c-border) !important;
}
.ant-pagination .ant-pagination-item-active {
  background: var(--c-primary-dim) !important;
  border-color: var(--c-primary) !important;
}
.ant-pagination .ant-pagination-item-active a { color: var(--c-primary) !important; }

.ant-badge-status-success .ant-badge-status-dot { background: var(--c-success) !important; }

/* ─── Page layout utility ─── */
.page-wrap {
  padding: 24px 28px;
  min-height: 100%;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.page-title-text {
  font-family: var(--f-display);
  font-size: 24px;
  font-weight: 600;
  color: var(--c-text);
  letter-spacing: -0.01em;
}
.page-title-text span {
  color: var(--c-primary);
}

/* ─── Card base ─── */
.glass-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
}

/* ─── Section label ─── */
.section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-text-muted);
  margin-bottom: 12px;
}

/* ─── Glow badge ─── */
.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 6px;
}
.status-dot.active { background: var(--c-success); box-shadow: 0 0 6px var(--c-success); }
.status-dot.pending { background: var(--c-warning); box-shadow: 0 0 6px var(--c-warning); }
.status-dot.completed { background: var(--c-text-muted); }
.status-dot.cancelled { background: var(--c-danger); }

/* ─── Keyframes ─── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes pulse-ring {
  0% { transform: scale(0.9); opacity: 0.6; }
  50% { transform: scale(1.05); opacity: 0.3; }
  100% { transform: scale(0.9); opacity: 0.6; }
}
@keyframes scanline {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(200%); }
}
</style>
