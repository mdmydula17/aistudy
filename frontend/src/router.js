import { createRouter, createWebHistory } from 'vue-router'
import RadarList from './views/RadarList.vue'
import SynthList from './views/SynthList.vue'
import ReportView from './views/ReportView.vue'

const routes = [
  { path: '/', name: 'RadarList', component: RadarList },
  { path: '/synth', name: 'SynthList', component: SynthList },
  { path: '/synth/:id/report', name: 'ReportView', component: ReportView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
