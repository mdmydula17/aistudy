<template>
  <div class="task-list">
    <div class="page-header">
      <h2>任务列表</h2>
      <div class="create-form">
        <input
          v-model="newUrl"
          placeholder="输入小红书笔记 URL"
          class="url-input"
          @keyup.enter="handleCreate"
        />
        <button @click="handleCreate" :disabled="!newUrl || creating" class="btn btn-primary">
          {{ creating ? '创建中...' : '创建任务' }}
        </button>
      </div>
    </div>

    <div v-if="tasks.length === 0" class="empty-state">
      <p>暂无任务，请输入小红书 URL 创建新任务</p>
    </div>

    <div v-else class="task-cards">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        @click="$router.push(`/tasks/${task.id}`)"
      >
        <div class="task-card-header">
          <span class="task-id">{{ task.id.slice(0, 8) }}...</span>
          <span :class="['status-badge', `status-${task.status}`]">
            {{ statusLabel(task.status) }}
          </span>
        </div>
        <div class="task-url">{{ task.url }}</div>
        <div class="task-meta">
          <span v-if="task.needs_human_review" class="review-flag">需人工审核</span>
          <span class="task-time">{{ formatTime(task.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { createTask, getTask } from '../api'

const newUrl = ref('')
const creating = ref(false)
const tasks = ref([])

const statusLabel = (status) => {
  const map = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    needs_review: '需审核',
    rejected: '已拒绝',
    failed: '失败',
  }
  return map[status] || status
}

const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

const handleCreate = async () => {
  if (!newUrl.value || creating.value) return
  creating.value = true
  try {
    const task = await createTask(newUrl.value)
    tasks.value.unshift(task)
    newUrl.value = ''
  } catch (e) {
    alert('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

onMounted(() => {
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 22px;
  font-weight: 600;
}

.create-form {
  display: flex;
  gap: 12px;
}

.url-input {
  width: 360px;
  padding: 10px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.url-input:focus {
  border-color: #4096ff;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #1677ff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #4096ff;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 64px 0;
  color: #999;
  font-size: 15px;
}

.task-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.task-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.task-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.task-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-id {
  font-family: monospace;
  font-size: 13px;
  color: #666;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-pending { background: #fff7e6; color: #d48806; }
.status-processing { background: #e6f7ff; color: #0958d9; }
.status-completed { background: #f6ffed; color: #389e0d; }
.status-needs_review { background: #fff1f0; color: #cf1322; }
.status-rejected { background: #f5f5f5; color: #999; }
.status-failed { background: #fff1f0; color: #cf1322; }

.task-url {
  font-size: 13px;
  color: #555;
  word-break: break-all;
  margin-bottom: 12px;
  line-height: 1.5;
}

.task-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.review-flag {
  background: #ff4d4f;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}
</style>
