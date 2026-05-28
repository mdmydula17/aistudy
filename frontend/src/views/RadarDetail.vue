<template>
  <div class="radar-detail" v-if="task">
    <div class="breadcrumb">
      <router-link to="/">🟢 雷达列表</router-link>
      <span>/</span>
      <span>任务详情</span>
    </div>

    <div class="detail-header">
      <div class="detail-title-row">
        <h2>🔍 {{ task.keyword }}</h2>
        <span :class="['status-badge', `status-${task.status}`]">
          {{ statusLabel(task.status) }}
        </span>
      </div>
      <div class="detail-meta">
        <span>ID: {{ task.id }}</span>
        <span>创建: {{ formatTime(task.created_at) }}</span>
        <span>更新: {{ formatTime(task.updated_at) }}</span>
      </div>
      <div v-if="task.error" class="detail-error">
        ❌ {{ task.error }}
      </div>
    </div>

    <div v-if="task.status === 'pending'" class="pending-hint">
      <div class="spinner"></div>
      <span>雷达扫描中，请稍候...</span>
    </div>

    <div v-else-if="task.results && task.results.length > 0" class="results-section">
      <h3>📋 扫描结果 ({{ task.results.length }} 条)</h3>
      <div class="result-cards">
        <div v-for="(item, idx) in task.results" :key="idx" class="result-card">
          <div class="result-index">{{ idx + 1 }}</div>
          <div class="result-body">
            <div class="result-title">
              <a :href="item.url" target="_blank" rel="noopener">{{ item.title || '(无标题)' }}</a>
            </div>
            <div class="result-meta">
              <span v-if="item.author">👤 {{ item.author }}</span>
              <span v-if="item.likes">❤️ {{ item.likes }}</span>
            </div>
            <div class="result-url">{{ item.url }}</div>
          </div>
        </div>
      </div>

      <div class="action-bar">
        <button @click="startSynth" class="btn btn-purple">
          🟣 一键开启炼丹
        </button>
      </div>
    </div>

    <div v-else-if="task.status === 'failed'" class="failed-section">
      <p>雷达扫描失败，请尝试其他关键词或稍后重试。</p>
      <button @click="$router.push('/')" class="btn btn-green">返回重试</button>
    </div>
  </div>

  <div v-else class="loading">加载中...</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getRadarTask, createSynthTask } from '../api'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id
const task = ref(null)
let pollTimer = null

const statusLabel = (status) => {
  const map = { pending: '扫描中', processing: '扫描中', completed: '已完成', failed: '失败' }
  return map[status] || status
}

const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

const fetchTask = async () => {
  try {
    task.value = await getRadarTask(taskId)
  } catch (e) {
    console.error('Failed to fetch task:', e)
  }
}

const startSynth = async () => {
  try {
    await createSynthTask(task.value.keyword, task.value.id)
    router.push('/synth')
  } catch (e) {
    alert('创建炼丹任务失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  fetchTask()
  pollTimer = setInterval(() => {
    if (task.value?.status === 'pending') fetchTask()
  }, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.breadcrumb { font-size: 14px; color: #999; margin-bottom: 20px; }
.breadcrumb a { color: #52c41a; text-decoration: none; }
.breadcrumb span { margin: 0 8px; }

.detail-header {
  background: white; border-radius: 12px; padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 24px;
}
.detail-title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.detail-title-row h2 { font-size: 20px; font-weight: 600; }
.detail-meta { display: flex; gap: 16px; font-size: 13px; color: #999; }
.detail-error { margin-top: 12px; padding: 12px; background: #fff1f0; border-radius: 8px; color: #cf1322; font-size: 14px; }

.status-badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.status-pending { background: #fff7e6; color: #d48806; }
.status-processing { background: #e6f7ff; color: #0958d9; }
.status-completed { background: #f6ffed; color: #389e0d; }
.status-failed { background: #fff1f0; color: #cf1322; }

.pending-hint {
  text-align: center; padding: 48px; background: white; border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); display: flex; align-items: center;
  justify-content: center; gap: 12px; color: #d48806; font-size: 16px;
}
.spinner {
  width: 20px; height: 20px; border: 3px solid #f0f0f0; border-top: 3px solid #52c41a;
  border-radius: 50%; animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.results-section {
  background: white; border-radius: 12px; padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.results-section h3 { font-size: 16px; font-weight: 600; margin-bottom: 16px; }

.result-cards { display: flex; flex-direction: column; gap: 12px; }
.result-card {
  display: flex; gap: 16px; padding: 16px; border: 1px solid #f0f0f0;
  border-radius: 8px; transition: all 0.2s;
}
.result-card:hover { border-color: #52c41a; background: #f6ffed; }
.result-index {
  width: 32px; height: 32px; border-radius: 50%; background: #52c41a; color: white;
  display: flex; align-items: center; justify-content: center; font-size: 14px;
  font-weight: 600; flex-shrink: 0;
}
.result-body { flex: 1; }
.result-title a { color: #333; text-decoration: none; font-size: 15px; font-weight: 500; line-height: 1.5; }
.result-title a:hover { color: #722ed1; }
.result-meta { display: flex; gap: 12px; font-size: 13px; color: #999; margin-top: 6px; }
.result-url { font-size: 12px; color: #bbb; margin-top: 4px; word-break: break-all; }

.action-bar { margin-top: 24px; padding-top: 16px; border-top: 1px solid #f0f0f0; text-align: center; }

.btn {
  padding: 12px 28px; border: none; border-radius: 8px; font-size: 15px;
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.btn-purple { background: #722ed1; color: white; }
.btn-purple:hover { background: #9254de; }
.btn-green { background: #52c41a; color: white; }
.btn-green:hover { background: #73d13d; }

.failed-section {
  text-align: center; padding: 48px; background: white; border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); color: #999;
}
.failed-section p { margin-bottom: 16px; }

.loading { text-align: center; padding: 64px 0; color: #999; font-size: 16px; }
</style>
