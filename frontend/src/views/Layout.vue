<template>
  <el-container class="layout-shell">
    <el-aside class="sidebar" width="248px">
      <div class="brand">
        <div class="brand-mark"><el-icon><Cpu /></el-icon></div>
        <div><strong>简普数智资产管理后台</strong><span>Asset Management Console</span></div>
      </div>
      <div class="workspace-label">工作台</div>
      <el-menu class="nav-menu" :default-active="route.path" router>
        <template v-for="group in visibleGroups" :key="group.key">
          <el-sub-menu v-if="group.children" :index="group.key">
            <template #title><el-icon><component :is="group.icon" /></el-icon><span>{{ group.title }}</span></template>
            <el-menu-item v-for="item in group.children" :key="item.path" :index="item.path">
              <span>{{ item.title }}</span><small v-if="item.hint">{{ item.hint }}</small>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="group.path">
            <el-icon><component :is="group.icon" /></el-icon><span>{{ group.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
      <div class="sidebar-footer">资产运营中心 · {{ currentDate }}</div>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div><div class="eyebrow">资产管理平台</div><h1>{{ currentTitle }}</h1></div>
        <div class="topbar-actions"><span class="status-dot"></span><span class="status-text">服务正常</span><el-divider direction="vertical" /><el-dropdown @command="handleCommand">
          <span class="user-info"><el-avatar :size="30">{{ (user?.name || '用').slice(0, 1) }}</el-avatar>{{ user?.name || '用户' }}<el-icon><ArrowDown /></el-icon></span>
          <template #dropdown><el-dropdown-menu><el-dropdown-item command="logout">退出登录</el-dropdown-item></el-dropdown-menu></template>
        </el-dropdown></div>
      </el-header>
      <el-main class="main-content"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Cpu, ArrowDown, DataAnalysis, CircleCheck, RefreshRight, Files, Delete, Search, Setting } from '@element-plus/icons-vue'
import { useUserStore } from '@/store'

const route = useRoute(); const router = useRouter(); const store = useUserStore()
const user = computed(() => store.user)
const currentDate = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric' }).format(new Date())
const groups = [
  { key: 'dashboard', title: '领导驾驶舱', icon: DataAnalysis, children: [{ path: '/dashboard', title: '经营总览', hint: 'KPI' }, { path: '/dashboard/report', title: '报告中心', hint: '导出' }] },
  { key: 'idle', title: '闲置盘活', icon: RefreshRight, path: '/idle' },
  { key: 'transfer', title: '资产调拨', icon: RefreshRight, path: '/transfer' },
  { key: 'lifecycle', title: '全生命周期档案', icon: Files, children: [{ path: '/lifecycle', title: '资产检索', hint: '身份证' }, { path: '/lifecycle/quality', title: '数据质量' }] },
  { key: 'check', title: '智能盘点', icon: CircleCheck, path: '/check' },
  { key: 'query', title: '智能查询', icon: Search, children: [{ path: '/query', title: '自然语言问答', hint: 'AI' }, { path: '/query/filter', title: '条件筛选' }] },
  { key: 'insight', title: '采购决策分析', icon: DataAnalysis, children: [{ path: '/insight/brands', title: '品牌表现' }, { path: '/procurement/forecast', title: '采购预测' }, { path: '/procurement', title: '采购建议' }] },
  { key: 'scrap', title: '报废决策', icon: Delete, path: '/scrap' },
  { key: 'system', title: '系统管理', icon: Setting, path: '/system', admin: true },
]
const visibleGroups = computed(() => groups.filter(g => !g.admin || user.value?.is_admin == 1))
const currentTitle = computed(() => route.meta?.title || '工作台')
const handleCommand = cmd => { if (cmd === 'logout') { store.logout(); router.push('/login') } }
</script>

<style scoped>
.layout-shell { min-height: 100vh; background: #f4f7fb; }
.sidebar { display:flex; flex-direction:column; background:#fff; color:#40536d; border-right:1px solid #dfe7f0; box-shadow:4px 0 18px rgba(32,51,77,.04); }
.brand { display:flex; gap:12px; align-items:center; padding:24px 22px; border-bottom:1px solid #1d385d; }
.brand { border-bottom-color:#e7eef6; }.brand-mark { width:36px; height:36px; display:grid; place-items:center; color:#1769aa; background:#eaf4fc; border-radius:10px; font-size:20px; }.brand strong { display:block; font-size:17px; color:#20334d; letter-spacing:.5px; }.brand span { display:block; margin-top:3px; color:#8191a7; font-size:10px; }
.workspace-label { padding:22px 22px 8px; color:#9aa9bb; font-size:11px; text-transform:uppercase; letter-spacing:1.5px; }.nav-menu { border:0; background:transparent; padding:0 10px; }.nav-menu :deep(.el-sub-menu__title), .nav-menu :deep(.el-menu-item) { height:46px; color:#53657d; border-radius:8px; margin:3px 0; }.nav-menu :deep(.el-menu-item small) { margin-left:auto; color:#9aa9bb; font-size:10px; }.nav-menu :deep(.el-sub-menu__title:hover), .nav-menu :deep(.el-menu-item:hover) { background:#f0f7fd; color:#1769aa; }.nav-menu :deep(.el-menu-item.is-active) { background:#e7f2fb; color:#1769aa; font-weight:600; }.nav-menu :deep(.el-menu) { background:transparent; }.nav-menu :deep(.el-sub-menu .el-menu-item) { padding-left:52px!important; min-width:0; }
.sidebar-footer { margin-top:auto; padding:18px 22px; color:#9aa9bb; font-size:11px; border-top:1px solid #e7eef6; }
.topbar { height:76px; display:flex; align-items:center; justify-content:space-between; padding:0 30px; background:#fff; border-bottom:1px solid #e6edf5; }.eyebrow { color:#8191a7; font-size:11px; }.topbar h1 { margin:3px 0 0; color:#20334d; font-size:21px; }.topbar-actions { display:flex; align-items:center; gap:8px; color:#53657d; font-size:13px; }.status-dot { width:7px; height:7px; border-radius:50%; background:#20b486; }.status-text { color:#198f6b; }.user-info { display:flex; align-items:center; gap:8px; cursor:pointer; }.main-content { padding:28px 30px; overflow:auto; }
</style>
