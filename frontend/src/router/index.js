import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/Index.vue'), meta: { title: '领导驾驶舱', icon: 'DataAnalysis' } },
      { path: 'check', name: 'Check', component: () => import('@/views/check/Index.vue'), meta: { title: '智能盘点', icon: 'CircleCheck' } },
      { path: 'idle', name: 'Idle', component: () => import('@/views/idle/Index.vue'), meta: { title: '闲置盘活', icon: 'RefreshRight' } },
      { path: 'lifecycle', name: 'Lifecycle', component: () => import('@/views/lifecycle/Index.vue'), meta: { title: '资产档案', icon: 'Files' } },
      { path: 'scrap', name: 'Scrap', component: () => import('@/views/scrap/Index.vue'), meta: { title: '报废决策', icon: 'Delete' } },
      { path: 'query', name: 'Query', component: () => import('@/views/query/Index.vue'), meta: { title: '智能查询', icon: 'Search' } },
      { path: 'system', name: 'System', component: () => import('@/views/system/Index.vue'), meta: { title: '系统管理', icon: 'Setting', admin: true } },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
