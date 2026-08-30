<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="24" color="#1890ff"><Cpu /></el-icon>
        <span>AI数智资产</span>
      </div>
      <el-menu :default-active="route.path" router background-color="#0a1929" text-color="#8892b0" active-text-color="#1890ff">
        <el-menu-item v-for="item in menus" :key="item.path" :index="item.path" v-if="!item.admin || user?.is_admin == 1">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
          <el-tag type="info" size="small" effect="dark">内网部署</el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ user?.name || '用户' }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main tech-bg">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Cpu, UserFilled, ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/store'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const user = computed(() => store.user)

const menus = [
  { path: '/dashboard', title: '领导驾驶舱', icon: 'DataAnalysis' },
  { path: '/check', title: '智能盘点', icon: 'CircleCheck' },
  { path: '/idle', title: '闲置盘活', icon: 'RefreshRight' },
  { path: '/lifecycle', title: '资产档案', icon: 'Files' },
  { path: '/scrap', title: '报废决策', icon: 'Delete' },
  { path: '/query', title: '智能查询', icon: 'Search' },
  { path: '/system', title: '系统管理', icon: 'Setting', admin: true },
]

const currentTitle = computed(() => route.meta?.title || '')

const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    store.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #0a1929; border-right: 1px solid #233554; }
.logo { display: flex; align-items: center; gap: 10px; padding: 20px; font-size: 16px; font-weight: bold; color: #e6f1ff; border-bottom: 1px solid #233554; }
:deep(.el-menu) { border-right: none; }
.header { background: #112240; border-bottom: 1px solid #233554; display: flex; align-items: center; justify-content: space-between; }
.header-title { font-size: 18px; font-weight: bold; color: #e6f1ff; }
.header-right { display: flex; align-items: center; gap: 16px; }
.user-info { display: flex; align-items: center; gap: 6px; cursor: pointer; color: #8892b0; }
.main { padding: 20px; overflow-y: auto; }
</style>
