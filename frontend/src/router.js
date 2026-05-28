import { createRouter, createWebHistory } from 'vue-router'
import TaskList from './views/TaskList.vue'
import TaskDetail from './views/TaskDetail.vue'
import ReportView from './views/ReportView.vue'

const routes = [
  { path: '/', name: 'TaskList', component: TaskList },
  { path: '/tasks/:id', name: 'TaskDetail', component: TaskDetail },
  { path: '/tasks/:id/report', name: 'ReportView', component: ReportView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
