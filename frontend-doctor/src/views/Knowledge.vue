<template>
  <div class="page-wrap">
    <!-- Header -->
    <div class="page-header">
      <div>
        <div class="section-label">KNOWLEDGE BASE</div>
        <h1 class="page-title-text">知识库 <span>查询</span></h1>
      </div>
    </div>

    <!-- Search bar -->
    <div class="search-bar glass-card">
      <a-form layout="inline" :model="searchForm" @finish="handleSearch" style="width: 100%">
        <div class="search-inner">
          <a-input
            v-model:value="searchForm.keyword"
            placeholder="搜索疾病、症状、药物等医学关键词..."
            size="large"
            allow-clear
            class="search-input"
          >
            <template #prefix>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--c-text-muted)">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
            </template>
          </a-input>
          <a-select
            v-model:value="searchForm.type"
            size="large"
            style="width: 130px; flex-shrink: 0"
          >
            <a-select-option value="all">全部类型</a-select-option>
            <a-select-option value="disease">疾病</a-select-option>
            <a-select-option value="symptom">症状</a-select-option>
            <a-select-option value="drug">药物</a-select-option>
          </a-select>
          <button class="search-btn" type="submit" :class="{ loading }">
            {{ loading ? '搜索中...' : '搜索' }}
          </button>
        </div>
      </a-form>
    </div>

    <!-- Main content -->
    <div class="knowledge-grid">
      <!-- Search results -->
      <div class="results-col">
        <div class="glass-card results-card">
          <div class="card-header">
            <span class="panel-label">搜索结果</span>
            <span v-if="searchResults.length" class="mono result-count">{{ pagination.total }} 条</span>
          </div>

          <div v-if="loading" class="loading-state">
            <a-spin tip="搜索中..." />
          </div>
          <div v-else-if="!searchResults.length" class="empty-results">
            <div class="empty-icon-wrap">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--c-text-muted)">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
            </div>
            <p>输入关键词开始搜索</p>
          </div>
          <div v-else class="results-list">
            <div
              class="result-item"
              v-for="item in searchResults"
              :key="item.id || item.title"
              @click="viewDetail(item)"
              :class="{ active: currentDetail?.title === item.title }"
            >
              <div class="result-type-dot" :class="item.type || 'default'"></div>
              <div class="result-body">
                <div class="result-title">{{ item.title }}</div>
                <div class="result-desc" v-html="item.description"></div>
                <div class="result-tags" v-if="item.tags?.length">
                  <span class="result-tag" v-for="tag in (item.tags || []).slice(0, 4)" :key="tag">{{ tag }}</span>
                </div>
              </div>
              <div class="result-arrow">→</div>
            </div>

            <div class="results-pagination">
              <a-pagination
                v-model:current="pagination.current"
                :total="pagination.total"
                :pageSize="pagination.pageSize"
                size="small"
                @change="handleSearch"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Right panel -->
      <div class="right-col">
        <!-- Knowledge graph -->
        <div class="glass-card graph-card">
          <div class="card-header">
            <span class="panel-label">
              <span class="graph-dot"></span>
              知识图谱
            </span>
            <div class="graph-actions" v-if="selectedEntity">
              <button class="ghost-action" type="button" @click="resetGraphView">重置图谱</button>
              <button class="ghost-action primary" type="button" @click="openGraphModal">查看大图</button>
            </div>
          </div>
          <div v-if="selectedEntity" class="graph-meta-row">
            <span class="entity-chip">{{ selectedEntity }}</span>
            <span class="graph-stat">{{ filteredGraphData.nodes.length }} 节点 / {{ filteredGraphData.links.length }} 关系</span>
          </div>
          <div v-if="!selectedEntity" class="panel-placeholder">
            <p>点击搜索结果查看实体关系图谱</p>
          </div>
          <div v-else class="graph-stage">
            <div ref="graphContainer" class="graph-container"></div>
            <div v-if="graphLoading" class="graph-overlay">
              <a-spin />
            </div>
            <div v-else-if="!filteredGraphData.links.length" class="graph-overlay">
              <p>当前无可展示关系</p>
            </div>
          </div>
        </div>

        <!-- Clinical guidelines -->
        <div class="glass-card guidelines-card">
          <div class="card-header">
            <span class="panel-label">临床指南</span>
          </div>
          <div v-if="guidelinesLoading" class="panel-placeholder-sm">
            <a-spin size="small" />
          </div>
          <div v-else-if="!guidelines.length" class="panel-placeholder-sm">
            <p>暂无临床指南</p>
          </div>
          <div v-else class="guidelines-list">
            <a
              class="guideline-item"
              v-for="item in guidelines"
              :key="item.id || item.title"
              :href="item.url"
              target="_blank"
            >
              <div class="guideline-icon">📋</div>
              <div class="guideline-title">{{ item.title }}</div>
              <div class="guideline-arrow">↗</div>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Fullscreen Graph Modal -->
    <a-modal
      v-model:open="graphModalVisible"
      :footer="null"
      :width="'calc(100vw - 48px)'"
      wrap-class-name="graph-modal-wrap"
      class="graph-modal"
      @after-open-change="handleGraphModalOpenChange"
    >
      <template #title>
        <div class="modal-title-row">
          <div>
            <div class="section-label">KNOWLEDGE GRAPH</div>
            <div class="modal-title">知识图谱详情：{{ selectedEntity || '未选择实体' }}</div>
          </div>
          <span class="graph-stat strong">{{ filteredGraphData.nodes.length }} 节点 / {{ filteredGraphData.links.length }} 关系</span>
        </div>
      </template>

      <div class="graph-workspace">
        <aside class="graph-filter-panel">
          <div class="filter-section">
            <div class="filter-title">图谱范围</div>
            <label class="filter-field">
              <span>查询深度</span>
              <a-select v-model:value="graphQuery.depth" size="small" @change="reloadGraphWithQuery">
                <a-select-option :value="1">仅一跳关系</a-select-option>
                <a-select-option :value="2">两跳关系</a-select-option>
                <a-select-option :value="3">三跳关系</a-select-option>
              </a-select>
            </label>
            <label class="filter-field">
              <span>关系上限</span>
              <a-select v-model:value="graphQuery.limit" size="small" @change="reloadGraphWithQuery">
                <a-select-option :value="30">30</a-select-option>
                <a-select-option :value="60">60</a-select-option>
                <a-select-option :value="100">100</a-select-option>
                <a-select-option :value="160">160</a-select-option>
              </a-select>
            </label>
          </div>

          <div class="filter-section">
            <div class="filter-title">节点类型</div>
            <a-checkbox-group v-model:value="graphFilters.nodeCategories" class="filter-check-list">
              <a-checkbox v-for="option in nodeCategoryOptions" :key="option.value" :value="option.value">
                <span class="legend-dot" :style="{ background: option.color }"></span>
                {{ option.label }}
              </a-checkbox>
            </a-checkbox-group>
          </div>

          <div class="filter-section">
            <div class="filter-title">关系类型</div>
            <a-checkbox-group v-model:value="graphFilters.relationCategories" class="filter-check-list compact">
              <a-checkbox v-for="option in relationCategoryOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </a-checkbox>
            </a-checkbox-group>
          </div>

          <button class="reset-filter-btn" type="button" @click="resetGraphFilters">恢复默认筛选</button>
        </aside>

        <main class="graph-canvas-panel">
          <div ref="fullGraphContainer" class="graph-full-container"></div>
          <div v-if="graphLoading" class="panel-placeholder graph-full-placeholder">
            <a-spin tip="图谱加载中..." />
          </div>
          <div v-else-if="!filteredGraphData.links.length" class="panel-placeholder graph-full-placeholder">
            <div>
              <p>当前筛选条件无关系</p>
              <button class="reset-filter-btn inline" type="button" @click="resetGraphView">恢复默认图谱</button>
            </div>
          </div>
        </main>

        <aside class="graph-detail-panel">
          <div class="filter-title">节点详情</div>
          <div v-if="selectedGraphNode" class="node-detail-card">
            <div class="node-name">{{ selectedGraphNode.name }}</div>
            <div class="node-meta">
              <span>{{ nodeCategoryLabel(selectedGraphNode.category) }}</span>
              <span>{{ selectedGraphNode.hop === 0 ? '中心节点' : `${selectedGraphNode.hop} 跳关联` }}</span>
            </div>
            <button class="reset-filter-btn" type="button" @click="focusGraphEntity(selectedGraphNode.name)">
              以此为中心展开
            </button>
          </div>
          <div v-else class="node-empty">点击图中节点查看详情</div>

          <div class="detail-divider"></div>
          <div class="filter-title">可见关系</div>
          <div class="relation-list">
            <div v-for="link in filteredGraphData.links.slice(0, 12)" :key="`${link.source}-${link.relation}-${link.target}`" class="relation-row">
              <span>{{ link.source }}</span>
              <b>{{ link.label }}</b>
              <span>{{ link.target }}</span>
            </div>
          </div>
        </aside>
      </div>
    </a-modal>

    <!-- Detail Drawer -->
    <a-drawer
      v-model:open="detailVisible"
      title="知识详情"
      width="620"
    >
      <div v-if="currentDetail" class="detail-content">
        <div class="detail-title-row">
          <h2 class="detail-title">{{ currentDetail.title }}</h2>
          <span v-if="currentDetail.type" class="type-badge">{{ currentDetail.type }}</span>
        </div>
        <div class="detail-divider"></div>
        <div class="detail-body" v-html="currentDetail.content"></div>
        <div class="detail-divider"></div>
        <div class="related-section">
          <div class="section-label" style="margin-bottom:12px">相关实体</div>
          <div v-if="detailRelatedEntities.length" class="related-tags">
            <span
              class="related-tag"
              v-for="entity in detailRelatedEntities"
              :key="entity"
              @click="searchEntity(entity)"
            >{{ entity }}</span>
          </div>
          <div v-else class="related-empty">暂无相关实体</div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { message } from 'ant-design-vue'
import { searchKnowledge, getKnowledgeGraph, getClinicalGuidelines } from '../api/knowledge'

const NODE_COLORS = {
  Center: '#22d3ee',
  Disease: '#f87171',
  Symptom: '#fbbf24',
  Drug: '#34d399',
  Exam: '#60a5fa',
  Treatment: '#a78bfa',
  BodyPart: '#fb7185',
  Department: '#38bdf8',
  Food: '#84cc16',
  Other: '#94a3b8'
}

const NODE_LABELS = {
  Center: '中心实体',
  Disease: '疾病',
  Symptom: '症状',
  Drug: '药物',
  Exam: '检查',
  Treatment: '治疗',
  BodyPart: '身体部位',
  Department: '科室',
  Food: '饮食',
  Other: '其他'
}

const DEFAULT_NODE_CATEGORIES = ['Center', 'Disease', 'Symptom', 'Drug', 'Exam', 'Treatment', 'BodyPart', 'Department', 'Other']
const DEFAULT_RELATION_CATEGORIES = ['symptom', 'drug', 'exam', 'complication', 'treatment', 'department', 'other']

const relationCategoryOptions = [
  { label: '症状/表现', value: 'symptom' },
  { label: '药物', value: 'drug' },
  { label: '检查', value: 'exam' },
  { label: '并发症', value: 'complication' },
  { label: '治疗', value: 'treatment' },
  { label: '科室', value: 'department' },
  { label: '饮食', value: 'food' },
  { label: '其他', value: 'other' }
]

const nodeCategoryOptions = Object.entries(NODE_LABELS).map(([value, label]) => ({
  value,
  label,
  color: NODE_COLORS[value] || NODE_COLORS.Other
}))

const loading = ref(false)
const graphLoading = ref(false)
const guidelinesLoading = ref(false)
const searchForm = ref({ keyword: '', type: 'all' })
const searchResults = ref([])
const guidelines = ref([])
const currentDetail = ref(null)
const selectedEntity = ref(null)
const detailVisible = ref(false)
const graphModalVisible = ref(false)
const selectedGraphNode = ref(null)
const graphRawData = ref({ nodes: [], links: [], categories: [] })
const graphQuery = ref({ depth: 2, limit: 60 })
const graphFilters = ref({
  nodeCategories: [...DEFAULT_NODE_CATEGORIES],
  relationCategories: [...DEFAULT_RELATION_CATEGORIES]
})
const graphContainer = ref(null)
const fullGraphContainer = ref(null)
let graphInstance = null
let fullGraphInstance = null

const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  onChange: (page) => {
    pagination.value.current = page
    handleSearch()
  }
})

onMounted(() => { loadGuidelines() })

onBeforeUnmount(() => {
  if (graphInstance) graphInstance.dispose()
  if (fullGraphInstance) fullGraphInstance.dispose()
})

const filteredGraphData = computed(() => {
  const allowedNodes = new Set(graphFilters.value.nodeCategories)
  const allowedRelations = new Set(graphFilters.value.relationCategories)
  const rawNodes = graphRawData.value.nodes || []
  const rawLinks = graphRawData.value.links || []
  const visibleNodeNames = new Set(
    rawNodes
      .filter(node => allowedNodes.has(node.category || 'Other'))
      .map(node => node.name)
  )
  if (selectedEntity.value) visibleNodeNames.add(selectedEntity.value)

  const links = rawLinks.filter(link => (
    visibleNodeNames.has(link.source) &&
    visibleNodeNames.has(link.target) &&
    allowedRelations.has(link.category || 'other')
  ))
  const linkedNames = new Set([selectedEntity.value])
  links.forEach(link => {
    linkedNames.add(link.source)
    linkedNames.add(link.target)
  })

  const nodes = rawNodes.filter(node => linkedNames.has(node.name))
  const categories = nodeCategoryOptions
    .filter(option => nodes.some(node => node.category === option.value))
    .map(option => ({ name: option.value, label: option.label }))

  return { nodes, links, categories }
})

const detailRelatedEntities = computed(() => {
  const directEntities = currentDetail.value?.related_entities || []
  if (directEntities.length) return directEntities

  const currentTitle = currentDetail.value?.title
  if (!currentTitle || currentTitle !== selectedEntity.value) return []

  return (graphRawData.value.nodes || [])
    .filter(node => node.name && node.name !== currentTitle)
    .sort((a, b) => (a.hop || 99) - (b.hop || 99))
    .slice(0, 12)
    .map(node => node.name)
})

watch(filteredGraphData, () => {
  nextTick(() => {
    renderPreviewGraph()
    renderFullGraph()
  })
}, { deep: true })

const handleSearch = async () => {
  if (!searchForm.value.keyword.trim()) {
    message.warning('请输入搜索关键词')
    return
  }
  loading.value = true
  try {
    const response = await searchKnowledge({
      keyword: searchForm.value.keyword,
      page: pagination.value.current,
      page_size: pagination.value.pageSize
    })
    // 响应拦截器已返回 response.data，所以直接用 response.items
    searchResults.value = response?.items || []
    pagination.value.total = response?.total || 0
  } catch (error) {
    message.error('搜索失败')
  } finally {
    loading.value = false
  }
}

const viewDetail = async (item) => {
  currentDetail.value = item
  detailVisible.value = true
  selectedEntity.value = item.title
  selectedGraphNode.value = null
  await loadKnowledgeGraph(item.title)
}

const searchEntity = (entity) => {
  searchForm.value.keyword = entity
  handleSearch()
  detailVisible.value = false
}

const loadKnowledgeGraph = async (entity) => {
  if (!entity) return
  graphLoading.value = true
  try {
    console.log('[知识图谱] 开始加载实体:', entity)
    const response = await getKnowledgeGraph(entity, graphQuery.value)
    console.log('[知识图谱] API 返回:', response)
    // 响应拦截器已返回 response.data，所以直接用 response
    graphRawData.value = normalizeGraphData(response)

    console.log('[知识图谱] 图谱数据:', graphRawData.value)

    await nextTick()
    await nextTick() // 等待两次确保 DOM 更新完成

    // 使用 setTimeout 确保容器渲染完成
    setTimeout(() => {
      renderPreviewGraph()
      renderFullGraph()
    }, 50)
  } catch (error) {
    console.error('[知识图谱] 加载失败:', error)
    graphRawData.value = { nodes: [], links: [], categories: [] }
    message.error('知识图谱加载失败: ' + (error.message || '未知错误'))
  } finally {
    graphLoading.value = false
  }
}

const normalizeGraphData = (graphData = {}) => {
  const nodes = (graphData.nodes || []).map(node => ({
    ...node,
    category: node.category || 'Other',
    labels: node.labels || [node.category || 'Other'],
    hop: Number.isInteger(node.hop) ? node.hop : (node.name === selectedEntity.value ? 0 : 1)
  }))
  const links = (graphData.links || []).map(link => ({
    ...link,
    relation: link.relation || link.label || 'related',
    label: link.label || link.relation || '相关',
    category: link.category || 'other'
  }))
  return { nodes, links, categories: graphData.categories || [] }
}

const buildGraphOption = (graphData, isFull = false) => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    formatter: (params) => {
      if (params.dataType === 'edge') {
        return `${params.data.source} <br/>${params.data.label || params.data.relation} → ${params.data.target}`
      }
      const data = params.data || {}
      return `${data.name}<br/>类型：${nodeCategoryLabel(data.category)}<br/>层级：${data.hop === 0 ? '中心实体' : `${data.hop} 跳关联`}`
    }
  },
  legend: isFull ? {
    show: true,
    bottom: 8,
    textStyle: { color: '#94a3b8' },
    data: graphData.categories.map(category => category.name)
  } : { show: false },
  series: [{
    type: 'graph',
    layout: 'force',
    data: graphData.nodes.map(node => ({
      ...node,
      symbolSize: node.symbolSize || (node.hop === 0 ? 46 : node.hop === 1 ? 30 : 20),
      itemStyle: {
        color: NODE_COLORS[node.category] || NODE_COLORS.Other,
        opacity: node.hop === 0 ? 1 : 0.86,
        shadowBlur: node.hop === 0 ? 18 : 6,
        shadowColor: NODE_COLORS[node.category] || NODE_COLORS.Other
      },
      label: {
        show: isFull || node.hop <= 1,
        color: node.hop === 0 ? '#e0f2fe' : '#cbd5e1',
        fontSize: node.hop === 0 ? 13 : 11,
        fontWeight: node.hop === 0 ? 700 : 500
      }
    })),
    links: graphData.links.map(link => ({
      ...link,
      label: {
        show: isFull,
        formatter: link.label || '',
        color: '#94a3b8',
        fontSize: 10
      }
    })),
    categories: graphData.categories,
    roam: true,
    draggable: true,
    label: { show: true, position: 'right', color: '#94a3b8', fontSize: 11 },
    labelLayout: { hideOverlap: true },
    edgeSymbol: ['none', 'arrow'],
    edgeSymbolSize: [0, 8],
    lineStyle: { color: 'rgba(148,163,184,0.28)', curveness: 0.16, width: isFull ? 1.4 : 1 },
    emphasis: {
      focus: 'adjacency',
      label: { show: true },
      lineStyle: { width: 3, color: '#22d3ee' }
    },
    force: {
      repulsion: isFull ? 420 : 170,
      gravity: isFull ? 0.04 : 0.1,
      edgeLength: isFull ? [90, 180] : [70, 120],
      layoutAnimation: true
    }
  }]
})

const renderGraph = (container, instance, isFull = false) => {
  if (!container) return instance
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    setTimeout(() => renderGraph(container, instance, isFull), 100)
    return instance
  }

  const graphData = filteredGraphData.value
  if (instance?.getDom && instance.getDom() !== container) {
    instance.dispose()
    instance = null
  }

  if (!graphData.nodes.length || !graphData.links.length) {
    instance?.clear()
    return instance
  }

  if (!instance) {
    instance = echarts.init(container, 'dark')
    instance.on('click', (params) => {
      if (params.dataType === 'node') selectedGraphNode.value = params.data
    })
  }
  instance.setOption(buildGraphOption(graphData, isFull), true)
  instance.resize()
  return instance
}

const renderPreviewGraph = () => {
  graphInstance = renderGraph(graphContainer.value, graphInstance, false)
}

const renderFullGraph = () => {
  if (!graphModalVisible.value) return
  fullGraphInstance = renderGraph(fullGraphContainer.value, fullGraphInstance, true)
}

const resetGraphView = () => {
  graphQuery.value = { depth: 2, limit: 60 }
  graphFilters.value = {
    nodeCategories: [...DEFAULT_NODE_CATEGORIES],
    relationCategories: [...DEFAULT_RELATION_CATEGORIES]
  }
  selectedGraphNode.value = null
  if (selectedEntity.value) {
    loadKnowledgeGraph(selectedEntity.value)
  } else {
    renderPreviewGraph()
    renderFullGraph()
  }
}

const openGraphModal = async () => {
  graphModalVisible.value = true
  await nextTick()
  setTimeout(() => renderFullGraph(), 120)
}

const handleGraphModalOpenChange = (open) => {
  if (open) {
    nextTick(() => setTimeout(() => renderFullGraph(), 120))
  }
}

const resetGraphFilters = () => {
  graphFilters.value = {
    nodeCategories: [...DEFAULT_NODE_CATEGORIES],
    relationCategories: [...DEFAULT_RELATION_CATEGORIES]
  }
}

const reloadGraphWithQuery = () => {
  if (selectedEntity.value) loadKnowledgeGraph(selectedEntity.value)
}

const focusGraphEntity = async (entity) => {
  selectedEntity.value = entity
  selectedGraphNode.value = null
  await loadKnowledgeGraph(entity)
}

const nodeCategoryLabel = (category) => NODE_LABELS[category] || category || '其他'

const loadGuidelines = async () => {
  guidelinesLoading.value = true
  try {
    const response = await getClinicalGuidelines({ page: 1, page_size: 6 })
    // 响应拦截器已返回 response.data，所以直接用 response.items
    guidelines.value = response?.items || []
  } catch (error) {
    console.error('加载临床指南失败:', error)
  } finally {
    guidelinesLoading.value = false
  }
}
</script>

<style scoped>
/* Search bar */
.search-bar {
  margin-bottom: 20px;
  padding: 16px 20px;
}
.search-inner {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
}
.search-input {
  flex: 1 1 auto;
  min-width: 0;
}
.search-inner :deep(.ant-select) {
  display: none;
}
.search-btn {
  height: 40px;
  min-width: 120px;
  padding: 0 28px;
  background: linear-gradient(135deg, #0e7490, #22d3ee);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition);
  font-family: var(--f-body);
  flex-shrink: 0;
}
.search-btn:hover { box-shadow: 0 4px 16px rgba(34,211,238,0.3); }
.search-btn.loading { opacity: 0.7; cursor: not-allowed; }

/* Knowledge grid */
.knowledge-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
  align-items: start;
}

.results-col {}
.right-col { display: flex; flex-direction: column; gap: 16px; }

/* Results card */
.results-card { overflow: hidden; }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--c-border);
}
.panel-label {
  font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--c-text-sec);
  display: flex; align-items: center; gap: 7px;
}
.result-count { font-size: 12px; color: var(--c-text-muted); }
.entity-chip {
  font-size: 11px; padding: 2px 10px; border-radius: 20px;
  background: rgba(34,211,238,0.1); color: var(--c-primary); border: 1px solid var(--c-primary-border);
}
.graph-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--c-agent); box-shadow: 0 0 8px var(--c-agent);
  animation: pulse-ring 2.5s ease-in-out infinite;
}

.loading-state, .empty-results {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px; gap: 12px; color: var(--c-text-muted); font-size: 13px;
}
.empty-icon-wrap { opacity: 0.5; }

/* Results list */
.results-list {}
.result-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--c-border-subtle);
  cursor: pointer;
  transition: background var(--transition);
}
.result-item:last-child { border-bottom: none; }
.result-item:hover, .result-item.active {
  background: rgba(34,211,238,0.04);
}
.result-item.active { border-left: 3px solid var(--c-primary); padding-left: 15px; }

.result-type-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 5px;
}
.result-type-dot.disease { background: var(--c-danger); box-shadow: 0 0 5px var(--c-danger); }
.result-type-dot.symptom { background: var(--c-warning); box-shadow: 0 0 5px var(--c-warning); }
.result-type-dot.drug { background: var(--c-success); box-shadow: 0 0 5px var(--c-success); }
.result-type-dot.default { background: var(--c-primary); box-shadow: 0 0 5px var(--c-primary); }

.result-body { flex: 1; min-width: 0; }
.result-title { font-size: 14px; font-weight: 600; color: var(--c-text); margin-bottom: 4px; }
.result-desc { font-size: 12px; color: var(--c-text-sec); line-height: 1.5; max-height: 48px; overflow: hidden; margin-bottom: 6px; }
.result-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.result-tag {
  font-size: 10px; padding: 2px 7px; border-radius: 4px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--c-border-subtle); color: var(--c-text-muted);
}
.result-arrow { color: var(--c-text-muted); font-size: 14px; flex-shrink: 0; margin-top: 2px; }

.results-pagination {
  padding: 14px 18px;
  border-top: 1px solid var(--c-border);
  display: flex;
  justify-content: flex-end;
}

/* Graph */
.graph-card { overflow: hidden; }
.graph-actions { display: flex; align-items: center; gap: 8px; }
.ghost-action {
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--c-border);
  border-radius: 999px;
  background: rgba(255,255,255,0.035);
  color: var(--c-text-sec);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--transition);
}
.ghost-action:hover {
  color: var(--c-text);
  border-color: var(--c-primary-border);
  background: rgba(34,211,238,0.08);
}
.ghost-action.primary {
  color: var(--c-primary);
  border-color: var(--c-primary-border);
}
.graph-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 16px 0;
}
.graph-stat { font-size: 11px; color: var(--c-text-muted); }
.graph-stat.strong { color: var(--c-primary); font-weight: 700; }
.panel-placeholder, .panel-placeholder-sm {
  display: flex; align-items: center; justify-content: center;
  height: 240px; color: var(--c-text-muted); font-size: 12px;
}
.panel-placeholder-sm { height: 80px; }
.graph-stage {
  position: relative;
  min-height: 340px;
}
.graph-container { width: 100%; height: 340px; }
.graph-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8, 15, 28, 0.62);
  color: var(--c-text-muted);
  font-size: 12px;
  pointer-events: none;
}

/* Fullscreen graph */
:global(.graph-modal-wrap .ant-modal) {
  top: 24px;
  max-width: none;
  padding-bottom: 0;
}
:global(.graph-modal-wrap .ant-modal-content) {
  height: calc(100vh - 48px);
  background: rgba(8, 15, 28, 0.96);
  border: 1px solid var(--c-border);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.48);
}
:global(.graph-modal-wrap .ant-modal-body) {
  height: calc(100vh - 128px);
  padding: 0;
}
.modal-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-right: 32px;
}
.modal-title {
  margin-top: 4px;
  color: var(--c-text);
  font-family: var(--f-display);
  font-size: 18px;
  font-weight: 700;
}
.graph-workspace {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr) 280px;
  height: 100%;
  min-height: 0;
  border-top: 1px solid var(--c-border);
}
.graph-filter-panel,
.graph-detail-panel {
  min-height: 0;
  overflow-y: auto;
  padding: 18px;
  background: rgba(15, 23, 42, 0.58);
}
.graph-filter-panel { border-right: 1px solid var(--c-border); }
.graph-detail-panel { border-left: 1px solid var(--c-border); }
.graph-canvas-panel {
  min-width: 0;
  min-height: 0;
  position: relative;
  background:
    radial-gradient(circle at 50% 45%, rgba(34,211,238,0.09), transparent 34%),
    linear-gradient(135deg, rgba(255,255,255,0.02), transparent);
}
.graph-full-container {
  width: 100%;
  height: 100%;
  min-height: 560px;
}
.graph-full-placeholder {
  position: absolute;
  inset: 0;
  z-index: 2;
  background: rgba(8, 15, 28, 0.7);
  height: 100%;
  min-height: 560px;
  text-align: center;
}
.filter-section {
  padding-bottom: 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--c-border-subtle);
}
.filter-title {
  margin-bottom: 12px;
  color: var(--c-text);
  font-size: 13px;
  font-weight: 700;
}
.filter-field {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--c-text-sec);
  font-size: 12px;
}
.filter-check-list {
  display: grid;
  gap: 9px;
}
.filter-check-list.compact { gap: 7px; }
.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}
.reset-filter-btn {
  width: 100%;
  height: 34px;
  border: 1px solid var(--c-primary-border);
  border-radius: 8px;
  background: rgba(34,211,238,0.08);
  color: var(--c-primary);
  cursor: pointer;
  transition: all var(--transition);
}
.reset-filter-btn:hover {
  background: rgba(34,211,238,0.15);
  box-shadow: 0 0 16px rgba(34,211,238,0.12);
}
.reset-filter-btn.inline {
  width: auto;
  margin-top: 10px;
  padding: 0 14px;
}
.node-detail-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: 12px;
  background: rgba(255,255,255,0.035);
}
.node-name {
  color: var(--c-text);
  font-size: 17px;
  font-weight: 700;
}
.node-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.node-meta span {
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.05);
  color: var(--c-text-sec);
  font-size: 11px;
}
.node-empty {
  padding: 24px 12px;
  color: var(--c-text-muted);
  text-align: center;
  border: 1px dashed var(--c-border);
  border-radius: 12px;
}
.relation-list {
  display: grid;
  gap: 8px;
}
.relation-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 2px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(255,255,255,0.03);
  color: var(--c-text-sec);
  font-size: 12px;
  line-height: 1.45;
}
.relation-row b {
  color: var(--c-primary);
  font-size: 11px;
  font-weight: 700;
}

/* Guidelines */
.guidelines-card { overflow: hidden; }
.guidelines-list {}
.guideline-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-bottom: 1px solid var(--c-border-subtle);
  text-decoration: none;
  transition: background var(--transition);
  cursor: pointer;
}
.guideline-item:last-child { border-bottom: none; }
.guideline-item:hover { background: rgba(34,211,238,0.04); }
.guideline-icon { font-size: 14px; flex-shrink: 0; }
.guideline-title { flex: 1; font-size: 12.5px; color: var(--c-text-sec); line-height: 1.4; min-width: 0; }
.guideline-item:hover .guideline-title { color: var(--c-primary); }
.guideline-arrow { font-size: 12px; color: var(--c-text-muted); flex-shrink: 0; }

/* Detail drawer */
.detail-content {}
.detail-title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.detail-title { font-family: var(--f-display); font-size: 22px; font-weight: 600; color: var(--c-text); flex: 1; }
.type-badge {
  font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 20px;
  background: rgba(34,211,238,0.1); color: var(--c-primary); border: 1px solid var(--c-primary-border);
  text-transform: uppercase; letter-spacing: 0.06em;
}
.detail-divider { height: 1px; background: var(--c-border); margin: 16px 0; }
.detail-body { font-size: 14px; color: var(--c-text-sec); line-height: 1.8; }
.related-section {}
.related-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.related-empty {
  color: var(--c-text-muted);
  font-size: 12px;
}
.related-tag {
  font-size: 12px; padding: 5px 12px; border-radius: 20px; cursor: pointer;
  background: rgba(34,211,238,0.06); border: 1px solid var(--c-primary-border); color: var(--c-primary);
  transition: all var(--transition);
}
.related-tag:hover { background: rgba(34,211,238,0.14); transform: translateY(-1px); }

@media (max-width: 1100px) {
  .knowledge-grid { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .search-inner {
    flex-wrap: wrap;
  }
  .search-btn {
    width: 100%;
  }
}
</style>
