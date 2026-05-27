import { createRouter, createWebHistory } from 'vue-router'
import TaskList from './views/TaskList.vue'
import TaskDetail from './views/TaskDetail.vue'
import AssetDetail from './views/AssetDetail.vue'

const routes = [
  { path: '/', name: 'TaskList', component: TaskList },
  { path: '/tasks/:id', name: 'TaskDetail', component: TaskDetail },
  { path: '/assets/:id', name: 'AssetDetail', component: AssetDetail },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
