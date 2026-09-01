<template>
  <div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="数据同步" name="sync">
        <div class="tech-card">
          <div class="card-title">数据同步管理</div>
          <el-alert type="info" :closable="false" style="margin-bottom:16px;">
            系统每日凌晨2点自动从原系统同步数据。也可手动触发同步。同步通道：直连原库（只读），待简普API文档到位后可切换为API方式。
          </el-alert>
          <el-space>
            <el-button type="primary" @click="doSync('all')" :loading="syncLoading">全量同步</el-button>
            <el-button @click="doSync('dict')" :loading="syncLoading">同步字典</el-button>
            <el-button @click="doSync('assets')" :loading="syncLoading">同步资产</el-button>
          </el-space>
          <div style="margin-top:20px;">
            <div class="card-title">大模型状态</div>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="服务状态">{{ llmHealth.status }}</el-descriptions-item>
              <el-descriptions-item label="已加载模型">{{ llmHealth.models?.join(', ') || '-' }}</el-descriptions-item>
              <el-descriptions-item label="目标模型">{{ llmHealth.model_loaded ? '已加载' : '未加载' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-tab-pane>
      <el-tab-pane label="部门人数维护" name="dept">
        <div class="tech-card">
          <div class="card-title">部门人数（用于人均资产指标）</div>
          <el-table :data="depts" size="small">
            <el-table-column prop="dept_name" label="部门名称" />
            <el-table-column prop="company_id" label="单位ID" width="120" />
            <el-table-column label="人数" width="200">
              <template #default="{ row }">
                <el-input-number v-model="row.headcount" :min="0" size="small" @change="saveHeadcount(row)" />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
      <el-tab-pane label="系统配置" name="config">
        <div class="tech-card">
          <div class="card-title">系统参数配置</div>
          <el-form :inline="true" size="default">
            <el-form-item label="闲置判定天数"><el-input-number v-model="config.idle_days" :min="30" /></el-form-item>
            <el-form-item label="残值率"><el-input-number v-model="config.residual_rate" :min="0" :max="1" :step="0.01" /></el-form-item>
            <el-form-item label="到期红色预警(天)"><el-input-number v-model="config.expire_red" :min="1" /></el-form-item>
            <el-form-item label="到期黄色预警(天)"><el-input-number v-model="config.expire_yellow" :min="1" /></el-form-item>
            <el-form-item><el-button type="primary" @click="saveConfig">保存配置</el-button></el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      <el-tab-pane label="线上 AI 配置" name="ai">
        <div class="tech-card ai-config-card">
          <div class="card-title">AI 服务连接</div>
          <el-alert type="info" :closable="false" style="margin-bottom:20px;">保存后，自然语言问答和后续接入的报告润色、资产归类等 AI 能力会统一使用此配置。</el-alert>
          <el-form label-width="108px" style="max-width:720px;">
            <el-form-item label="启用 AI"><el-switch v-model="aiConfig.enabled" /></el-form-item>
            <el-form-item label="服务类型"><el-radio-group v-model="aiConfig.provider"><el-radio value="openai">线上兼容接口</el-radio><el-radio value="ollama">本地 Ollama</el-radio></el-radio-group></el-form-item>
            <template v-if="aiConfig.provider === 'openai'">
              <el-form-item label="接口地址"><el-input v-model="aiConfig.base_url" placeholder="https://api.example.com/v1" /></el-form-item>
              <el-form-item label="模型名称"><el-input v-model="aiConfig.model" placeholder="例如：gpt-4o-mini" /></el-form-item>
              <el-form-item label="API Key"><el-input v-model="aiConfig.api_key" type="password" show-password :placeholder="aiConfig.api_key_configured ? '已配置；留空则不修改' : '请输入 API Key'" /></el-form-item>
            </template>
            <el-form-item><el-button type="primary" :loading="aiSaving" @click="saveAiConfig">保存并生效</el-button><span v-if="aiConfig.api_key_configured" class="key-status">API Key 已保存</span></el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { syncAll, syncDict, syncAssets, getDepartments, updateHeadcount, getLlmHealth, getAiConfig, updateAiConfig } from '@/api'

const activeTab = ref('sync')
const syncLoading = ref(false)
const depts = ref([])
const llmHealth = ref({})
const config = reactive({ idle_days: 90, residual_rate: 0.05, expire_red: 90, expire_yellow: 180 })
const aiSaving = ref(false)
const aiConfig = reactive({ enabled: true, provider: 'openai', base_url: '', model: '', api_key: '', api_key_configured: false })

const doSync = async (type) => {
  syncLoading.value = true
  try {
    if (type === 'all') await syncAll()
    else if (type === 'dict') await syncDict()
    else await syncAssets()
    ElMessage.success('同步完成')
  } catch (e) {
    ElMessage.error('同步失败，请检查数据库连接')
  } finally { syncLoading.value = false }
}
const loadDepts = async () => { depts.value = await getDepartments() }
const saveHeadcount = async (row) => {
  await updateHeadcount(row.dept_id, row.headcount)
  ElMessage.success('已更新')
}
const loadLlmHealth = async () => {
  try { llmHealth.value = await getLlmHealth() } catch { llmHealth.value = { status: 'unknown' } }
}
const saveConfig = () => { ElMessage.success('配置已保存（演示）') }
const loadAiConfig = async () => { Object.assign(aiConfig, await getAiConfig()) }
const saveAiConfig = async () => {
  aiSaving.value = true
  try {
    await updateAiConfig({ enabled: aiConfig.enabled, provider: aiConfig.provider, base_url: aiConfig.base_url, model: aiConfig.model, api_key: aiConfig.api_key })
    aiConfig.api_key = ''
    await loadAiConfig()
    await loadLlmHealth()
    ElMessage.success('AI 配置已保存并生效')
  } finally { aiSaving.value = false }
}
onMounted(() => { loadDepts(); loadLlmHealth(); loadAiConfig() })
</script>

<style scoped>
.card-title { font-size:16px; font-weight:650; color:#20334d; margin-bottom:12px; border-left:3px solid #1769aa; padding-left:10px; }
:deep(.el-tabs__item) { color:#53657d; font-weight:500; }
:deep(.el-tabs__item.is-active) { color:#1769aa; font-weight:650; }
:deep(.el-tabs__active-bar) { background-color:#1769aa; }
:deep(.el-alert--info) { --el-alert-bg-color:#eef6fd; --el-alert-border-color:#cfe0ef; --el-alert-text-color:#354965; }
:deep(.el-descriptions__label) { background:#f5f8fb !important; color:#53657d !important; }
:deep(.el-descriptions__content) { color:#20334d !important; }
.key-status { margin-left:12px; color:#198f6b; font-size:13px; }
</style>
