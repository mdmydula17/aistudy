<template>
  <div class="report-view" v-if="report">
    <div class="breadcrumb">
      <router-link to="/">任务列表</router-link>
      <span>/</span>
      <router-link :to="`/tasks/${taskId}`">任务详情</router-link>
      <span>/</span>
      <span>研报</span>
    </div>

    <div class="report-header">
      <h1>{{ report.title }}</h1>
      <div class="report-meta">
        <span class="report-time">{{ formatTime(report.created_at) }}</span>
        <button v-if="report.pdf_path" @click="downloadPdf" class="btn btn-outline">
          下载 PDF
        </button>
      </div>
    </div>

    <div class="report-body">
      <div class="markdown-content" v-html="renderMarkdown(report.markdown_content)"></div>
    </div>
  </div>

  <div v-else class="loading">加载研报中...</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getReport } from '../api'

const route = useRoute()
const taskId = route.params.id
const report = ref(null)

const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

const downloadPdf = () => {
  if (report.value?.pdf_path) {
    window.open(`/api/v1/files/${report.value.pdf_path}`, '_blank')
  }
}

const renderMarkdown = (text) => {
  if (!text) return ''
  let html = text
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
  html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
  html = html.replace(/<\/li>\n<li>/g, '</li><li>')
  html = html.replace(/\n{2,}/g, '</p><p>')
  html = html.replace(/\n/g, '<br/>')
  html = `<p>${html}</p>`
  html = html.replace(/<p><\/p>/g, '')
  html = html.replace(/<p>(<h[1-3]>)/g, '$1')
  html = html.replace(/(<\/h[1-3]>)<\/p>/g, '$1')
  html = html.replace(/<p>(<blockquote>)/g, '$1')
  html = html.replace(/(<\/blockquote>)<\/p>/g, '$1')
  html = html.replace(/<p>(<ul>)/g, '$1')
  html = html.replace(/(<\/ul>)<\/p>/g, '$1')
  return html
}

onMounted(async () => {
  try {
    report.value = await getReport(taskId)
  } catch (e) {
    alert('研报加载失败: ' + (e.response?.data?.detail || e.message))
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

.report-header {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 2px solid #f0f0f0;
}

.report-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
  color: #1a1a2e;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.report-time {
  font-size: 14px;
  color: #999;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline {
  background: white;
  color: #1677ff;
  border: 1px solid #1677ff;
}

.btn-outline:hover { background: #f0f5ff; }

.report-body {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  max-width: 900px;
}

.markdown-content {
  font-size: 16px;
  line-height: 1.9;
  color: #333;
}

.markdown-content :deep(h1) {
  font-size: 24px;
  font-weight: 700;
  margin: 32px 0 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e8e8e8;
  color: #1a1a2e;
}

.markdown-content :deep(h2) {
  font-size: 20px;
  font-weight: 600;
  margin: 28px 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
  color: #16213e;
}

.markdown-content :deep(h3) {
  font-size: 18px;
  font-weight: 600;
  margin: 24px 0 12px;
  color: #333;
}

.markdown-content :deep(blockquote) {
  margin: 16px 0;
  padding: 12px 20px;
  border-left: 4px solid #1677ff;
  background: #f0f5ff;
  border-radius: 0 8px 8px 0;
  color: #555;
}

.markdown-content :deep(ul) {
  padding-left: 24px;
  margin: 12px 0;
}

.markdown-content :deep(li) {
  margin: 8px 0;
  line-height: 1.8;
}

.markdown-content :deep(strong) {
  font-weight: 600;
  color: #1a1a2e;
}

.markdown-content :deep(p) {
  margin: 12px 0;
}

.loading {
  text-align: center;
  padding: 64px 0;
  color: #999;
  font-size: 16px;
}
</style>
