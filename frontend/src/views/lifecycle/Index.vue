<template>
  <div>
    <div class="page-title">资产全生命周期档案</div>
    <el-row :gutter="16">
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
        <div class="tech-card" style="margin-top:16px;">
          <div class="card-title">数据质量</div>
          <el-row :gutter="12">
            <el-col :span="8"><div class="metric-card"><div class="metric-value">{{ dq.abnormal }}</div><div class="metric-label">异常数据</div></div></el-col>
            <el-col :span="8"><div class="metric-card"><div class="metric-value" style="color:#ffaa00">{{ dq.abnormal_rate }}%</div><div class="metric-label">异常率</div></div></el-col>
            <el-col :span="8"><div class="metric-card"><div class="metric-value" style="color:#00d4aa">{{ dq.avg_quality_score }}</div><div class="metric-label">平均质量分</div></div></el-col>
          </el-row>
          <el-button type="primary" size="small" style="margin-top:12px;" @click="showAbnormal = !showAbnormal">查看异常资产</el-button>
          <el-table :data="abnormalList" size="small" style="margin-top:12px;" v-if="showAbnormal" max-height="200">
            <el-table-column prop="barcode" label="编号" width="140" />
            <el-table-column prop="asset_name" label="名称" />
            <el-table-column prop="data_quality_score" label="质量分" width="80" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }"><el-button type="primary" link size="small" @click="selectAsset(row)">清洗</el-button></template>
            </el-table-column>
          </el-table>
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
              <div style="font-weight:bold;color:#e6f1ff;">{{ t.type }}</div>
              <div style="font-size:12px;color:#8892b0;">工单号: {{ t.bill_no }} | 经办人: {{ t.handler || '-' }}</div>
              <div v-if="t.fee" style="font-size:12px;color:#ffaa00;">费用: ¥{{ t.fee }}</div>
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
        <div class="tech-card" v-else style="text-align:center;padding:80px;color:#8892b0;">
          <el-icon :size="48"><Files /></el-icon>
          <div style="margin-top:12px;">请从左侧选择资产查看详情</div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Files } from '@element-plus/icons-vue'
import { queryAssets, getAssetDetail, getDataQuality, getAbnormalAssets } from '@/api'

const keyword = ref('')
const searchResults = ref([])
const searchTotal = ref(0)
const searchPage = ref(1)
const asset = ref(null)
const dq = ref({})
const abnormalList = ref([])
const showAbnormal = ref(false)

const search = async () => {
  const res = await queryAssets({ keyword: keyword.value || undefined, page: searchPage.value, size: 10 })
  searchResults.value = res.list
  searchTotal.value = res.total
}
const selectAsset = async (row) => {
  asset.value = await getAssetDetail(row.asset_id)
}
const loadDQ = async () => { dq.value = await getDataQuality() }
const loadAbnormal = async () => {
  const res = await getAbnormalAssets({ size: 20 })
  abnormalList.value = res.list
}
onMounted(() => { search(); loadDQ(); loadAbnormal() })
</script>

<style scoped>
.card-title { font-size: 16px; font-weight: bold; color: #e6f1ff; margin-bottom: 12px; border-left: 3px solid #1890ff; padding-left: 10px; }
:deep(.el-descriptions__label) { background: #1a2a4a !important; color: #8892b0 !important; width: 100px; }
:deep(.el-descriptions__content) { color: #e6f1ff !important; }
</style>
