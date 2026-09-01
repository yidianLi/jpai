<template>
  <div class="login-container tech-bg">
    <div class="login-box tech-card">
      <div class="login-title">
        <el-icon :size="32" color="#1890ff"><Monitor /></el-icon>
        <h1>简普数智资产管理后台</h1>
        <p>AI-Powered Fixed Asset Management</p>
      </div>
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">登 录</el-button>
      </el-form>
      <div class="login-footer">内网部署 · 数据不出域 · 信创兼容</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Monitor } from '@element-plus/icons-vue'
import { login } from '@/api'
import { useUserStore } from '@/store'

const router = useRouter()
const store = useUserStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = new URLSearchParams()
    data.append('username', form.username)
    data.append('password', form.password)
    const res = await fetch('/api/auth/login', { method: 'POST', body: data })
    const result = await res.json()
    if (result.access_token) {
      store.setLogin(result.access_token, result.user)
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } else {
      ElMessage.error(result.detail || '登录失败')
    }
  } catch (e) {
    ElMessage.error('登录失败，请检查网络')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; position: relative; z-index: 1;
}
.login-box { width: 400px; padding: 40px; }
.login-title { text-align: center; margin-bottom: 30px; }
.login-title h1 { font-size: 22px; color: #e6f1ff; margin: 12px 0 6px; }
.login-title p { font-size: 12px; color: #8892b0; letter-spacing: 2px; }
.login-btn { width: 100%; background: linear-gradient(135deg, #1890ff, #096dd9); border: none; }
.login-footer { text-align: center; margin-top: 20px; font-size: 12px; color: #8892b0; }
</style>
