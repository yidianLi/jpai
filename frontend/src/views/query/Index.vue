<template>
  <div>
    <div class="page-title">智能查询与分析</div>

    <!-- 自然语言查询 -->
    <div class="tech-card" style="margin-bottom:16px;">
      <div class="card-title">AI自然语言查询 <span class="tag-blue" style="margin-left:8px;">本地大模型驱动</span></div>
      <div class="nl-search">
        <el-input v-model="nlInput" placeholder="例如：办公室有多少台闲置的笔记本电脑？" size="large" @keyup.enter="doNlQuery">
          <template #prefix><el-icon><ChatDotRound /></el-icon></template>
          <template #append><el-button type="primary" @click="doNlQuery" :loading="nlLoading">查询</el-button></template>
        </el-input>
      </div>
      <div v-if="nlAnswer" class="nl-answer tech-card" style="margin-top:12px;background:rgba(24,144,255,0.05);">
        <div style="color:#1890ff;font-weight:bold;margin-bottom:6px;">AI回答</div>
        <div>{{ nlAnswer.answer }}</div>
        <div v-if="nlAnswer.filters" style="margin-top:8px;font-size:12px;color:#8892b0;">
          识别意图: {{ nlAnswer.intent }} | 筛选条件: {{ JSON.stringify(nlAnswer.filters) }}
        </div>
      </div>
      <div style="margin-top:12px;">
        <el-tag v-for="q in quickQueries" :key="q" size="small" style="margin-right:8px;margin-bottom:6px;cursor:pointer;" @click="nlQuery=q;doNlQuery()">{{ q }}</el-tag>
      </div>
    </div>

    <!-- 多维度筛选 -->
    <div class="tech-card" style="margin-bottom:16px;">
      <div class="card-title">多维度资产筛选</div>
      <el-form :inline="true" size="small">
        <el-form-item label="关键词"><el-input v-model="filter.keyword" placeholder="名称/编号/型号" clearable style="width:180px" /></el-form-item>
        <el-form-item label="分类"><el-select v-model="filter.class_id" placeholder="全部" clearable style="width:160px;"><el-option v-for="c in classes" :key="c.class_id" :label="c.class_name" :value="c.class_id" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="filter.state_id" placeholder="全部" clearable style="width:140px;"><el-option v-for="s in states" :key="s.state_id" :label="s.state_name" :value="s.state_id" /></el-select></el-form-item>
        <el-form-item label="部门"><el-select v-model="filter.dept_id" placeholder="全部" clearable style="width:140px;"><el-option v-for="d in depts" :key="d.dept_id" :label="d.dept_name" :value="d.dept_id" /></el-select></el-form-item>
        <el-form-item label="是否闲置"><el-select v-model="filter.is_idle" placeholder="全部" clearable style="width:100px;"><el-option :value="1" label="是" /><el-option :value="0" label="否" /></el-select></el-form-item>
        <el-form-item label="价值区间"><el-input-number v-model="filter.min_price" placeholder="最小" style="width:100px;" /> - <el-input-number v-model="filter.max_price" placeholder="最大" style="width:100px;" /></el-form-item>
        <el-form-item><el-button type="primary" @click="doQuery">查询</el-button><el-button @click="resetFilter">重置</el-button><el-button @click="exportExcel">导出Excel</el-button></el-form-item>
      </el-form>
    </div>

    <!-- 查询结果 -->
    <div class="tech-card">
      <div class="card-title">查询结果（共{{ total }}条）</div>
      <el-table :data="results" size="small" max-height="450">
        <el-table-column prop="barcode" label="资产编号" width="160" />
        <el-table-column prop="asset_name" label="资产名称" />
        <el-table-column prop="model" label="型号" width="120" />
        <el-table-column prop="class_path" label="分类" width="160" show-overflow-tooltip />
        <el-table-column prop="state_name" label="状态" width="80" />
        <el-table-column prop="dept_name" label="部门" width="100" />
        <el-table-column prop="responsible" label="责任人" width="90" />
        <el-table-column prop="buy_price" label="原值(元)" width="100" />
        <el-table-column prop="current_value" label="净值(元)" width="100" />
        <el-table-column prop="buy_date" label="购置日期" width="110" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }"><el-button type="primary" link size="small" @click="viewDetail(row)">详情</el-button></template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:12px;justify-content:flex-end;display:flex;" background layout="total, prev, pager, next" :total="total" :page-size="20" :current-page="page" @current-change="p => {page=p;doQuery()}" />
    </div>

    <!-- 采购预测 -->
    <div class="tech-card" style="margin-top:16px;">
      <div class="card-title" style="display:flex;justify-content:space-between;">
        <span>采购需求预测（规则驱动+移动平均）</span>
        <el-button type="primary" size="small" @click="runForecast">重新计算</el-button>
      </div>
      <el-table :data="forecast" size="small">
        <el-table-column prop="class_name" label="资产类别" />
        <el-table-column prop="forecast_qty" label="预测需求量(台/半年)" width="160" />
        <el-table-column prop="basis" label="预测依据" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { queryAssets, nlQuery, getForecast, computeForecast, getDepartments, getAssetClasses, getAssetStates } from '@/api'
import { useRouter } from 'vue-router'

const router = useRouter()
const nlInput = ref('')
const nlLoading = ref(false)
const nlAnswer = ref(null)
const quickQueries = ['有多少台闲置的电脑', '哪个部门资产最多', '今年新增了多少资产', '即将到期的资产有哪些']
const filter = reactive({ keyword: '', class_id: null, state_id: null, dept_id: null, is_idle: null, min_price: null, max_price: null })
const results = ref([])
const total = ref(0)
const page = ref(1)
const forecast = ref([])
const classes = ref([])
const states = ref([])
const depts = ref([])

const doNlQuery = async () => {
  if (!nlInput.value) return
  nlLoading.value = true
  try { nlAnswer.value = await nlQuery(nlInput.value) } finally { nlLoading.value = false }
}
const doQuery = async () => {
  const params = { ...filter, page: page.value, size: 20 }
  Object.keys(params).forEach(k => { if (params[k] === '' || params[k] === null) delete params[k] })
  const res = await queryAssets(params)
  results.value = res.list
  total.value = res.total
}
const resetFilter = () => {
  Object.assign(filter, { keyword: '', class_id: null, state_id: null, dept_id: null, is_idle: null, min_price: null, max_price: null })
  page.value = 1
  doQuery()
}
const viewDetail = (row) => { router.push({ path: '/lifecycle', query: { id: row.asset_id } }) }
const exportExcel = () => {
  const headers = ['编号','名称','型号','分类','状态','部门','责任人','原值','净值','购置日期']
  const rows = results.value.map(r => [r.barcode,r.asset_name,r.model,r.class_path,r.state_name,r.dept_name,r.responsible,r.buy_price,r.current_value,r.buy_date])
  const csv = '\uFEFF' + [headers, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = '资产查询结果.csv'
  a.click()
}
const loadForecast = async () => { forecast.value = await getForecast() }
const runForecast = async () => { await computeForecast(6); loadForecast() }
onMounted(async () => {
  doQuery()
  loadForecast()
  classes.value = await getAssetClasses()
  states.value = await getAssetStates()
  depts.value = await getDepartments()
})
</script>

<style scoped>
.card-title { font-size: 16px; font-weight: bold; color: #e6f1ff; margin-bottom: 12px; border-left: 3px solid #1890ff; padding-left: 10px; }
.nl-answer { padding: 16px; border-left: 3px solid #1890ff; }
</style>
