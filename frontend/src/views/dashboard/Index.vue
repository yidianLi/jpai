<template>
  <div class="dashboard">
    <!-- 顶部指标卡 -->
    <el-row :gutter="16" class="metric-row">
      <el-col :span="4" v-for="m in metrics" :key="m.label">
        <div class="metric-card">
          <div class="metric-value">{{ m.value }}</div>
          <div class="metric-label">{{ m.label }}</div>
          <div v-if="m.sub" class="metric-sub" :class="m.subClass">{{ m.sub }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="8">
        <div class="tech-card">
          <div class="card-title">资产分类分布</div>
          <div ref="classChart" style="height: 280px;"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="tech-card">
          <div class="card-title">资产状态分布</div>
          <div ref="stateChart" style="height: 280px;"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="tech-card">
          <div class="card-title">近12个月增减趋势</div>
          <div ref="trendChart" style="height: 280px;"></div>
        </div>
      </el-col>
    </el-row>

    <!-- 底部：部门排名 + 预警 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="12">
        <div class="tech-card">
          <div class="card-title">部门资产排名</div>
          <el-table :data="deptRanking" size="small" max-height="300">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="dept" label="部门" />
            <el-table-column prop="count" label="数量" width="80" />
            <el-table-column prop="value" label="原值(元)" width="120">
              <template #default="{ row }">{{ row.value?.toLocaleString() }}</template>
            </el-table-column>
            <el-table-column label="闲置率" width="100">
              <template #default="{ row }">
                <span :class="row.idle_rate > 10 ? 'tag-red' : 'tag-green'">{{ row.idle_rate }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="tech-card">
          <div class="card-title" style="display:flex;justify-content:space-between;">
            <span>实时预警</span>
            <el-button type="primary" link size="small" @click="loadWarnings">刷新</el-button>
          </div>
          <div v-for="w in warnings.list" :key="w.id" class="warning-item">
            <span :class="w.level == 1 ? 'dot-red' : w.level == 2 ? 'dot-yellow' : 'dot-blue'"></span>
            <span class="warning-text">{{ w.content }}</span>
            <span class="warning-date">{{ w.date }}</span>
          </div>
          <el-empty v-if="!warnings.list?.length" description="暂无预警" :image-size="60" />
        </div>
      </el-col>
    </el-row>

    <!-- 报告生成 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="24">
        <div class="tech-card">
          <div class="card-title">报告生成</div>
          <el-space>
            <el-date-picker v-model="reportMonth" type="month" placeholder="选择月份" value-format="YYYY-MM" />
            <el-button type="primary" @click="genReport" :loading="genLoading">生成月度报告</el-button>
            <el-button @click="loadReports">查看历史报告</el-button>
          </el-space>
          <el-table :data="reports" size="small" style="margin-top: 12px;" max-height="200">
            <el-table-column prop="title" label="报告名称" />
            <el-table-column prop="period" label="期间" width="120" />
            <el-table-column prop="create_time" label="生成时间" width="180" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="downloadReport(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getOverview, getClassDistribution, getStateDistribution, getMonthlyTrend, getDeptRanking, getWarnings, generateMonthlyReport, getReports } from '@/api'

const overview = ref({})
const classChart = ref()
const stateChart = ref()
const trendChart = ref()
const deptRanking = ref([])
const warnings = reactive({ list: [], total: 0 })
const reportMonth = ref('')
const genLoading = ref(false)
const reports = ref([])

const metrics = ref([
  { label: '资产总数', value: '-', sub: '' },
  { label: '资产原值(万)', value: '-', sub: '' },
  { label: '账面净值(万)', value: '-', sub: '' },
  { label: '在用资产', value: '-', sub: '' },
  { label: '闲置资产', value: '-', sub: '', subClass: 'text-yellow' },
  { label: '未处理预警', value: '-', sub: '', subClass: 'text-red' },
])

const loadData = async () => {
  const ov = await getOverview()
  overview.value = ov
  metrics.value = [
    { label: '资产总数', value: ov.total_count?.toLocaleString() },
    { label: '资产原值(万)', value: (ov.total_value / 10000)?.toFixed(1) },
    { label: '账面净值(万)', value: (ov.current_value / 10000)?.toFixed(1) },
    { label: '在用资产', value: ov.in_use_count?.toLocaleString() },
    { label: '闲置资产', value: ov.idle_count, sub: `闲置率 ${ov.idle_rate}%`, subClass: 'text-yellow' },
    { label: '未处理预警', value: ov.warning_count, sub: `账实相符率 ${ov.match_rate}%`, subClass: 'text-red' },
  ]
  const cls = await getClassDistribution()
  const states = await getStateDistribution()
  const trend = await getMonthlyTrend(12)
  deptRanking.value = await getDeptRanking()

  await nextTick()
  // 分类饼图
  echarts.init(classChart.value).setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['40%', '70%'], data: cls.slice(0, 8).map(c => ({ name: c.name, value: c.count })),
      itemStyle: { borderColor: '#112240', borderWidth: 2 }, label: { color: '#8892b0' } }]
  })
  // 状态柱状图
  echarts.init(stateChart.value).setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: states.map(s => s.name), axisLabel: { color: '#8892b0', rotate: 30 } },
    yAxis: { type: 'value', axisLabel: { color: '#8892b0' } },
    series: [{ type: 'bar', data: states.map(s => s.value), itemStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#1890ff'},{offset:1,color:'#096dd9'}]) } }]
  })
  // 趋势折线图
  echarts.init(trendChart.value).setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增', '减少'], textStyle: { color: '#8892b0' } },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: trend.map(t => t.month), axisLabel: { color: '#8892b0' } },
    yAxis: { type: 'value', axisLabel: { color: '#8892b0' } },
    series: [
      { name: '新增', type: 'line', smooth: true, data: trend.map(t => t.added), itemStyle: { color: '#00d4aa' }, areaStyle: { opacity: 0.2 } },
      { name: '减少', type: 'line', smooth: true, data: trend.map(t => t.reduced), itemStyle: { color: '#ff4757' }, areaStyle: { opacity: 0.2 } },
    ]
  })
}

const loadWarnings = async () => {
  const res = await getWarnings({ status: 0, size: 10 })
  warnings.list = res.list
  warnings.total = res.total
}

const genReport = async () => {
  if (!reportMonth.value) { ElMessage.warning('请选择月份'); return }
  const [y, m] = reportMonth.value.split('-')
  genLoading.value = true
  try {
    await generateMonthlyReport(parseInt(y), parseInt(m))
    ElMessage.success('报告生成成功')
    loadReports()
  } finally { genLoading.value = false }
}

const loadReports = async () => {
  const res = await getReports({ size: 10 })
  reports.value = res.list
}

const downloadReport = (row) => {
  window.open(`/api${row.file_path.replace('reports', 'dashboard/reports')}`, '_blank')
}

onMounted(() => { loadData(); loadWarnings(); loadReports() })
</script>

<style scoped>
.metric-row { margin-bottom: 0; }
.card-title { font-size: 16px; font-weight: bold; color: #e6f1ff; margin-bottom: 12px; border-left: 3px solid #1890ff; padding-left: 10px; }
.metric-sub { font-size: 12px; margin-top: 4px; }
.text-yellow { color: #ffaa00; }
.text-red { color: #ff4757; }
.warning-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #233554; }
.dot-red { width: 8px; height: 8px; border-radius: 50%; background: #ff4757; box-shadow: 0 0 8px #ff4757; }
.dot-yellow { width: 8px; height: 8px; border-radius: 50%; background: #ffaa00; box-shadow: 0 0 8px #ffaa00; }
.dot-blue { width: 8px; height: 8px; border-radius: 50%; background: #1890ff; }
.warning-text { flex: 1; font-size: 13px; color: #c8d6e5; }
.warning-date { font-size: 12px; color: #8892b0; }
</style>
