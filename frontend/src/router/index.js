import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'transfer', name: 'Transfer', component: () => import('@/views/transfer/Index.vue'), meta: { title: '资产调拨', icon: 'Switch' } },
      { path: 'insight/brands', name: 'BrandInsight', component: () => import('@/views/insight/Brand.vue'), meta: { title: '品牌表现', icon: 'DataAnalysis' } },
      { path: 'procurement', name: 'Procurement', component: () => import('@/views/procurement/Index.vue'), meta: { title: '采购建议', icon: 'Tickets' } },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/Index.vue'), meta: { title: '经营总览' } },
      { path: 'dashboard/report', name: 'DashboardReport', component: () => import('@/views/dashboard/Index.vue'), meta: { title: '报告中心', view: 'report' } },
      { path: 'check', name: 'Check', component: () => import('@/views/check/Index.vue'), meta: { title: '智能盘点', icon: 'CircleCheck' } },
      { path: 'idle', name: 'Idle', component: () => import('@/views/idle/Index.vue'), meta: { title: '闲置盘活', icon: 'RefreshRight' } },
      { path: 'lifecycle', name: 'Lifecycle', component: () => import('@/views/lifecycle/Index.vue'), meta: { title: '资产检索与身份证' } },
      { path: 'lifecycle/quality', name: 'LifecycleQuality', component: () => import('@/views/lifecycle/Index.vue'), meta: { title: '数据质量', view: 'quality' } },
      { path: 'scrap', name: 'Scrap', component: () => import('@/views/scrap/Index.vue'), meta: { title: '报废决策', icon: 'Delete' } },
      { path: 'query', name: 'Query', component: () => import('@/views/query/Index.vue'), meta: { title: '自然语言问答', view: 'nl' } },
      { path: 'query/filter', name: 'QueryFilter', component: () => import('@/views/query/Index.vue'), meta: { title: '资产条件筛选', view: 'filter' } },
      { path: 'query/forecast', name: 'QueryForecast', component: () => import('@/views/query/Index.vue'), meta: { title: '采购预测', view: 'forecast' } },
      { path: 'procurement/forecast', name: 'ProcurementForecast', component: () => import('@/views/query/Index.vue'), meta: { title: '采购预测', view: 'forecast' } },
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
  } else if (to.meta.admin) {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (user?.is_admin != 1) {
      next('/dashboard')
      return
    }
    next()
  } else {
    next()
  }
})

export default router
