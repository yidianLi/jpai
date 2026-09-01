<template>
  <div>
    <div class="page-description">先盘活闲置资产，再计算采购缺口和预算参考。</div>
    <div class="tech-card">
      <el-form class="procurement-form">
        <el-form-item label="自然语言需求" class="request-field">
          <el-input v-model="text" type="textarea" :rows="2" placeholder="例如：为设计部采购10台笔记本" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="aiPreview">AI生成预览</el-button>
        <el-divider direction="vertical" />
        <el-form-item label="资产类别ID"><el-input-number v-model="form.class_id" :min="1" /></el-form-item>
        <el-form-item label="需求数量"><el-input-number v-model="form.quantity" :min="1" /></el-form-item>
        <el-button :loading="loading" @click="preview">规则预览</el-button>
      </el-form>
    </div>
    <div v-if="result" class="tech-card">
      <div class="summary">
        <div><b>{{ result.requested_quantity }}</b><span>需求数量</span></div>
        <div><b>{{ result.available_transfer }}</b><span>可调拨</span></div>
        <div><b>{{ result.purchase_gap }}</b><span>采购缺口</span></div>
        <div><b>{{ Number(result.estimated_budget).toLocaleString() }}</b><span>预算参考（元）</span></div>
      </div>
      <el-alert type="info" :closable="false">{{ result.disclaimer }}<span v-if="result.ai_used"> 已使用 {{ result.provider }}/{{ result.model }} 理解需求。</span></el-alert>
      <div class="result-actions"><el-button type="success" :loading="saving" @click="saveSuggestion">保存采购建议</el-button></div>
      <h3>可调拨资产</h3>
      <el-table :data="result.transfer_assets" stripe>
        <el-table-column prop="asset_id" label="资产ID" /><el-table-column prop="asset_name" label="名称" />
        <el-table-column prop="brand" label="品牌" /><el-table-column prop="model" label="型号" /><el-table-column prop="dept_name" label="当前部门" />
      </el-table>
      <h3>候选型号</h3>
      <el-table :data="result.candidates" stripe>
        <el-table-column prop="brand" label="品牌" /><el-table-column prop="model" label="型号" />
        <el-table-column prop="asset_count" label="历史数量" /><el-table-column prop="average_price" label="平均购置价" />
      </el-table>
    </div>
    <div class="tech-card suggestions"><div class="section-title">已保存建议</div><el-table :data="suggestions" stripe><el-table-column prop="id" label="编号" width="90"/><el-table-column prop="quantity" label="数量" width="90"/><el-table-column prop="status" label="状态" width="110"/><el-table-column prop="created_at" label="创建时间"/><el-table-column label="操作" width="120"><template #default="{row}"><el-button v-if="row.status==='draft'" link type="primary" @click="confirmSuggestion(row.id)">确认</el-button></template></el-table-column></el-table></div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { previewProcurement, aiPreviewProcurement, saveProcurementSuggestion, getProcurementSuggestions, confirmProcurementSuggestion } from '@/api'

const form = reactive({ class_id: null, quantity: 1 })
const text = ref('')
const result = ref(null)
const loading = ref(false)
const saving = ref(false)
const suggestions = ref([])
const preview = async () => { loading.value = true; try { result.value = await previewProcurement({ class_id: form.class_id || undefined, quantity: form.quantity }) } finally { loading.value = false } }
const aiPreview = async () => { if (!text.value.trim()) return; loading.value = true; try { result.value = await aiPreviewProcurement(text.value) } finally { loading.value = false } }
const saveSuggestion = async () => { if (!result.value) return; saving.value = true; try { await saveProcurementSuggestion({ class_id: form.class_id || null, quantity: result.value.requested_quantity, preview: result.value }); await loadSuggestions() } finally { saving.value = false } }
const loadSuggestions = async () => { const r = await getProcurementSuggestions(); suggestions.value = r.list || [] }
const confirmSuggestion = async (id) => { await confirmProcurementSuggestion(id); await loadSuggestions() }
loadSuggestions()
</script>

<style scoped>
.page-description { margin-bottom: 18px; color: #718198 }
.procurement-form { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap }
.request-field { flex: 1 1 360px; min-width: 260px }
.request-field :deep(.el-form-item__content) { width: 100% }
.request-field :deep(.el-textarea__inner) { resize: vertical }
.summary { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 16px; margin-bottom: 18px }
.summary div { padding: 14px; background: #f5f8fb }
.summary b { display: block; font-size: 22px; color: #1769aa }
.summary span { color: #718198; font-size: 12px }
h3 { margin: 20px 0 10px; color: #20334d }
.result-actions { margin: 14px 0; text-align: right }
.section-title { font-weight: 600; margin-bottom: 12px; color: #20334d }
@media (max-width: 700px) { .summary { grid-template-columns: repeat(2, minmax(120px, 1fr)) } .procurement-form { align-items: stretch } .procurement-form .el-button { width: 100% } .procurement-form :deep(.el-divider--vertical) { display: none } }
</style>
