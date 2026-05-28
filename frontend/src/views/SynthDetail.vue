<template>
  <div class="synth-detail" v-if="task">
    <div class="breadcrumb">
      <router-link to="/synth">🟣 炼丹炉</router-link>
      <span>/</span>
      <span>任务详情</span>
    </div>

    <div class="detail-header">
      <div class="detail-title-row">
        <h2>🟣 {{ task.keyword }}</h2>
        <span :class="['status-badge', `status-${task.status}`]">
          {{ statusLabel(task.status) }}
        </span>
      </div>
      <div class="detail-meta">
        <span>ID: {{ task.id }}</span>
        <span>创建: {{ formatTime(task.created_at) }}</span>
      </div>
      <div v-if="task.error" class="detail-error">❌ {{ task.error }}</div>
    </div>

    <div v-if="task.status === 'pending'" class="upload-section">
      <h3>📎 上传资料</h3>
      <p class="upload-hint">请上传 TXT / PDF / DOCX 格式的参考资料，上传完成后点击"开始炼丹"</p>
      <div class="upload-area">
        <label class="upload-label">
          📁 选择文件
          <input type="file" multiple accept=".txt,.pdf,.docx" @change="handleUpload" class="file-input" />
        </label>
        <div v-if="uploadedFiles.length > 0" class="uploaded-list">
          <div v-for="f in uploadedFiles" :key="f" class="uploaded-item">✅ {{ f }}</div>
        </div>
      </div>
      <div class="action-bar">
        <button @click="startSynth" :disabled="uploadedFiles.length === 0" class="btn btn-purple">
          🟣 开始炼丹
        </button>
      </div>
    </div>

    <div v-else-if="task.status === 'processing'" class="processing-section">
      <div class="spinner"></div>
      <p>🟣 炼丹进行中，AI 正在融合知识...</p>
    </div>

    <div v-else-if="task.status === 'completed'" class="completed-section">
      <p>✅ 研报已生成！</p>
      <button @click="$router.push(`/synth/${task.id}/report`)" class="btn btn-green">
        📄 查看研报
      </button>
    </div>

    <div v-else-if="task.status === 'failed'" class="failed-section">
      <p>❌ 炼丹失败：{{ task.error }}</p>
      <button @click="$router.push('/synth')" class="btn btn-outline">返回</button>
    </div>
  </div>

  <div v-else class="loading">加载中...</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSynthTask, uploadFiles, runSynthTask } from '../api'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id
const task = ref(null)
const uploadedFiles = ref([])
let pollTimer = null

const statusLabel = (status) => {
  const map = { pending: '等待上传', processing: '炼丹中', completed: '已完成', failed: '失败' }
  return map[status] || status
}

const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

const fetchTask = async () => {
  try {
    task.value = await getSynthTask(taskId)
  } catch (e) {
    console.error('Failed to fetch task:', e)
  }
}

const handleUpload = async (event) => {
  const files = event.target.files
  if (!files || files.length === 0) return

  try {
    const result = await uploadFiles(taskId, files)
    uploadedFiles.value = result.saved
  } catch (e) {
    alert('上传失败: ' + (e.response?.data?.detail || e.message))
  }
}

const startSynth = async () => {
  try {
    await runSynthTask(taskId)
    task.value = await getSynthTask(taskId)
    pollTimer = setInterval(async () => {
      task.value = await getSynthTask(taskId)
      if (task.value.status !== 'processing') {
        if (pollTimer) clearInterval(pollTimer)
      }
    }, 5000)
  } catch (e) {
    alert('启动失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(fetchTask)

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.breadcrumb { font-size: 14px; color: #999; margin-bottom: 20px; }
.breadcrumb a { color: #722ed1; text-decoration: none; }
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
.status-pending { background: #f9f0ff; color: #722ed1; }
.status-processing { background: #e6f7ff; color: #0958d9; }
.status-completed { background: #f6ffed; color: #389e0d; }
.status-failed { background: #fff1f0; color: #cf1322; }

.upload-section {
  background: white; border-radius: 12px; padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.upload-section h3 { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.upload-hint { font-size: 14px; color: #999; margin-bottom: 16px; }

.upload-area { margin-bottom: 20px; }
.upload-label {
  display: inline-block; padding: 12px 24px; background: #f9f0ff; color: #722ed1;
  border-radius: 8px; cursor: pointer; font-size: 14px; transition: all 0.2s;
}
.upload-label:hover { background: #efdbff; }
.file-input { display: none; }

.uploaded-list { margin-top: 12px; }
.uploaded-item { padding: 6px 0; font-size: 14px; color: #52c41a; }

.action-bar { margin-top: 16px; padding-top: 16px; border-top: 1px solid #f0f0f0; text-align: center; }

.btn {
  padding: 12px 28px; border: none; border-radius: 8px; font-size: 15px;
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.btn-purple { background: #722ed1; color: white; }
.btn-purple:hover:not(:disabled) { background: #9254de; }
.btn-purple:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-green { background: #52c41a; color: white; }
.btn-green:hover { background: #73d13d; }
.btn-outline { background: white; color: #722ed1; border: 1px solid #722ed1; }
.btn-outline:hover { background: #f9f0ff; }

.processing-section {
  text-align: center; padding: 64px; background: white; border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); color: #722ed1; font-size: 16px;
}
.spinner {
  width: 40px; height: 40px; border: 4px solid #f0f0f0; border-top: 4px solid #722ed1;
  border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

.completed-section {
  text-align: center; padding: 64px; background: white; border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); color: #389e0d; font-size: 16px;
}
.completed-section p { margin-bottom: 16px; }

.failed-section {
  text-align: center; padding: 64px; background: white; border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); color: #cf1322; font-size: 16px;
}
.failed-section p { margin-bottom: 16px; }

.loading { text-align: center; padding: 64px 0; color: #999; font-size: 16px; }
</style>
