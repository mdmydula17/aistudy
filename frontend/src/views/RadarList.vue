<template>
  <div class="radar-list">
    <div class="page-header">
      <h2>🟢 爆款雷达</h2>
      <p class="subtitle">输入关键词，扫描小红书高热度笔记列表</p>
    </div>

    <div class="create-panel">
      <div class="form-row">
        <input
          v-model="newKeyword"
          placeholder="输入搜索关键词，如：小红书无货源玩法"
          class="keyword-input"
          @keyup.enter="handleSearch"
        />
        <button @click="handleSearch" :disabled="!newKeyword.trim() || searching" class="btn btn-green">
          {{ searching ? '扫描中...' : '🔍 启动雷达' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>

    <div v-else-if="tasks.length === 0" class="empty-state">
      <p>暂无雷达任务，输入关键词开始扫描</p>
    </div>

    <div v-else class="task-cards">
      <div v-for="task in tasks" :key="task.id" class="task-card" @click="$router.push(`/radar/${task.id}`)">
        <div class="task-card-header">
          <span class="task-id">{{ task.id.slice(0, 8) }}...</span>
          <span :class="['status-badge', `status-${task.status}`]">
            {{ statusLabel(task.status) }}
          </span>
        </div>
        <div class="task-keyword">
          🔍 {{ task.keyword }}
        </div>
        <div v-if="task.error" class="task-error">{{ task.error }}</div>
        <div v-if="task.results && task.results.length > 0" class="results-count">
          📋 {{ task.results.length }} 条结果
        </div>
        <div class="task-meta">
          <span class="task-time">{{ formatTime(task.created_at) }}</span>
          <span class="click-hint">点击查看详情 →</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { listRadarTasks, createRadarTask } from '../api'

const newKeyword = ref('')
const searching = ref(false)
const loading = ref(true)
const tasks = ref([])
let pollTimer = null

const statusLabel = (status) => {
  const map = { pending: '等待中', processing: '扫描中', completed: '已完成', failed: '失败' }
  return map[status] || status
}

const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

const handleSearch = async () => {
  if (!newKeyword.value.trim() || searching.value) return
  searching.value = true
  try {
    const task = await createRadarTask(newKeyword.value.trim())
    tasks.value.unshift(task)
    newKeyword.value = ''
  } catch (e) {
    alert('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    searching.value = false
  }
}

const fetchTasks = async () => {
  try {
    tasks.value = await listRadarTasks()
  } catch (e) {
    console.error('Failed to fetch radar tasks:', e)
  } finally {
    loading.value = false
  }
}

const hasPending = () => tasks.value.some(t => t.status === 'pending')

onMounted(() => {
  fetchTasks()
  pollTimer = setInterval(() => {
    if (hasPending()) fetchTasks()
  }, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; font-weight: 600; }
.subtitle { color: #999; font-size: 14px; margin-top: 4px; }

.create-panel {
  background: white; border-radius: 12px; padding: 24px;
  margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.form-row { display: flex; gap: 12px; align-items: center; }

.keyword-input {
  flex: 1; padding: 10px 16px; border: 1px solid #d9d9d9; border-radius: 8px;
  font-size: 14px; outline: none; transition: border-color 0.2s;
}
.keyword-input:focus { border-color: #52c41a; }

.btn {
  padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px;
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.btn-green { background: #52c41a; color: white; }
.btn-green:hover:not(:disabled) { background: #73d13d; }
.btn-green:disabled { opacity: 0.5; cursor: not-allowed; }

.loading-state, .empty-state {
  text-align: center; padding: 64px 0; color: #999; font-size: 15px;
}

.task-cards {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 16px;
}

.task-card {
  background: white; border-radius: 12px; padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: all 0.2s; cursor: pointer;
}
.task-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); transform: translateY(-1px); }

.task-card-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
}
.task-id { font-family: monospace; font-size: 13px; color: #666; }

.status-badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.status-pending { background: #fff7e6; color: #d48806; }
.status-processing { background: #e6f7ff; color: #0958d9; }
.status-completed { background: #f6ffed; color: #389e0d; }
.status-failed { background: #fff1f0; color: #cf1322; }

.task-keyword { font-size: 15px; font-weight: 500; margin-bottom: 8px; }
.task-error { color: #cf1322; font-size: 13px; margin-bottom: 8px; word-break: break-all; }
.results-count { font-size: 13px; color: #52c41a; margin-bottom: 8px; }

.task-meta {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px; color: #999; margin-top: 8px; padding-top: 8px; border-top: 1px solid #f0f0f0;
}
.click-hint { color: #52c41a; font-size: 12px; }
</style>
