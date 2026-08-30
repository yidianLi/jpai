<template>
  <div>
    <div class="page-title">闲置资产盘活</div>
    <el-row :gutter="16">
      <el-col :span="6"><div class="metric-card"><div class="metric-value">{{ stats.idle_count }}</div><div class="metric-label">闲置资产数</div></div></el-col>
      <el-col :span="6"><div class="metric-card"><div class="metric-value" style="color:#ffaa00">¥{{ (stats.idle_value/10000)?.toFixed(1) }}万</div><div class="metric-label">估算闲置价值</div></div></el-col>
      <el-col :span="6"><div class="metric-card"><div class="metric-value" style="color:#00d4aa">{{ stats.transferred_count }}</div><div class="metric-label">已盘活数</div></div></el-col>
      <el-col :span="6"><div class="metric-card"><div class="metric-value">{{ stats.avg_idle_days }}天</div><div class="metric-label">平均闲置时长</div></div></el-col>
    </el-row>
    <div class="tech-card" style="margin-top:16px;">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>闲置资产池</span>
        <el-space>
          <el-input v-model="searchDept" placeholder="按部门筛选" clearable size="small" style="width:160px" @clear="loadList" />
          <el-select v-model="minDays" placeholder="闲置天数" clearable size="small" style="width:140px" @change="loadList">
            <el-option :value="90" label="90天以上" />
            <el-option :value="180" label="180天以上" />
            <el-option :value="365" label="1年以上" />
          </el-select>
          <el-button type="primary" size="small" @click="refresh">刷新闲置池</el-button>
        </el-space>
      </div>
      <el-table :data="list" size="small" max-height="500">
        <el-table-column prop="barcode" label="资产编号" width="160" />
        <el-table-column prop="asset_name" label="资产名称" />
        <el-table-column prop="model" label="型号" width="140" />
        <el-table-column prop="dept_name" label="所属部门" width="120" />
        <el-table-column prop="position" label="存放位置" width="140" />
        <el-table-column prop="buy_price" label="原值(元)" width="100" />
        <el-table-column prop="estimated_value" label="估算价值" width="100" />
        <el-table-column prop="idle_days" label="闲置天数" width="90">
          <template #default="{ row }"><span :class="row.idle_days>=180?'tag-red':'tag-yellow'">{{ row.idle_days }}天</span></template>
        </el-table-column>
        <el-table-column label="建议" width="100">
          <template #default="{ row }">
            <span :class="row.suggest_action=='scrap'?'tag-red':row.suggest_action=='transfer'?'tag-blue':'tag-green'">
              {{ row.suggest_action=='scrap'?'建议报废':row.suggest_action=='transfer'?'建议调拨':'继续使用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="transfer(row)">标记调拨</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:12px;justify-content:flex-end;display:flex;" background layout="total, prev, pager, next" :total="total" :page-size="20" :current-page="page" @current-change="p => {page=p;loadList()}" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getIdlePool, getIdleStats, refreshIdle, markTransfer } from '@/api'

const list = ref([])
const stats = ref({})
const total = ref(0)
const page = ref(1)
const searchDept = ref('')
const minDays = ref(null)

const loadList = async () => {
  const res = await getIdlePool({ dept: searchDept.value || undefined, min_days: minDays.value || undefined, page: page.value, size: 20 })
  list.value = res.list
  total.value = res.total
}
const loadStats = async () => { stats.value = await getIdleStats() }
const refresh = async () => {
  await refreshIdle()
  ElMessage.success('闲置池已刷新')
  loadList(); loadStats()
}
const transfer = async (row) => {
  await ElMessageBox.confirm(`确认将资产"${row.asset_name}"标记为已调拨？`, '确认', { type: 'warning' })
  await markTransfer(row.id)
  ElMessage.success('已标记')
  loadList(); loadStats()
}
onMounted(() => { loadList(); loadStats() })
</script>

<style scoped>
.card-title { font-size: 16px; font-weight: bold; color: #e6f1ff; margin-bottom: 12px; border-left: 3px solid #1890ff; padding-left: 10px; }
</style>
