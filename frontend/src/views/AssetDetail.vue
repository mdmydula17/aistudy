<template>
  <div class="asset-detail" v-if="asset">
    <div class="breadcrumb">
      <router-link to="/">任务列表</router-link>
      <span>/</span>
      <router-link :to="`/tasks/${asset.task_id}`">任务详情</router-link>
      <span>/</span>
      <span>资产详情</span>
    </div>

    <div class="detail-header">
      <h2>{{ asset.title }}</h2>
      <div class="score-badge" :class="scoreClass(asset.confidence_score)">
        置信度 {{ (asset.confidence_score * 100).toFixed(0) }}%
      </div>
    </div>

    <div class="detail-card">
      <h3>核心逻辑</h3>
      <div class="markdown-content" v-html="renderMarkdown(asset.core_logic)"></div>
    </div>

    <div class="detail-card">
      <h3>可执行步骤</h3>
      <div v-if="parsedSop.length > 0" class="sop-list">
        <div v-for="step in parsedSop" :key="step.step" class="sop-item">
          <div class="sop-step">Step {{ step.step }}</div>
          <div class="sop-action">{{ step.action }}</div>
          <div class="sop-detail">{{ step.detail }}</div>
        </div>
      </div>
      <div v-else class="empty-hint">暂无步骤数据</div>
    </div>

    <div class="detail-card" v-if="asset.raw_text">
      <h3>原始文本</h3>
      <pre class="raw-text">{{ asset.raw_text }}</pre>
    </div>

    <div class="detail-card" v-if="asset.ocr_text">
      <h3>OCR 文本</h3>
      <pre class="raw-text">{{ asset.ocr_text }}</pre>
    </div>
  </div>

  <div v-else class="loading">加载中...</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAsset } from '../api'

const route = useRoute()
const asset = ref(null)

const parsedSop = computed(() => {
  if (!asset.value?.actionable_sop) return []
  try {
    return typeof asset.value.actionable_sop === 'string'
      ? JSON.parse(asset.value.actionable_sop)
      : asset.value.actionable_sop
  } catch {
    return []
  }
})

const scoreClass = (score) => {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.6) return 'score-mid'
  return 'score-low'
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return text
    .replace(/## (.*)/g, '<h3>$1</h3>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
}

onMounted(async () => {
  try {
    asset.value = await getAsset(route.params.id)
  } catch (e) {
    alert('加载失败')
  }
})
</script>

<style scoped>
.breadcrumb {
  font-size: 14px;
  color: #999;
  margin-bottom: 20px;
}

.breadcrumb a {
  color: #1677ff;
  text-decoration: none;
}

.breadcrumb span {
  margin: 0 8px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.detail-header h2 {
  font-size: 22px;
}

.score-badge {
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.score-high { background: #f6ffed; color: #389e0d; }
.score-mid { background: #fffbe6; color: #d48806; }
.score-low { background: #fff1f0; color: #cf1322; }

.detail-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.detail-card h3 {
  font-size: 16px;
  margin-bottom: 16px;
  color: #333;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.markdown-content {
  line-height: 1.8;
  font-size: 15px;
  color: #444;
}

.markdown-content h3 {
  font-size: 16px;
  margin: 16px 0 8px;
  border: none;
  padding: 0;
}

.sop-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sop-item {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  border-left: 4px solid #1677ff;
}

.sop-step {
  font-size: 12px;
  color: #1677ff;
  font-weight: 600;
  margin-bottom: 4px;
}

.sop-action {
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 4px;
}

.sop-detail {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

.raw-text {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
}

.empty-hint {
  color: #999;
  text-align: center;
  padding: 24px 0;
}

.loading {
  text-align: center;
  padding: 64px 0;
  color: #999;
}
</style>
