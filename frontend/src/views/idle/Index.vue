<template>
  <div class="page-shell">
    <header class="page-head"><div><span class="page-kicker">IDLE ASSET ACTIVATION</span><h2>闲置盘活</h2><p>识别闲置资产并优先推进调拨、维修或报废。</p></div><el-button type="primary" @click="refresh">刷新闲置池</el-button></header>
    <el-row :gutter="16">
      <el-col :span="6"><div class="metric-card"><div class="metric-value">{{ stats.idle_count }}</div><div class="metric-label">闲置资产数</div></div></el-col>
      <el-col :span="6"><div class="metric-card"><div class="metric-value" style="color:#ffaa00">¥{{ (stats.idle_value/10000)?.toFixed(1) }}万</div><div class="metric-label">估算闲置价值</div></div></el-col>
      <el-col :span="6"><div class="metric-card"><div class="metric-value" style="color:#00d4aa">{{ stats.transferred_count }}</div><div class="metric-label">已盘活数</div></div></el-col>
      <el-col :span="6"><div class="metric-card"><div class="metric-value">{{ stats.avg_idle_days }}天</div><div class="metric-label">平均闲置时长</div></div></el-col>
    </el-row>
    <div class="tech-card list-card">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>闲置资产池</span>
        <el-space>
          <el-input v-model="searchDept" placeholder="按部门筛选" clearable size="small" style="width:160px" @clear="loadList" />
          <el-select v-model="minDays" placeholder="闲置天数" clearable size="small" style="width:140px" @change="loadList">
            <el-option :value="90" label="90天以上" />
            <el-option :value="180" label="180天以上" />
            <el-option :value="365" label="1年以上" />
          </el-select>
          <span class="result-count">共 {{ total }} 条资产</span>
        </el-space>
      </div>
      <FilterChips :items="activeFilters" @remove="removeFilter" @clear="clearFilters" />
      <DataState :loading="loading" :error="error" :empty="!list.length" empty-text="当前筛选下暂无闲置资产" @retry="loadList"><template #default><el-table :data="list" size="small" width="100%" max-height="500" fit class="idle-table">
        <el-table-column prop="barcode" label="资产编号" width="180" show-overflow-tooltip />
        <el-table-column prop="asset_name" label="资产名称" width="185" show-overflow-tooltip />
        <el-table-column prop="model" label="型号" min-width="255" show-overflow-tooltip />
        <el-table-column prop="dept_name" label="所属部门" width="165" show-overflow-tooltip />
        <el-table-column prop="position" label="存放位置" width="175" show-overflow-tooltip />
        <el-table-column prop="buy_price" label="原值(元)" width="125" :formatter="formatAmount" />
        <el-table-column prop="estimated_value" label="估算价值" width="125" :formatter="formatAmount" />
        <el-table-column prop="idle_days" label="闲置天数" width="105">
          <template #default="{ row }"><span :class="row.idle_days>=180?'tag-red':'tag-yellow'">{{ row.idle_days }}天</span></template>
        </el-table-column>
        <el-table-column label="建议" width="115">
          <template #default="{ row }">
            <span :class="row.suggest_action=='scrap'?'tag-red':row.suggest_action=='transfer'?'tag-blue':'tag-green'">
              {{ row.suggest_action=='scrap'?'建议报废':row.suggest_action=='transfer'?'建议调拨':'继续使用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="115">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="transfer(row)">标记调拨</el-button>
          </template>
        </el-table-column>
      </el-table></template></DataState>
      <el-pagination style="margin-top:12px;justify-content:flex-end;display:flex;" background layout="total, prev, pager, next" :total="total" :page-size="20" :current-page="page" @current-change="p => {page=p;loadList()}" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getIdlePool, getIdleStats, refreshIdle } from '@/api'
import DataState from '@/components/DataState.vue'
import FilterChips from '@/components/FilterChips.vue'
const router = useRouter()

const list = ref([])
const stats = ref({})
const total = ref(0)
const page = ref(1)
const searchDept = ref('')
const minDays = ref(null)
const loading = ref(false)
const error = ref(false)
const activeFilters = computed(() => { const a=[]; if(searchDept.value) a.push({key:'dept',label:'部门',value:searchDept.value}); if(minDays.value) a.push({key:'days',label:'闲置时长',value:`${minDays.value}天以上`}); return a })
const removeFilter = key => { if(key==='dept') searchDept.value=''; if(key==='days') minDays.value=null; page.value=1; loadList() }
const clearFilters = () => { searchDept.value=''; minDays.value=null; page.value=1; loadList() }
const formatAmount = (_, __, value) => value == null ? '-' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })

const loadList = async () => {
  loading.value = true; error.value = false
  try { const res = await getIdlePool({ dept: searchDept.value || undefined, min_days: minDays.value || undefined, page: page.value, size: 20 }); list.value = res.list; total.value = res.total } catch { error.value=true; list.value=[]; total.value=0 } finally { loading.value = false }
}
const loadStats = async () => { stats.value = await getIdleStats() }
const refresh = async () => {
  await refreshIdle()
  ElMessage.success('闲置池已刷新')
  loadList(); loadStats()
}
const transfer = async (row) => {
  router.push({ path: '/transfer', query: { asset_id: row.id } })
}
onMounted(async () => {
  await Promise.allSettled([loadList(), loadStats()])
})
</script>

<style scoped>
.page-shell{display:grid;gap:16px}.page-head{display:flex;align-items:flex-end;justify-content:space-between}.page-kicker{font-size:11px;letter-spacing:1.6px;color:#1769aa}.page-head h2{margin:4px 0 6px;font-size:24px}.page-head p,.result-count{color:#718198;font-size:13px}.list-card{margin-top:0}
.card-title { font-size:16px; font-weight:650; color:#20334d; margin-bottom:12px; border-left:3px solid #1769aa; padding-left:10px; }
.idle-table :deep(.el-table__cell) { padding:10px 12px; }
.idle-table :deep(.cell) { line-height:20px; }
</style>
