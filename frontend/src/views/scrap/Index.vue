<template>
  <div class="page-shell">
    <header class="page-head"><div><span class="page-kicker">RETIREMENT DECISION</span><h2>报废决策</h2><p>按到期范围筛选资产，查看净值并发起评估。</p></div></header>
    <div class="tech-card">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>到期资产清单</span>
        <el-space>
          <el-select v-model="filterDays" placeholder="到期范围" clearable size="small" style="width:140px" @change="loadList">
            <el-option :value="90" label="3个月内" />
            <el-option :value="180" label="6个月内" />
          <el-option :value="365" label="1年内" />
          </el-select>
          <el-button type="primary" size="small" @click="batchEval" :disabled="!selected.length">批量评估({{ selected.length }})</el-button>
        </el-space>
      </div>
      <FilterChips :items="activeFilters" @remove="removeFilter" @clear="clearFilters" />
      <el-table :data="list" size="small" max-height="450" @selection-change="selected = $">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="barcode" label="资产编号" width="160" />
        <el-table-column prop="asset_name" label="资产名称" />
        <el-table-column prop="model" label="型号" width="120" />
        <el-table-column prop="dept_name" label="部门" width="100" />
        <el-table-column prop="buy_date" label="购置日期" width="110" />
        <el-table-column prop="use_year" label="使用年限" width="80" />
        <el-table-column prop="expire_date" label="到期日" width="110" />
        <el-table-column label="剩余天数" width="90">
          <template #default="{ row }">
            <span :class="row.days_left <= 30 ? 'tag-red' : row.days_left <= 90 ? 'tag-yellow' : 'tag-blue'">{{ row.days_left }}天</span>
          </template>
        </el-table-column>
        <el-table-column prop="current_value" label="净值(元)" width="100" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }"><el-button type="primary" link size="small" @click="evaluate(row)">AI评估</el-button></template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:12px;justify-content:flex-end;display:flex;" background layout="total, prev, pager, next" :total="total" :page-size="20" :current-page="page" @current-change="p => {page=p;loadList()}" />
    </div>

    <!-- 评估结果弹窗 -->
    <el-dialog v-model="evalVisible" title="AI报废评估结果" width="600px">
      <div v-if="evalResult" class="eval-result">
        <el-alert :title="`评估结论：${evalResult.eval_result_text}`" :type="evalResult.eval_result==1?'error':evalResult.eval_result==2?'success':'warning'" show-icon style="margin-bottom:16px;" />
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="资产名称">{{ evalResult.asset_name }}</el-descriptions-item>
          <el-descriptions-item label="已使用比例">{{ evalResult.used_ratio }}%</el-descriptions-item>
          <el-descriptions-item label="维修次数">{{ evalResult.repair_count }}次</el-descriptions-item>
          <el-descriptions-item label="当前净值">¥{{ evalResult.current_value?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="估算残值">¥{{ evalResult.residual_value?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="处置建议">{{ {sell:'变卖',donate:'捐赠',recycle:'回收',destroy:'销毁'}[evalResult.dispose_suggest] }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <div style="font-weight:bold;margin-bottom:8px;">评估依据：</div>
        <div v-for="(r, i) in evalResult.reasons" :key="i" style="padding:4px 0;color:#354965;">• {{ r }}</div>
        <el-alert v-if="evalResult.abnormal" title="注意：该资产使用不足1/3年限即建议报废，需重点审核！" type="error" show-icon style="margin-top:12px;" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getExpireList, evaluateAsset, batchEvaluate } from '@/api'
import FilterChips from '@/components/FilterChips.vue'

const list = ref([])
const total = ref(0)
const page = ref(1)
const filterDays = ref(null)
const activeFilters = computed(() => filterDays.value ? [{ key: 'days', label: '到期范围', value: `${filterDays.value}天内` }] : [])
const removeFilter = () => { filterDays.value=null; page.value=1; loadList() }
const clearFilters = () => { filterDays.value=null; page.value=1; loadList() }
const selected = ref([])
const evalVisible = ref(false)
const evalResult = ref(null)

const loadList = async () => {
  const res = await getExpireList({ days: filterDays.value || undefined, page: page.value, size: 20 })
  list.value = res.list
  total.value = res.total
}
const evaluate = async (row) => {
  evalResult.value = await evaluateAsset(row.asset_id)
  evalVisible.value = true
}
const batchEval = async () => {
  const ids = selected.value.map(r => r.asset_id)
  const results = await batchEvaluate(ids)
  ElMessage.success(`已完成${results.length}台资产评估，详情请查看评估记录`)
  console.log('批量评估结果:', results)
}
onMounted(loadList)
</script>

<style scoped>
.page-shell{display:grid;gap:16px}.page-head{display:flex;align-items:flex-end}.page-kicker{font-size:11px;letter-spacing:1.6px;color:#1769aa}.page-head h2{margin:4px 0 6px;font-size:24px}.page-head p{color:#718198;font-size:13px}
.card-title { font-size:16px; font-weight:650; color:#20334d; margin-bottom:12px; border-left:3px solid #1769aa; padding-left:10px; }
.eval-result { padding: 10px 0; }
</style>
