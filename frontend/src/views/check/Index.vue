<template>
  <div>
    <div class="page-title">智能盘点分析</div>
    <el-row :gutter="16">
      <el-col :span="8">
        <div class="tech-card">
          <div class="card-title">盘点任务</div>
          <div v-for="t in tasks" :key="t.check_bid" class="task-item" :class="{active: currentBid == t.check_bid}" @click="selectTask(t)">
            <div class="task-title">{{ t.title || `盘点#${t.check_bid}` }}</div>
            <div class="task-meta">{{ t.date }} · 共{{ t.total }}台</div>
            <div class="task-stats">
              <span class="tag-green">正常{{ t.normal }}</span>
              <span class="tag-red">盘亏{{ t.loss }}</span>
              <span class="tag-yellow">不符{{ t.mismatch }}</span>
              <span class="tag-blue">相符率{{ t.match_rate }}%</span>
            </div>
          </div>
          <el-empty v-if="!tasks.length" description="暂无盘点任务" :image-size="60" />
        </div>
      </el-col>
      <el-col :span="16">
        <div class="tech-card" v-if="diagnosis">
          <div class="card-title">盘点结果智能诊断</div>
          <el-row :gutter="16">
            <el-col :span="6"><div class="metric-card"><div class="metric-value">{{ diagnosis.total }}</div><div class="metric-label">应盘总数</div></div></el-col>
            <el-col :span="6"><div class="metric-card"><div class="metric-value" style="color:#00d4aa">{{ diagnosis.normal }}</div><div class="metric-label">账实相符</div></div></el-col>
            <el-col :span="6"><div class="metric-card"><div class="metric-value" style="color:#ff4757">{{ diagnosis.loss }}</div><div class="metric-label">盘亏</div></div></el-col>
            <el-col :span="6"><div class="metric-card"><div class="metric-value" style="color:#ffaa00">{{ diagnosis.match_rate }}%</div><div class="metric-label">相符率</div></div></el-col>
          </el-row>
          <el-divider />
          <div class="card-title">整改建议</div>
          <div v-for="(s, i) in diagnosis.suggestions" :key="i" class="suggestion">{{ i+1 }}. {{ s }}</div>
          <el-divider v-if="diagnosis.high_value_loss?.length" />
          <div class="card-title" v-if="diagnosis.high_value_loss?.length">高价值盘亏资产</div>
          <el-table :data="diagnosis.high_value_loss" size="small" v-if="diagnosis.high_value_loss?.length">
            <el-table-column prop="asset_name" label="资产名称" />
            <el-table-column prop="barcode" label="编号" width="160" />
            <el-table-column prop="buy_price" label="原值(元)" width="120" />
            <el-table-column prop="dept" label="部门" />
          </el-table>
        </div>
        <div class="tech-card" v-else style="text-align:center;padding:60px;color:#8892b0;">
          请从左侧选择盘点任务查看诊断结果
        </div>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top:16px;" v-if="currentBid">
      <el-col :span="24">
        <div class="tech-card">
          <div class="card-title" style="display:flex;justify-content:space-between;">
            <span>盘点明细</span>
            <el-radio-group v-model="filterState" size="small" @change="loadDetail">
              <el-radio-button :value="null">全部</el-radio-button>
              <el-radio-button :value="1">正常</el-radio-button>
              <el-radio-button :value="2">盘亏</el-radio-button>
              <el-radio-button :value="3">不符</el-radio-button>
            </el-radio-group>
          </div>
          <el-table :data="detail.list" size="small" max-height="400">
            <el-table-column prop="barcode" label="资产编号" width="160" />
            <el-table-column label="盘点结果" width="80">
              <template #default="{ row }"><span :class="row.check_state==1?'tag-green':row.check_state==2?'tag-red':'tag-yellow'">{{ row.state_text }}</span></template>
            </el-table-column>
            <el-table-column prop="old_dept" label="原部门" width="120" />
            <el-table-column prop="new_dept" label="盘点部门" width="120" />
            <el-table-column prop="old_position" label="原位置" />
            <el-table-column prop="new_position" label="盘点位置" />
            <el-table-column prop="old_responsible" label="原责任人" width="100" />
          </el-table>
          <el-pagination style="margin-top:12px;justify-content:flex-end;display:flex;" background layout="total, prev, pager, next" :total="detail.total" :page-size="20" :current-page="detail.page" @current-change="p => {detail.page=p;loadDetail()}" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { getCheckTasks, getCheckDetail, getCheckDiagnosis } from '@/api'

const tasks = ref([])
const currentBid = ref(null)
const diagnosis = ref(null)
const detail = reactive({ list: [], total: 0, page: 1 })
const filterState = ref(null)

const loadTasks = async () => { tasks.value = await getCheckTasks() }
const selectTask = async (t) => {
  currentBid.value = t.check_bid
  diagnosis.value = await getCheckDiagnosis(t.check_bid)
  detail.page = 1
  loadDetail()
}
const loadDetail = async () => {
  const res = await getCheckDetail(currentBid.value, { state: filterState.value, page: detail.page, size: 20 })
  detail.list = res.list
  detail.total = res.total
}
loadTasks()
</script>

<style scoped>
.card-title { font-size: 16px; font-weight: bold; color: #e6f1ff; margin-bottom: 12px; border-left: 3px solid #1890ff; padding-left: 10px; }
.task-item { padding: 14px; border: 1px solid #233554; border-radius: 6px; margin-bottom: 10px; cursor: pointer; transition: all 0.3s; }
.task-item:hover, .task-item.active { border-color: #1890ff; background: rgba(24,144,255,0.1); }
.task-title { font-weight: bold; color: #e6f1ff; margin-bottom: 4px; }
.task-meta { font-size: 12px; color: #8892b0; margin-bottom: 8px; }
.task-stats { display: flex; gap: 6px; flex-wrap: wrap; }
.suggestion { padding: 6px 0; color: #c8d6e5; font-size: 14px; }
</style>
