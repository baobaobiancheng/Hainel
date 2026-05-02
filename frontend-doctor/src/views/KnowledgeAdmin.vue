<template>
  <div class="page-wrap knowledge-admin-page">
    <div class="page-header">
      <div>
        <div class="section-label">KNOWLEDGE OPERATIONS</div>
        <h1 class="page-title-text">知识库管理 <span>导入与状态</span></h1>
      </div>
      <a-button :loading="statsLoading" @click="loadStats">刷新</a-button>
    </div>

    <div class="stats-grid">
      <div class="stat-card accent-cyan">
        <div class="stat-label">运行状态</div>
        <div class="stat-value">{{ statusLabel }}</div>
      </div>
      <div class="stat-card accent-blue">
        <div class="stat-label">向量条目数</div>
        <div class="stat-value mono">{{ chromaStats.total_documents ?? 0 }}</div>
      </div>
      <div class="stat-card accent-amber">
        <div class="stat-label">Embedding 模型</div>
        <div class="stat-value compact break">{{ chromaStats.embedding_model || '--' }}</div>
      </div>
      <div class="stat-card accent-violet">
        <div class="stat-label">上传目录</div>
        <div class="stat-value compact mono">{{ uploadDir }}</div>
      </div>
    </div>

    <div class="content-grid">
      <div class="main-col">
        <div class="glass-card panel-card">
          <div class="panel-head">
            <span class="panel-label">单文件导入</span>
            <a-tag :color="statusTagColor">{{ statusLabel }}</a-tag>
          </div>

          <a-upload-dragger
            class="upload-panel"
            :before-upload="handleFileUpload"
            :show-upload-list="false"
            accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md"
          >
            <p class="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p class="ant-upload-text">点击或拖拽文件上传</p>
            <p class="ant-upload-hint">PDF / Word / Excel / TXT / Markdown</p>
          </a-upload-dragger>

          <div v-if="uploading" class="progress-block">
            <a-progress :percent="uploadProgress" status="active" />
          </div>

          <div v-if="lastFileImport" class="result-strip">
            <span class="result-chip">最近导入</span>
            <span class="result-text">{{ lastFileImport.file_path || lastFileImport.message }}</span>
            <a-button size="small" @click="copyText(lastFileImport.file_path)">复制路径</a-button>
          </div>
        </div>

        <div class="glass-card panel-card">
          <div class="panel-head">
            <span class="panel-label">目录导入</span>
          </div>

          <div class="directory-form">
            <a-input
              v-model:value="directoryPath"
              class="directory-input"
              placeholder="输入服务器目录路径"
              @pressEnter="handleDirectoryImport"
            />
            <button class="search-btn directory-btn" type="button" @click="handleDirectoryImport">
              {{ importingDirectory ? '导入中...' : '导入' }}
            </button>
          </div>

          <div v-if="lastDirectoryImport" class="result-strip">
            <span class="result-chip">最近目录</span>
            <span class="result-text">{{ lastDirectoryImport.directory || '--' }}</span>
          </div>
        </div>
      </div>

      <div class="side-col">
        <div class="glass-card panel-card search-panel">
          <div class="panel-head">
            <span class="panel-label">搜索测试</span>
            <span v-if="searchTouched" class="panel-meta">{{ searchResults.length }} 条结果</span>
          </div>

          <div class="search-toolbar">
            <a-input
              v-model:value="testQuery"
              allow-clear
              placeholder="输入关键词"
              class="search-input"
              @pressEnter="handleTestSearch"
            >
              <template #prefix>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--c-text-muted)">
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.35-4.35" />
                </svg>
              </template>
            </a-input>
            <a-input-number v-model:value="topK" :min="1" :max="20" class="topk-input" />
            <button class="search-btn" type="button" @click="handleTestSearch">
              {{ testingSearch ? '查询中...' : '查询' }}
            </button>
          </div>

          <div v-if="searchResults.length" class="search-list">
            <button
              v-for="(item, index) in searchResults"
              :key="item.id || index"
              class="search-item"
              type="button"
            >
              <div class="search-item-head">
                <div class="search-item-main">
                  <span class="search-order mono">#{{ index + 1 }}</span>
                  <span class="search-item-title">{{ item.title }}</span>
                </div>
                <span class="search-score">置信度: {{ scoreText(item.score) }}</span>
              </div>
              <div class="search-item-desc">{{ item.description || item.content || '--' }}</div>
            </button>
          </div>
          <a-empty v-else-if="searchTouched && !testingSearch" description="暂无结果" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import {
  getKnowledgeStats,
  importDirectory,
  importDocument,
  searchKnowledge
} from '../api/knowledge'

const stats = ref({})
const statsLoading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const importingDirectory = ref(false)
const testingSearch = ref(false)

const directoryPath = ref('')
const testQuery = ref('')
const topK = ref(5)
const searchTouched = ref(false)

const lastFileImport = ref(null)
const lastDirectoryImport = ref(null)
const searchResults = ref([])

const chromaStats = computed(() => stats.value.chroma || {})
const uploadDir = computed(() => stats.value.upload_dir || 'uploads')

const statusLabel = computed(() => {
  if (chromaStats.value.status === 'ready') return '已就绪'
  if (chromaStats.value.status === 'failed') return '失败'
  return '加载中'
})

const statusTagColor = computed(() => {
  if (chromaStats.value.status === 'ready') return 'green'
  if (chromaStats.value.status === 'failed') return 'red'
  return 'orange'
})

onMounted(() => {
  loadStats()
})

const loadStats = async () => {
  statsLoading.value = true
  try {
    stats.value = await getKnowledgeStats()
  } finally {
    statsLoading.value = false
  }
}

const handleFileUpload = async (file) => {
  uploading.value = true
  uploadProgress.value = 40

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await importDocument(formData)
    uploadProgress.value = 100
    lastFileImport.value = response
    message.success(response.message || '导入成功')
    await loadStats()
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || '导入失败')
  } finally {
    uploading.value = false
  }

  return false
}

const handleDirectoryImport = async () => {
  if (!directoryPath.value.trim()) {
    message.warning('请输入目录路径')
    return
  }

  importingDirectory.value = true
  try {
    const response = await importDirectory({
      directory: directoryPath.value.trim(),
      recursive: true
    })
    lastDirectoryImport.value = response
    message.success(response.message || '导入成功')
    await loadStats()
  } catch (error) {
    message.error(error.response?.data?.detail || error.message || '导入失败')
  } finally {
    importingDirectory.value = false
  }
}

const handleTestSearch = async () => {
  if (!testQuery.value.trim()) {
    message.warning('请输入关键词')
    return
  }

  testingSearch.value = true
  searchTouched.value = true
  try {
    const response = await searchKnowledge({
      keyword: testQuery.value.trim(),
      page_size: topK.value
    })
    searchResults.value = response.items || []
  } catch (error) {
    searchResults.value = []
    message.error(error.response?.data?.detail || error.message || '搜索失败')
  } finally {
    testingSearch.value = false
  }
}

const scoreText = (score) => {
  const value = Number(score)
  if (!Number.isFinite(value)) return '--'
  return `${(value * 100).toFixed(1)}%`
}

const copyText = async (text) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(String(text))
    message.success('已复制')
  } catch (error) {
    message.error('复制失败')
  }
}
</script>

<style scoped>
.knowledge-admin-page {
  display: grid;
  gap: 18px;
}

.page-wrap {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--c-primary, #22d3ee);
  margin-bottom: 4px;
}

.page-title-text {
  font-size: 24px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
}

.page-title-text span {
  font-weight: 400;
  color: #64748b;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 92px;
  padding: 16px 18px 14px;
  border-radius: 18px;
  border: 1px solid var(--c-border-subtle);
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.12), transparent 45%);
}

.stat-card::after {
  content: '';
  position: absolute;
  inset: auto 0 0 0;
  height: 3px;
  background: currentColor;
  opacity: 0.75;
}

.accent-cyan {
  color: #22d3ee;
}

.accent-blue {
  color: #60a5fa;
}

.accent-amber {
  color: #f59e0b;
}

.accent-violet {
  color: #a78bfa;
}

.stat-label {
  color: var(--c-text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  line-height: 1.2;
}

.stat-value {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text);
  line-height: 1.2;
}

.stat-value.compact {
  font-size: 15px;
  line-height: 1.4;
}

.accent-blue .stat-value.mono {
  font-size: 18px;
}

.accent-cyan .stat-value {
  font-size: 20px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 1fr);
  gap: 18px;
}

.main-col,
.side-col {
  display: grid;
  gap: 18px;
}

.glass-card {
  background: var(--c-bg-card);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
}

.panel-card {
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.panel-label {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-text-sec);
}

.panel-meta {
  color: var(--c-text-muted);
  font-size: 12px;
  font-family: 'SF Mono', 'Monaco', monospace;
}

.upload-panel :deep(.ant-upload) {
  min-height: 182px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.02);
}

.progress-block {
  margin-top: 14px;
}

.directory-form {
  display: flex;
  align-items: stretch;
  gap: 0;
}

.directory-input :deep(.ant-input) {
  height: 44px;
  line-height: 44px;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.directory-input :deep(.ant-input),
.search-input :deep(.ant-input-affix-wrapper .ant-input),
.topk-input :deep(.ant-input-number),
.topk-input :deep(.ant-input-number-input) {
  color: var(--c-text);
  font-size: 14px;
}

.directory-input :deep(.ant-input),
.topk-input :deep(.ant-input-number) {
  border: 1px solid rgba(34, 211, 238, 0.14);
  background: rgba(22, 35, 62, 0.94);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.directory-input :deep(.ant-input::placeholder),
.search-input :deep(.ant-input::placeholder),
.topk-input :deep(.ant-input-number-input::placeholder) {
  color: rgba(148, 163, 184, 0.72);
}

.directory-input :deep(.ant-input:hover),
.directory-input :deep(.ant-input:focus),
.topk-input :deep(.ant-input-number:hover),
.topk-input :deep(.ant-input-number-focused) {
  border-color: rgba(56, 189, 248, 0.34);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.08);
  background: rgba(24, 39, 68, 0.98);
}

.directory-btn {
  height: 44px;
  min-width: 112px;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  flex-shrink: 0;
}

.result-strip {
  margin-top: 14px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--c-border-subtle);
}

.result-chip {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #22d3ee;
}

.result-text {
  color: var(--c-text-sec);
  font-size: 12px;
  word-break: break-all;
}

.search-panel {
  min-height: 100%;
}

.search-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 102px 120px;
  gap: 12px;
  align-items: stretch;
}

/* 关键词：仅 affix 外框一层边框，内层 input 透明无边框 */
.search-input :deep(.ant-input-affix-wrapper) {
  display: flex;
  align-items: center;
  min-height: 44px;
  height: 44px;
  border-radius: 14px;
  padding-inline: 14px;
  border: 1px solid rgba(34, 211, 238, 0.14);
  background: rgba(22, 35, 62, 0.94);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.search-input :deep(.ant-input-affix-wrapper .ant-input) {
  flex: 1 1 auto;
  min-width: 0;
  height: auto;
  line-height: 1.45;
  border: none;
  box-shadow: none;
  background: transparent;
  padding-inline: 0;
}

.search-input :deep(.ant-input-affix-wrapper .ant-input:hover),
.search-input :deep(.ant-input-affix-wrapper .ant-input:focus) {
  border: none;
  box-shadow: none;
  background: transparent;
}

.search-input :deep(.ant-input-affix-wrapper:hover),
.search-input :deep(.ant-input-affix-wrapper-focused) {
  border-color: rgba(56, 189, 248, 0.34);
  box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.08);
  background: rgba(24, 39, 68, 0.98);
}

.search-input :deep(.ant-input-prefix) {
  margin-inline-end: 10px;
  color: rgba(148, 163, 184, 0.76);
}

.topk-input :deep(.ant-input-number) {
  min-height: 44px;
  height: 44px;
  width: 100%;
  border-radius: 14px;
}

.topk-input :deep(.ant-input-number-input) {
  height: 44px;
  line-height: 44px;
  padding-inline: 14px;
}

.topk-input :deep(.ant-input-number-handler-wrap) {
  height: 44px;
  border-start-end-radius: 14px;
  border-end-end-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
}

.topk-input :deep(.ant-input-number-handler) {
  height: 22px;
  line-height: 20px;
}

.search-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
  min-height: 44px;
  height: 44px;
  min-width: 112px;
  box-sizing: border-box;
  border: 0;
  border-radius: 14px;
  padding: 0 18px;
  background: linear-gradient(135deg, #22d3ee 0%, #38bdf8 100%);
  color: #03131d;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
  box-shadow: 0 10px 24px rgba(34, 211, 238, 0.18);
}

.search-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(34, 211, 238, 0.22);
}

.search-btn:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 3px rgba(34, 211, 238, 0.12),
    0 14px 28px rgba(34, 211, 238, 0.22);
}

.search-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
  box-shadow: 0 10px 24px rgba(34, 211, 238, 0.12);
}

.search-btn:active {
  transform: translateY(0);
}

.search-list {
  margin-top: 16px;
  display: grid;
  gap: 12px;
}

.search-item {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid var(--c-border-subtle);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)),
    rgba(255, 255, 255, 0.02);
  text-align: left;
  transition: border-color 0.18s ease, transform 0.18s ease, background 0.18s ease;
}

.search-item:hover {
  border-color: rgba(34, 211, 238, 0.24);
  transform: translateY(-1px);
  background:
    linear-gradient(180deg, rgba(34, 211, 238, 0.07), rgba(255, 255, 255, 0.02)),
    rgba(255, 255, 255, 0.025);
}

.search-item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.search-item-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.search-order {
  color: var(--c-text-muted);
  font-size: 12px;
}

.search-item-title {
  color: var(--c-text);
  font-size: 14px;
  font-weight: 700;
}

.search-score {
  color: #22d3ee;
  font-family: 'SF Mono', 'Monaco', monospace;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.search-item-desc {
  margin-top: 10px;
  color: var(--c-text-sec);
  font-size: 12px;
  line-height: 1.7;
}

.mono {
  font-family: 'SF Mono', 'Monaco', monospace;
}

.break {
  word-break: break-all;
}

@media (max-width: 1360px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .page-header,
  .stats-grid,
  .search-toolbar,
  .result-strip {
    display: grid;
    grid-template-columns: 1fr;
  }

  .directory-form {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .directory-input :deep(.ant-input),
  .directory-btn {
    border-radius: 12px;
  }
}
</style>
