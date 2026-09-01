<template>
  <div v-if="isReportView" class="dashboard">
    <div class="page-description">按月生成资产运营报告，并集中管理历史导出文件。</div>
    <div class="tech-card report-panel">
      <div class="card-title">生成月度报告</div>
        <el-space wrap>
          <el-date-picker v-model="reportMonth" type="month" placeholder="选择报告月份" value-format="YYYY-MM" :disabled-date="disableReportMonth" />
          <el-tag type="info" effect="plain">未来月份不可选</el-tag>
          <el-button type="primary" @click="genReport" :loading="genLoading">生成月度报告</el-button>
        <el-button @click="loadReports">刷新记录</el-button>
      </el-space>
        <div v-if="reportJob" class="report-job" :class="`report-job-${reportJob.status}`">
          <span>任务状态：{{ reportJobStatus }}</span>
          <el-button v-if="reportJob.status === 'queued'" link size="small" @click="cancelJob">取消</el-button>
          <el-button v-if="['failed', 'cancelled'].includes(reportJob.status)" link type="primary" size="small" @click="retryJob">重试</el-button>
          <span v-if="reportJob.error" class="report-job-error">{{ reportJob.error }}</span>
        </div>
        <div class="report-hint">可生成当月及以前月份；报告统计使用当前资产数据快照。</div>
        <div class="report-hint">AI 状态：当前月报使用规则统计生成，未调用大模型润色。</div>
      <el-divider />
      <div class="card-title">历史报告</div>
      <el-table :data="reports" size="small" max-height="480">
        <el-table-column prop="title" label="报告名称" />
        <el-table-column prop="period" label="期间" width="140" />
        <el-table-column prop="create_time" label="生成时间" width="190" />
        <el-table-column label="操作" width="100"><template #default="{ row }"><el-button type="primary" link size="small" @click="downloadReport(row)">下载</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!reports.length" description="暂无历史报告" :image-size="70" />
    </div>
  </div>
  <div v-else class="dashboard">
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
    <div class="tech-card action-panel">
      <div class="card-title action-title"><span>待我处理</span><span class="action-summary">{{ actionItems.total }} 条待办 · 高优先级 {{ actionItems.high_count }} 条</span></div>
      <div class="action-grid">
        <div v-for="item in actionItems.items" :key="item.id" class="action-item" @click="goAction(item)">
          <span class="action-dot" :class="item.priority"></span><span class="action-text">{{ item.title }}</span>
          <span v-if="item.amount" class="action-amount">节约 ¥{{ item.amount.toLocaleString() }}</span><el-button link type="primary" size="small">处理</el-button>
        </div>
        <el-empty v-if="!actionItems.items.length" description="暂无待处理事项" :image-size="50" />
      </div>
    </div>
    <div class="tech-card operations-panel">
      <div class="card-title">运营效果</div>
      <el-table :data="operationalMonths" size="small" max-height="220">
        <el-table-column prop="month" label="月份" width="100" />
        <el-table-column prop="transfer_count" label="调拨次数" width="100" />
            <el-table-column prop="idle_saving_amount" label="利旧金额" width="120" />
        <el-table-column prop="check_anomaly_rate" label="盘点异常率" width="120"><template #default="{ row }">{{ row.check_anomaly_rate }}%</template></el-table-column>
        <el-table-column prop="warning_response_rate" label="预警响应率"><template #default="{ row }">{{ row.warning_response_rate }}%</template></el-table-column>
        <el-table-column prop="scrap_compliance_rate" label="报废合规率"><template #default="{ row }">{{ row.scrap_compliance_rate }}%</template></el-table-column>
      </el-table>
    </div>
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
            <el-table-column label="下钻" width="80"><template #default="{ row }"><el-button link type="primary" size="small" @click="openDept(row)">查看</el-button></template></el-table-column>
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

    <el-drawer v-model="drillVisible" :title="drillTitle" size="620px" destroy-on-close>
      <div class="drill-summary" v-if="drillDept"><div><span>部门</span><strong>{{ drillDept.dept }}</strong></div><div><span>资产数</span><strong>{{ drillDept.count }}</strong></div><div><span>原值</span><strong>¥{{ Number(drillDept.value || 0).toLocaleString() }}</strong></div><div><span>闲置率</span><strong>{{ drillDept.idle_rate }}%</strong></div></div>
      <el-divider content-position="left">资产明细</el-divider>
      <el-table :data="drillAssets" v-loading="drillLoading" size="small" height="280" empty-text="暂无可见资产明细"><el-table-column prop="barcode" label="资产编号" min-width="140"/><el-table-column prop="asset_name" label="资产名称" min-width="150"/><el-table-column prop="state_name" label="状态" width="90"/><el-table-column prop="current_value" label="净值(元)" width="110"/></el-table>
      <el-divider content-position="left">最近操作审计</el-divider>
      <el-table :data="drillAudits" v-loading="drillLoading" size="small" height="220" empty-text="暂无审计记录"><el-table-column prop="created_at" label="时间" min-width="150"/><el-table-column prop="action" label="操作" min-width="130"/><el-table-column prop="result" label="结果" width="80"/><el-table-column prop="actor_name" label="操作人" width="100"/></el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getOverview, getActionItems, getClassDistribution, getStateDistribution, getMonthlyTrend, getOperationalEffectiveness, getDeptRanking, getWarnings, generateMonthlyReport, getReportJob, cancelReportJob, retryReportJob, getReports, queryAssets, getAuditEvents } from '@/api'
import { useUserStore } from '@/store'

const overview = ref({})
const classChart = ref()
const stateChart = ref()
const trendChart = ref()
const deptRanking = ref([])
const warnings = reactive({ list: [], total: 0 })
const actionItems = reactive({ total: 0, high_count: 0, estimated_saving: 0, items: [] })
const operationalMonths = ref([])
const drillVisible = ref(false); const drillLoading = ref(false); const drillDept = ref(null); const drillAssets = ref([]); const drillAudits = ref([])
const drillTitle = computed(() => drillDept.value ? `${drillDept.value.dept} · 运营下钻` : '运营下钻')
  const reportMonth = ref('')
const genLoading = ref(false)
const reports = ref([])
const reportJob = ref(null)
let reportJobTimer = null
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
  const isReportView = computed(() => route.meta.view === 'report')
  const disableReportMonth = (date) => date > new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0)

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
  const operational = await getOperationalEffectiveness(12)
  operationalMonths.value = operational.months || []
  deptRanking.value = await getDeptRanking()

  await nextTick()
  // 分类饼图
  echarts.init(classChart.value).setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['40%', '70%'], data: cls.slice(0, 8).map(c => ({ name: c.name, value: c.count })),
      itemStyle: { borderColor: '#ffffff', borderWidth: 2 }, label: { color: '#718198' } }]
  })
  // 状态柱状图
  echarts.init(stateChart.value).setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: states.map(s => s.name), axisLabel: { color: '#718198', rotate: 30 } },
    yAxis: { type: 'value', axisLabel: { color: '#718198' } },
    series: [{ type: 'bar', data: states.map(s => s.value), itemStyle: { color: '#1769aa' } }]
  })
  // 趋势折线图
  echarts.init(trendChart.value).setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增', '减少'], textStyle: { color: '#718198' } },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: trend.map(t => t.month), axisLabel: { color: '#718198' } },
    yAxis: { type: 'value', axisLabel: { color: '#718198' } },
    series: [
      { name: '新增', type: 'line', smooth: true, data: trend.map(t => t.added), itemStyle: { color: '#198f6b' }, areaStyle: { opacity: 0.12 } },
      { name: '减少', type: 'line', smooth: true, data: trend.map(t => t.reduced), itemStyle: { color: '#c84b54' }, areaStyle: { opacity: 0.12 } },
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
    reportJob.value = await generateMonthlyReport(parseInt(y), parseInt(m))
    pollReportJob()
  } finally { genLoading.value = false }
}

const reportJobStatus = computed(() => ({ queued: '排队中', running: '生成中', succeeded: '已完成', failed: '失败', cancelled: '已取消' })[reportJob.value?.status] || '-')
const clearReportJobTimer = () => { if (reportJobTimer) { clearTimeout(reportJobTimer); reportJobTimer = null } }
const pollReportJob = async () => {
  clearReportJobTimer()
  if (!reportJob.value?.job_id) return
  try {
    reportJob.value = await getReportJob(reportJob.value.job_id)
    if (reportJob.value.status === 'succeeded') { ElMessage.success('报告生成成功'); loadReports(); return }
    if (['failed', 'cancelled'].includes(reportJob.value.status)) return
    reportJobTimer = setTimeout(pollReportJob, 1200)
  } catch (error) { ElMessage.error('获取报告任务状态失败') }
}
const cancelJob = async () => { reportJob.value = await cancelReportJob(reportJob.value.job_id); clearReportJobTimer() }
const retryJob = async () => { reportJob.value = await retryReportJob(reportJob.value.job_id); pollReportJob() }

const loadReports = async () => {
  const res = await getReports({ size: 10 })
  reports.value = res.list
}

  const downloadReport = async (row) => {
    const filename = String(row.file_path || '').split(/[\\/]/).pop()
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`/api/dashboard/reports/id/${encodeURIComponent(row.id)}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      if (!response.ok) throw new Error(response.status === 401 ? '登录已过期，请重新登录' : '报告下载失败')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url)
    } catch (error) { ElMessage.error(error.message) }
  }

const loadActionItems = async () => Object.assign(actionItems, await getActionItems())
const goAction = item => router.push(item.link)
const openDept = async (row) => {
  drillDept.value = row; drillVisible.value = true; drillLoading.value = true
  try {
    const assetsPromise = queryAssets({ dept_id: row.dept_id, page: 1, size: 20 })
    const auditsPromise = userStore.user?.is_admin == 1 ? getAuditEvents({ page: 1, size: 20 }) : Promise.resolve({ list: [] })
    const [assets, audits] = await Promise.all([assetsPromise, auditsPromise])
    drillAssets.value = assets.list || []; drillAudits.value = audits.list || []
  } catch { drillAssets.value = []; drillAudits.value = [] } finally { drillLoading.value = false }
}
const loadView = () => {
  if (isReportView.value) { loadReports(); if (reportJob.value && !['succeeded', 'failed', 'cancelled'].includes(reportJob.value.status)) pollReportJob() }
  else { loadData(); loadWarnings(); loadActionItems() }
}
onMounted(loadView)
watch(isReportView, loadView)
</script>

<style scoped>
.metric-row { margin-bottom: 0; }
.action-panel { margin-top: 16px; }
.operations-panel { margin-top: 16px; }
.action-title { display:flex; justify-content:space-between; align-items:center; }
.action-summary { color:#718198; font-size:12px; font-weight:400; }
.action-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 24px; }
.action-item { display:flex; align-items:center; gap:8px; min-height:36px; padding:6px 0; border-bottom:1px solid #e8eef5; cursor:pointer; }
.action-dot { width:8px; height:8px; flex:0 0 8px; border-radius:50%; background:#1769aa; }.action-dot.high { background:#c84b54; }.action-dot.medium { background:#c98516; }
.action-text { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#354965; font-size:13px; }.action-amount { color:#198f6b; font-size:12px; white-space:nowrap; }
.card-title { font-size: 16px; font-weight: 650; color: #20334d; margin-bottom: 12px; border-left: 3px solid #1769aa; padding-left: 10px; }
  .page-description { margin: 0 0 18px; color: #718198; font-size: 13px; }.report-panel { max-width: 980px; }.report-hint { margin-top: 8px; color: #8795a8; font-size: 12px; }.report-job { display:flex; align-items:center; gap:8px; margin-top:10px; font-size:12px; color:#718198; }.report-job-running { color:#1769aa; }.report-job-failed { color:#c84b54; }.report-job-error { max-width:420px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.metric-sub { font-size: 12px; margin-top: 4px; }
.text-yellow { color: #b7791f; }.text-red { color: #c84b54; }
.warning-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #e8eef5; }.dot-red { width: 8px; height: 8px; border-radius: 50%; background: #c84b54; }.dot-yellow { width: 8px; height: 8px; border-radius: 50%; background: #d99a23; }.dot-blue { width: 8px; height: 8px; border-radius: 50%; background: #1769aa; }.warning-text { flex: 1; font-size: 13px; color: #354965; }.warning-date { font-size: 12px; color: #718198; }
.drill-summary { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; padding:12px; background:#f6f9fc; border:1px solid #e2eaf2; border-radius:8px; }.drill-summary span,.drill-summary strong { display:block; }.drill-summary span { color:#8191a7; font-size:12px; }.drill-summary strong { margin-top:4px; color:#20334d; font-size:16px; }
@media (max-width: 900px) { .action-grid { grid-template-columns: 1fr; } .action-summary { display: none; } }
</style>
