import { createRouter, createWebHistory } from 'vue-router'
import LibraryPage from './pages/LibraryPage.vue'
import EmulatorsPage from './pages/EmulatorsPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'library', component: LibraryPage },
    { path: '/emulators', name: 'emulators', component: EmulatorsPage },
  ],
})
