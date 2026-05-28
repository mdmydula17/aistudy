import { createRouter, createWebHistory } from 'vue-router'
import RadarList from './views/RadarList.vue'
import RadarDetail from './views/RadarDetail.vue'
import SynthList from './views/SynthList.vue'
import SynthDetail from './views/SynthDetail.vue'
import ReportView from './views/ReportView.vue'

const routes = [
  { path: '/', name: 'RadarList', component: RadarList },
  { path: '/radar/:id', name: 'RadarDetail', component: RadarDetail },
  { path: '/synth', name: 'SynthList', component: SynthList },
  { path: '/synth/:id', name: 'SynthDetail', component: SynthDetail },
  { path: '/synth/:id/report', name: 'ReportView', component: ReportView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
