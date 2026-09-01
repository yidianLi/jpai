<template>
  <div>
    <div class="page-description">{{ isQualityView ? '定位异常资产，优先处理影响盘点、折旧和决策的数据问题。' : '检索资产后查看完整身份信息、价值信息和流转记录。' }}</div>
    <el-row v-if="isQualityView" :gutter="16">
      <el-col :span="24">
        <div class="tech-card">
          <div class="card-title">质量概览</div>
          <el-row :gutter="16">
            <el-col :span="8"><div class="metric-card"><div class="metric-value">{{ dq.abnormal }}</div><div class="metric-label">异常数据</div></div></el-col>
            <el-col :span="8"><div class="metric-card"><div class="metric-value metric-warning">{{ dq.abnormal_rate }}%</div><div class="metric-label">异常率</div></div></el-col>
            <el-col :span="8"><div class="metric-card"><div class="metric-value metric-success">{{ dq.avg_quality_score }}</div><div class="metric-label">平均质量分</div></div></el-col>
          </el-row>
        </div>
        <div class="tech-card" style="margin-top:16px;">
          <div class="card-title">待处理异常资产</div>
          <el-table :data="abnormalList" size="small" max-height="520">
            <el-table-column prop="barcode" label="编号" width="160" />
            <el-table-column prop="asset_name" label="名称" />
            <el-table-column prop="dept_name" label="部门" width="160" />
            <el-table-column prop="data_quality_score" label="质量分" width="100" />
            <el-table-column label="操作" width="100"><template #default="{ row }"><el-button type="primary" link size="small" @click="openAsset(row)">查看档案</el-button></template></el-table-column>
          </el-table>
          <el-empty v-if="!abnormalList.length" description="暂无异常资产" :image-size="70" />
        </div>
      </el-col>
    </el-row>
    <el-row v-else :gutter="16">
      <el-col :span="10">
        <div class="tech-card">
          <div class="card-title">资产检索</div>
          <el-input v-model="keyword" placeholder="输入资产编号/名称搜索" clearable @keyup.enter="search">
            <template #append><el-button @click="search">搜索</el-button></template>
          </el-input>
          <el-table :data="searchResults" size="small" style="margin-top:12px;max-height:500px;overflow:auto;" highlight-current-row @row-click="selectAsset">
            <el-table-column prop="barcode" label="编号" width="150" />
            <el-table-column prop="asset_name" label="名称" />
            <el-table-column prop="dept_name" label="部门" width="100" />
            <el-table-column prop="state_name" label="状态" width="80" />
          </el-table>
          <el-pagination style="margin-top:10px;justify-content:flex-end;display:flex;" background layout="total, prev, pager, next" :total="searchTotal" :page-size="10" :current-page="searchPage" @current-change="p => {searchPage=p;search()}" />
        </div>
      </el-col>
      <el-col :span="14">
        <div class="tech-card" v-if="asset">
          <div class="card-title">资产身份证 #{{ asset.basic.barcode }}</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="资产名称">{{ asset.basic.asset_name }}</el-descriptions-item>
            <el-descriptions-item label="型号">{{ asset.basic.model || '-' }}</el-descriptions-item>
            <el-descriptions-item label="品牌">{{ asset.basic.brand || '-' }}</el-descriptions-item>
            <el-descriptions-item label="序列号">{{ asset.basic.sn || '-' }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ asset.basic.class_path || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ asset.basic.state_name }}</el-descriptions-item>
            <el-descriptions-item label="使用单位">{{ asset.basic.company_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="使用部门">{{ asset.basic.dept_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="责任人">{{ asset.basic.responsible || '-' }}</el-descriptions-item>
            <el-descriptions-item label="使用人">{{ asset.basic.user_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="存放位置">{{ asset.basic.position || '-' }}</el-descriptions-item>
            <el-descriptions-item label="供应商">{{ asset.basic.supplier_name || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-divider />
          <div class="card-title">价值信息</div>
          <el-descriptions :column="4" border size="small">
            <el-descriptions-item label="购置原值">¥{{ asset.value.buy_price?.toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="购置日期">{{ asset.value.buy_date }}</el-descriptions-item>
            <el-descriptions-item label="使用年限">{{ asset.value.use_year }}年</el-descriptions-item>
            <el-descriptions-item label="当前净值">¥{{ asset.value.current_value?.toLocaleString() }}</el-descriptions-item>
          </el-descriptions>
          <el-divider />
          <div class="card-title">流转时间轴（{{ asset.stats.transfer_count }}次）</div>
          <el-timeline>
            <el-timeline-item v-for="(t, i) in asset.timeline" :key="i" :timestamp="t.date" placement="top" :type="i==0?'primary':''">
              <div style="font-weight:bold;color:#20334d;">{{ t.type }}</div>
              <div style="font-size:12px;color:#62748c;">工单号: {{ t.bill_no }} | 经办人: {{ t.handler || '-' }}</div>
              <div v-if="t.fee" style="font-size:12px;color:#a96b0d;">费用: ¥{{ t.fee }}</div>
            </el-timeline-item>
          </el-timeline>
          <el-divider v-if="asset.check_history?.length" />
          <div class="card-title" v-if="asset.check_history?.length">盘点记录（{{ asset.stats.check_count }}次）</div>
          <el-table :data="asset.check_history" size="small" v-if="asset.check_history?.length">
            <el-table-column prop="date" label="盘点日期" width="140" />
            <el-table-column label="结果" width="80">
              <template #default="{ row }"><span :class="row.state=='正常'?'tag-green':'tag-red'">{{ row.state }}</span></template>
            </el-table-column>
            <el-table-column prop="position" label="盘点位置" />
          </el-table>
        </div>
        <div class="tech-card" v-else style="text-align:center;padding:80px;color:#62748c;">
          <el-icon :size="48"><Files /></el-icon>
          <div style="margin-top:12px;">请从左侧选择资产查看详情</div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Files } from '@element-plus/icons-vue'
import { queryAssets, getAssetDetail, getDataQuality, getAbnormalAssets, getQualityIssues, actionQualityIssue } from '@/api'

const keyword = ref('')
const searchResults = ref([])
const searchTotal = ref(0)
const searchPage = ref(1)
const asset = ref(null)
const dq = ref({})
const abnormalList = ref([])
const qualityIssues = ref([])
const issueStatus = ref('')
const route = useRoute()
const isQualityView = computed(() => route.meta.view === 'quality')

const search = async () => {
  const res = await queryAssets({ keyword: keyword.value || undefined, page: searchPage.value, size: 10 })
  searchResults.value = res.list
  searchTotal.value = res.total
}
const selectAsset = async (row) => {
  asset.value = await getAssetDetail(row.asset_id)
}
const openAsset = row => { window.location.assign(`/lifecycle?id=${row.asset_id}`) }
const loadDQ = async () => { dq.value = await getDataQuality() }
const loadAbnormal = async () => {
  const res = await getAbnormalAssets({ size: 20 })
  abnormalList.value = res.list
}
const loadIssues = async () => { const res = await getQualityIssues({ status: issueStatus.value || undefined, size: 50 }); qualityIssues.value = res.list || [] }
const issueAction = async (row, action) => { await actionQualityIssue(row.id, action, { remark: action === 'fix' ? '已完成数据修复，待复核' : undefined }); await loadIssues(); await loadDQ() }
onMounted(async () => {
  await search()
  const requestedId = Number(route.query.id)
  const initialAsset = requestedId
    ? searchResults.value.find(item => item.asset_id === requestedId)
    : searchResults.value[0]
  if (initialAsset) await selectAsset(initialAsset)
  loadDQ(); loadAbnormal(); loadIssues()
})
</script>

<style scoped>
.page-description { margin: 0 0 18px; color: #718198; font-size: 13px; }.card-title { font-size: 16px; font-weight: 650; color: #20334d; margin-bottom: 12px; border-left: 3px solid #1769aa; padding-left: 10px; }.metric-warning { color: #b7791f; }.metric-success { color: #198f6b; }
:deep(.el-descriptions__label) { background: #f5f8fb !important; color: #62748c !important; width: 100px; }:deep(.el-descriptions__content) { color: #20334d !important; }
</style>
