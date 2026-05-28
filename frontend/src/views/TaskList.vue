<template>
  <div class="task-list">
    <div class="page-header">
      <h2>任务列表</h2>
    </div>

    <div class="create-panel">
      <div class="form-row">
        <input
          v-model="newKeyword"
          placeholder="输入搜索关键词，如：小红书无货源玩法"
          class="keyword-input"
          @keyup.enter="handleCreate"
        />
        <button @click="handleCreate" :disabled="(!newKeyword && !manualUrls.trim() && !manualContents.trim()) || creating" class="btn btn-primary">
          {{ creating ? '创建中...' : '创建任务' }}
        </button>
      </div>
      <div class="form-row">
        <textarea
          v-model="manualUrls"
          placeholder="手动输入小红书笔记 URL（可选，每行一个）"
          class="urls-input"
          rows="2"
        ></textarea>
      </div>
      <div class="form-row">
        <textarea
          v-model="manualContents"
          placeholder="直接粘贴笔记文本内容（可选，每段用空行分隔，将自动拆分为多条）— 最可靠的方式"
          class="contents-input"
          rows="4"
        ></textarea>
      </div>
      <div class="form-row cookie-row">
        <input
          v-model="xhsCookie"
          placeholder="小红书 Cookie（可选，登录后搜索更精准）— 在浏览器登录小红书 → F12 → Network → 任意请求 → 复制 Cookie 值"
          class="cookie-input"
        />
        <button @click="saveCookie" class="btn btn-outline" :disabled="!xhsCookie">
          保存
        </button>
        <span v-if="cookieSaved" class="cookie-saved">✓ 已保存</span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>

    <div v-else-if="tasks.length === 0" class="empty-state">
      <p>暂无任务，请输入关键词创建新任务</p>
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
        <div class="task-keyword">
          <span class="keyword-icon">🔍</span>
          {{ task.keyword || '(手动URL任务)' }}
        </div>
        <div class="task-meta">
          <span v-if="task.needs_human_review" class="review-flag">需人工审核</span>
          <span v-if="task.error" class="error-flag">有错误</span>
          <span class="task-time">{{ formatTime(task.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listTasks, createTask } from '../api'

const newKeyword = ref('')
const manualUrls = ref('')
const manualContents = ref('')
const xhsCookie = ref('')
const cookieSaved = ref(false)
const creating = ref(false)
const loading = ref(true)
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

const saveCookie = async () => {
  if (!xhsCookie.value) return
  try {
    await fetch('/api/v1/settings/cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: xhsCookie.value }),
    })
    cookieSaved.value = true
    setTimeout(() => { cookieSaved.value = false }, 3000)
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const handleCreate = async () => {
  if ((!newKeyword.value && !manualUrls.value.trim() && !manualContents.value.trim()) || creating.value) return
  creating.value = true
  try {
    const urls = manualUrls.value
      ? manualUrls.value.split('\n').map(u => u.trim()).filter(u => u.length > 0)
      : null
    const contents = manualContents.value.trim()
      ? manualContents.value.split(/\n\s*\n/).map(c => c.trim()).filter(c => c.length > 0)
      : null
    const keyword = newKeyword.value.trim() || null
    const task = await createTask(keyword, urls, contents)
    tasks.value.unshift(task)
    newKeyword.value = ''
    manualUrls.value = ''
    manualContents.value = ''
  } catch (e) {
    alert('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

const fetchTasks = async () => {
  loading.value = true
  try {
    tasks.value = await listTasks()
  } catch (e) {
    console.error('Failed to fetch tasks:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchTasks)
</script>

<style scoped>
.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 22px;
  font-weight: 600;
}

.create-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.form-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
}

.form-row:last-child {
  margin-bottom: 0;
}

.keyword-input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.keyword-input:focus {
  border-color: #4096ff;
}

.urls-input {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  resize: vertical;
  font-family: inherit;
}

.urls-input:focus {
  border-color: #4096ff;
}

.contents-input {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  resize: vertical;
  font-family: inherit;
  background: #fafafa;
}

.contents-input:focus {
  border-color: #4096ff;
  background: white;
}

.cookie-row {
  padding-top: 8px;
  border-top: 1px dashed #e8e8e8;
}

.cookie-input {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}

.cookie-input:focus {
  border-color: #4096ff;
}

.cookie-saved {
  color: #52c41a;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
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

.btn-outline {
  background: white;
  color: #1677ff;
  border: 1px solid #1677ff;
  padding: 8px 16px;
  font-size: 13px;
}

.btn-outline:hover:not(:disabled) {
  background: #f0f5ff;
}

.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state {
  text-align: center;
  padding: 64px 0;
  color: #999;
  font-size: 15px;
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

.task-keyword {
  font-size: 15px;
  color: #333;
  font-weight: 500;
  margin-bottom: 12px;
  line-height: 1.5;
}

.keyword-icon {
  margin-right: 4px;
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

.error-flag {
  background: #faad14;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}
</style>
