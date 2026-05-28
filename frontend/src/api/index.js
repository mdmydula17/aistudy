import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

export async function listRadarTasks(limit = 50, offset = 0) {
  const res = await api.get('/radar/', { params: { limit, offset } })
  return res.data
}

export async function createRadarTask(keyword) {
  const res = await api.post('/radar/', { keyword })
  return res.data
}

export async function getRadarTask(taskId) {
  const res = await api.get(`/radar/${taskId}`)
  return res.data
}

export async function listSynthTasks(limit = 50, offset = 0) {
  const res = await api.get('/synth/', { params: { limit, offset } })
  return res.data
}

export async function createSynthTask(keyword, radarTaskId = null) {
  const payload = { keyword }
  if (radarTaskId) {
    payload.radar_task_id = radarTaskId
  }
  const res = await api.post('/synth/', payload)
  return res.data
}

export async function getSynthTask(taskId) {
  const res = await api.get(`/synth/${taskId}`)
  return res.data
}

export async function getSynthReport(taskId) {
  const res = await api.get(`/synth/${taskId}/report`)
  return res.data
}

export async function uploadFiles(taskId, files) {
  const formData = new FormData()
  for (const f of files) {
    formData.append('files', f)
  }
  const res = await api.post(`/synth/${taskId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
