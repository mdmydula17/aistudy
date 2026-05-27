<template>
  <div class="task-detail" v-if="task">
    <div class="breadcrumb">
      <router-link to="/">任务列表</router-link>
      <span>/</span>
      <span>任务详情</span>
    </div>

    <div class="detail-header">
      <div>
        <h2>任务 {{ task.id.slice(0, 8) }}...</h2>
        <span :class="['status-badge', `status-${task.status}`]">
          {{ statusLabel(task.status) }}
        </span>
      </div>
      <div v-if="task.needs_human_review" class="review-actions">
        <button @click="handleApprove" class="btn btn-success">通过</button>
        <button @click="handleReject" class="btn btn-danger">拒绝</button>
      </div>
    </div>

    <div class="detail-card">
      <div class="detail-row">
        <label>URL</label>
        <a :href="task.url" target="_blank" class="url-link">{{ task.url }}</a>
      </div>
      <div class="detail-row">
        <label>状态</label>
        <span>{{ task.status }}</span>
      </div>
      <div class="detail-row">
        <label>需人工审核</label>
        <span>{{ task.needs_human_review ? '是' : '否' }}</span>
      </div>
      <div class="detail-row" v-if="task.error">
        <label>错误信息</label>
        <span class="error-text">{{ task.error }}</span>
      </div>
      <div class="detail-row">
        <label>创建时间</label>
        <span>{{ formatTime(task.created_at) }}</span>
      </div>
    </div>

    <div class="assets-section">
      <h3>提取资产</h3>
      <div v-if="assets.length === 0" class="empty-hint">暂无资产数据</div>
      <div v-else class="asset-cards">
        <div
          v-for="asset in assets"
          :key="asset.id"
          class="asset-card"
          @click="$router.push(`/assets/${asset.id}`)"
        >
          <h4>{{ asset.title }}</h4>
          <div class="asset-score">
            置信度:
            <span :class="scoreClass(asset.confidence_score)">
              {{ (asset.confidence_score * 100).toFixed(0) }}%
            </span>
          </div>
          <div class="asset-time">{{ formatTime(asset.created_at) }}</div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="loading">加载中...</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getTask, getAssetsByTask, approveTask, rejectTask } from '../api'

const route = useRoute()
const task = ref(null)
const assets = ref([])

const statusLabel = (status) => {
  const map = {
    pending: '等待中', processing: '处理中', completed: '已完成',
    needs_review: '需审核', rejected: '已拒绝', failed: '失败',
  }
  return map[status] || status
}

const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

const scoreClass = (score) => {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.6) return 'score-mid'
  return 'score-low'
}

const handleApprove = async () => {
  try {
    task.value = await approveTask(task.value.id)
  } catch (e) {
    alert('操作失败')
  }
}

const handleReject = async () => {
  try {
    task.value = await rejectTask(task.value.id)
  } catch (e) {
    alert('操作失败')
  }
}

onMounted(async () => {
  const id = route.params.id
  try {
    task.value = await getTask(id)
    assets.value = await getAssetsByTask(id)
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
  font-size: 20px;
  margin-bottom: 8px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.status-pending { background: #fff7e6; color: #d48806; }
.status-processing { background: #e6f7ff; color: #0958d9; }
.status-completed { background: #f6ffed; color: #389e0d; }
.status-needs_review { background: #fff1f0; color: #cf1322; }
.status-rejected { background: #f5f5f5; color: #999; }
.status-failed { background: #fff1f0; color: #cf1322; }

.review-actions {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 8px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-success {
  background: #52c41a;
  color: white;
}

.btn-success:hover { background: #73d13d; }

.btn-danger {
  background: #ff4d4f;
  color: white;
}

.btn-danger:hover { background: #ff7875; }

.detail-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.detail-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child { border-bottom: none; }

.detail-row label {
  width: 120px;
  color: #999;
  font-size: 14px;
  flex-shrink: 0;
}

.url-link {
  color: #1677ff;
  word-break: break-all;
}

.error-text {
  color: #ff4d4f;
}

.assets-section h3 {
  font-size: 18px;
  margin-bottom: 16px;
}

.empty-hint {
  color: #999;
  text-align: center;
  padding: 32px 0;
}

.asset-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.asset-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.asset-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.asset-card h4 {
  font-size: 16px;
  margin-bottom: 12px;
}

.asset-score {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.score-high { color: #52c41a; font-weight: 600; }
.score-mid { color: #faad14; font-weight: 600; }
.score-low { color: #ff4d4f; font-weight: 600; }

.asset-time {
  font-size: 12px;
  color: #999;
}

.loading {
  text-align: center;
  padding: 64px 0;
  color: #999;
}
</style>
