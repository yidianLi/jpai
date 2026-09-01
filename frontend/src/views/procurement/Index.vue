<template>
  <div class="page-shell">
    <header class="page-head"><div><span class="page-kicker">PROCUREMENT DECISION</span><h2>采购建议</h2><p>先盘活闲置资产，再计算采购缺口和预算参考。</p></div></header>
    <div class="page-description">先盘活闲置资产，再计算采购缺口和预算参考。</div>
    <div class="tech-card input-card">
      <el-alert v-if="formError" :title="formError" type="error" show-icon :closable="false" class="form-error" />
      <el-form class="procurement-form" label-position="top">
        <el-form-item label="自然语言需求" class="request-field">
          <el-input v-model="text" type="textarea" :rows="2" placeholder="例如：为设计部采购10台笔记本" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="aiPreview">AI生成预览</el-button>
        <el-divider direction="vertical" />
        <el-form-item label="资产类别ID"><el-input-number v-model="form.class_id" :min="1" /></el-form-item>
        <el-form-item label="需求数量" required><el-input-number v-model="form.quantity" :min="1" :max="100000" controls-position="right" /></el-form-item>
        <el-button :loading="loading" @click="preview">规则预览</el-button>
      </el-form>
    </div>
    <div v-if="result" class="tech-card result-card">
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { previewProcurement, aiPreviewProcurement, saveProcurementSuggestion, getProcurementSuggestions, confirmProcurementSuggestion } from '@/api'

const form = reactive({ class_id: null, quantity: 1 })
const text = ref('')
const result = ref(null)
const loading = ref(false)
const saving = ref(false)
const formError = ref('')
const suggestions = ref([])
const preview = async () => { if(form.quantity<1) { formError.value='需求数量必须大于 0'; return }; formError.value=''; loading.value = true; try { result.value = await previewProcurement({ class_id: form.class_id || undefined, quantity: form.quantity }) } catch { formError.value='规则预览失败，请稍后重试' } finally { loading.value = false } }
const aiPreview = async () => { if (!text.value.trim()) { formError.value='请输入自然语言采购需求'; return }; formError.value=''; loading.value = true; try { result.value = await aiPreviewProcurement(text.value) } catch { formError.value='AI 预览失败，可继续使用规则预览' } finally { loading.value = false } }
const saveSuggestion = async () => { if (!result.value) return; try { await ElMessageBox.confirm('保存后将形成待确认采购建议，是否继续？','确认保存',{type:'info'}); saving.value = true; await saveProcurementSuggestion({ class_id: form.class_id || null, quantity: result.value.requested_quantity, preview: result.value }); ElMessage.success('采购建议已保存'); await loadSuggestions() } catch {} finally { saving.value = false } }
const loadSuggestions = async () => { const r = await getProcurementSuggestions(); suggestions.value = r.list || [] }
const confirmSuggestion = async (id) => { try { await ElMessageBox.confirm('确认后将进入人工确认结果，是否继续？','确认采购建议',{type:'warning'}); await confirmProcurementSuggestion(id); ElMessage.success('采购建议已确认'); await loadSuggestions() } catch {} }
loadSuggestions()
</script>
<style scoped>
.page-shell{display:grid;gap:16px}.page-head{display:flex;align-items:flex-end}.page-kicker{font-size:11px;letter-spacing:1.6px;color:#1769aa}.page-head h2{margin:4px 0 6px;font-size:24px}.page-head p{color:#718198;font-size:13px}.input-card{background:#fff}.result-card{display:grid;gap:16px}.result-card h3{font-size:15px;color:#20334d;margin:4px 0 -4px;border-left:3px solid #1769aa;padding-left:8px}
.form-error{margin-bottom:16px}
</style>

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
