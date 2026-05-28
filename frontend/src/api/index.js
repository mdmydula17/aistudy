import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

export async function listTasks(limit = 50, offset = 0) {
  const res = await api.get('/tasks/', { params: { limit, offset } })
  return res.data
}

export async function createTask(keyword, urls = null, contents = null) {
  const payload = {}
  if (keyword) {
    payload.keyword = keyword
  }
  if (urls && urls.length > 0) {
    payload.urls = urls
  }
  if (contents && contents.length > 0) {
    payload.contents = contents
  }
  const res = await api.post('/tasks/', payload)
  return res.data
}

export async function getTask(taskId) {
  const res = await api.get(`/tasks/${taskId}`)
  return res.data
}

export async function getReport(taskId) {
  const res = await api.get(`/tasks/${taskId}/report`)
  return res.data
}

export async function approveTask(taskId) {
  const res = await api.patch(`/tasks/${taskId}/approve`)
  return res.data
}

export async function rejectTask(taskId) {
  const res = await api.patch(`/tasks/${taskId}/reject`)
  return res.data
}

export async function getAssetsByTask(taskId) {
  const res = await api.get(`/assets/task/${taskId}`)
  return res.data
}

export async function getAsset(assetId) {
  const res = await api.get(`/assets/${assetId}`)
  return res.data
}
