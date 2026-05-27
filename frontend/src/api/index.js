import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

export async function createTask(url) {
  const res = await api.post('/tasks/', { url })
  return res.data
}

export async function getTask(taskId) {
  const res = await api.get(`/tasks/${taskId}`)
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
