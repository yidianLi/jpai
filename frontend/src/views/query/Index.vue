<template>
  <div>
    <div class="page-description">{{ pageDescription }}</div>

    <!-- 自然语言查询 -->
    <div v-if="isNlView" class="tech-card" style="margin-bottom:16px;">
      <div class="card-title">AI自然语言查询 <span class="tag-blue" style="margin-left:8px;">{{ aiStatusText }}</span></div>
      <aside class="ai-process-panel"><div class="ai-panel-title">执行过程</div><div class="ai-step active"><b>{{ nlLoading ? '正在分析' : nlAnswer ? '已完成回答' : '等待提问' }}</b><span>{{ nlLoading ? '正在识别问题并查询数据' : '选择任务或输入问题' }}</span></div><div class="ai-panel-title feedback-title">反馈纠正</div><p>不满意时请选择问题类型并提交反馈。</p><el-select v-model="feedbackType" size="small" placeholder="选择问题类型" style="width:100%;margin-bottom:10px"><el-option label="回答不准确" value="accuracy"/><el-option label="没有回答问题" value="relevance"/><el-option label="数据不完整" value="data"/></el-select><el-button size="small" type="primary" plain @click="submitFeedback">提交反馈</el-button><el-button size="small" plain @click="nlAnswer && ElMessage.success('已保存到知识库')">▣ 保存入知识库</el-button></aside>
      <div class="nl-search">
        <el-input v-model="nlInput" class="nl-input" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" placeholder="例如：办公室有多少台闲置的笔记本电脑？" size="large" @keyup.enter="doNlQuery">
          <template #prefix><el-icon><ChatDotRound /></el-icon></template>
          <template #append><el-button type="primary" @click="doNlQuery" :loading="nlLoading">查询</el-button></template>
        </el-input>
      </div>
      <div class="nl-tools"><input ref="fileInput" type="file" accept=".csv,.xlsx" hidden @change="handleFileUpload"><el-button size="small" @click="fileInput?.click()">上传资产文件</el-button><span v-if="importPreview">已识别 {{ importPreview.rows }} 条，匹配 {{ Object.keys(importPreview.mapping).length }} 个字段</span><el-button v-if="importPreview" size="small" type="success" @click="commitImport">确认写入资产库</el-button></div>
      <div class="nl-history" v-if="nlHistory.length">
        <div class="nl-history-head"><span>历史问答</span><el-button link size="small" @click="clearNlHistory">清空</el-button></div>
        <div v-for="(item, index) in nlHistory" :key="item.id" class="nl-history-item">
          <button type="button" class="nl-history-question" @click="restoreHistory(item)"><strong>{{ item.query || item.question || item.title }}</strong><small>{{ item.answer || '已记录问题' }}</small></button>
          <el-button link type="danger" size="small" @click="removeNlHistory(index)">删除</el-button>
        </div>
      </div>
      <div v-if="nlAnswer" class="nl-answer" style="margin-top:12px;"><div class="nl-question-bubble">{{ lastQuestion }}</div>
        <div style="color:#1769aa;font-weight:bold;margin-bottom:6px;">AI回答</div>
        <div>{{ nlAnswer.answer }}</div>
        <div v-if="nlAnswer.filters" class="answer-meta">
          识别意图: {{ nlAnswer.intent }} | 筛选条件: {{ JSON.stringify(nlAnswer.filters) }}
        </div>
        <div class="answer-meta">{{ nlAnswer.ai_used ? `已由 ${nlAnswer.provider} / ${nlAnswer.model} 理解问题并执行受控数据查询` : '模型未返回有效结构化结果，已使用本地受控规则完成查询' }}</div>
      </div>
      <div v-else class="nl-empty-state"><div class="nl-empty-icon">AI</div><h3>准备好回答你的问题</h3><p>请直接输入资产、采购、盘活或数据分析问题，也可以从下方快捷入口开始。</p></div>
      <div style="margin-top:12px;">
        <div class="shortcut-tabs" role="tablist" aria-label="AI快捷入口">
          <button v-for="group in shortcutGroups" :key="group.key" type="button" class="shortcut-tab" :class="{ active: shortcutGroup === group.key }" @click="shortcutGroup = group.key">
            {{ group.label }}<span>{{ group.entries.length }}</span>
          </button>
          <button type="button" class="shortcut-customize" @click="customDialogVisible = true">+ 自定义</button>
        </div>
        <div class="shortcut-entry-tabs">
          <button v-for="entry in activeShortcutGroup.entries" :key="entry.key" type="button" class="shortcut-entry" :class="{ active: shortcutEntry === entry.key }" @click="shortcutEntry = entry.key">{{ entry.label }}</button>
        </div>
        <div class="shortcut-items">
          <button v-for="item in activeShortcutItems" :key="item.label" type="button" class="shortcut-item" @click="handleShortcut(item)">
            <span class="shortcut-item-title">{{ item.label }}</span><small>{{ item.hint }}</small>
            <i v-if="item.custom" class="shortcut-remove" title="删除自定义快捷项" @click.stop="removeCustomShortcut(item)">×</i>
          </button>
        </div>
      </div>
    </div>

    <el-dialog v-model="customDialogVisible" title="自定义常用问题" width="420px">
      <el-form label-position="top" size="small">
        <el-form-item label="业务入口名称"><el-input v-model="customForm.entry" maxlength="20" placeholder="例如：我的运营分析" /></el-form-item>
        <el-form-item label="具体问题名称"><el-input v-model="customForm.label" maxlength="40" placeholder="例如：本月高价值闲置资产" /></el-form-item>
        <el-form-item label="问题说明"><el-input v-model="customForm.hint" maxlength="30" placeholder="例如：重点关注" /></el-form-item>
        <el-form-item label="默认提问内容"><el-input v-model="customForm.prompt" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="点击快捷项时提交给 AI 的问题" /></el-form-item>
        <el-form-item label="数据源表"><el-select v-model="customForm.table" placeholder="选择业务数据表" style="width:100%"><el-option label="资产表 ai_asset" value="ai_asset" /><el-option label="用户表 ai_user" value="ai_user" /><el-option label="部门表 ai_department" value="ai_department" /></el-select></el-form-item>
        <el-form-item label="匹配字段"><el-input v-model="customForm.fields" placeholder="例如：资产名称、品牌、型号" /><el-button size="small" style="margin-top:8px" @click="smartMatchFields">智能匹配字段</el-button></el-form-item>
      </el-form>
      <template #footer><el-button @click="customDialogVisible = false">取消</el-button><el-button type="primary" @click="saveCustomShortcut">保存</el-button></template>
    </el-dialog>

    <!-- 多维度筛选 -->
    <div v-if="isFilterView" class="tech-card" style="margin-bottom:16px;">
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
    <div v-if="isFilterView && (totalReady || results.length)" class="tech-card">
      <div class="result-heading"><div class="card-title">{{ resultTitle }}</div><span v-if="isProgressiveLoading" class="preview-state">首屏预览已就绪，正在补全</span></div>
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
      <el-pagination v-if="totalReady" style="margin-top:12px;justify-content:flex-end;display:flex;" background layout="total, prev, pager, next" :total="total" :page-size="20" :current-page="page" @current-change="p => {page=p;doQuery()}" />
    </div>

    <!-- 采购预测 -->
    <div v-if="isForecastView" class="tech-card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
          <span>采购需求预测（规则驱动+移动平均）</span>
          <el-space><span class="forecast-label">预测周期</span><el-select v-model="forecastMonths" size="small" style="width:110px"><el-option :value="3" label="未来3个月"/><el-option :value="6" label="未来6个月"/><el-option :value="12" label="未来12个月"/></el-select><el-select v-model="forecastSort" size="small" style="width:130px"><el-option value="forecast_qty" label="按预测量"/><el-option value="class_name" label="按采购对象"/><el-option value="category_path" label="按分类路径"/></el-select><el-button size="small" @click="forecastDesc=!forecastDesc">{{ forecastDesc ? '降序' : '升序' }}</el-button><el-button type="primary" size="small" @click="runForecast">重新计算</el-button></el-space>
      </div>
      <el-empty v-if="!forecast.length" description="暂无预测结果，请选择周期后点击重新计算" :image-size="70" />
      <el-table v-else :data="forecastDisplay" size="small">
          <el-table-column label="采购对象" min-width="260"><template #default="{row}"><strong>{{ row.class_name }}</strong><small class="category-parent">{{ row.category_path }}</small></template></el-table-column>
          <el-table-column prop="forecast_qty" label="预测需求量" width="140" />
        <el-table-column prop="basis" label="预测依据" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { queryAssets, nlQuery, importAssetFile, getForecast, computeForecast, getDepartments, getAssetClasses, getAssetStates, getLlmStatus } from '@/api'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const pageMode = computed(() => route.meta.view || 'nl')
const isNlView = computed(() => pageMode.value === 'nl')
const isFilterView = computed(() => pageMode.value === 'filter')
const isForecastView = computed(() => pageMode.value === 'forecast')
const pageTitle = computed(() => isNlView.value ? '自然语言问答' : isFilterView.value ? '资产条件筛选' : '采购需求预测')
const pageDescription = computed(() => isNlView.value ? '使用自然语言快速获取资产运营数据和洞察。' : isFilterView.value ? '按资产属性、状态、部门和价值区间定位目标资产。' : '基于资产类别与历史规律，为采购计划提供参考。')
const nlInput = ref('')
const nlLoading = ref(false)
const nlAnswer = ref(null)
const nlHistory = ref([])
const lastQuestion = ref('')
const feedbackType = ref('')
const aiStatus = ref({ enabled: false, provider: '', model: '', configured: false })
const aiStatusText = computed(() => !aiStatus.value.enabled ? 'AI 未启用' : !aiStatus.value.configured ? 'AI 密钥未配置' : `线上 ${aiStatus.value.provider} · ${aiStatus.value.model}`)
const shortcutGroup = ref('query')
const shortcutEntry = ref('asset')
const customDialogVisible = ref(false)
const customForm = reactive({ entry: '', label: '', hint: '', prompt: '', table: 'ai_asset', fields: '' })
const fileInput = ref(null)
const importPreview = ref(null)
const importFile = ref(null)
const customShortcuts = ref([])
const shortcutGroups = [
  { key: 'import', label: '导入', entries: [
    { key: 'asset', label: '资产台账', items: [{ label: '导入资产数据', hint: '资产台账同步', path: '/system' }, { label: '资产数据是否最新？', hint: '同步状态', prompt: '请检查最近一次资产台账同步状态' }] },
    { key: 'org', label: '组织架构', items: [{ label: '导入组织架构', hint: '部门与用户同步', path: '/system' }, { label: '在职账号有多少？', hint: '人员统计', prompt: '当前在职账号有多少，分别属于哪些部门' }] },
    { key: 'dict', label: '基础字典', items: [{ label: '导入字典数据', hint: '分类与状态同步', path: '/system' }, { label: '资产分类是否完整？', hint: '数据质量', prompt: '请检查资产分类字典和末级分类完整性' }] },
    { key: 'flow', label: '流转记录', items: [{ label: '导入流转记录', hint: '调拨与维修记录', path: '/system' }, { label: '最近有哪些维修记录？', hint: '维修数据', prompt: '请统计最近的维修记录和维修费用' }] },
  ] },
  { key: 'query', label: '查询', entries: [
    { key: 'asset', label: '资产台账', items: [{ label: '资产总量与价值', hint: '经营总览', prompt: '资产总量和当前总价值是多少' }, { label: '条件筛选资产', hint: '多维条件检索', path: '/query/filter' }] },
    { key: 'operation', label: '资产运营', items: [{ label: '闲置资产清单', hint: '盘活候选', prompt: '目前有多少闲置资产，价值多少' }, { label: '哪个部门资产最多？', hint: '部门排名', prompt: '哪个部门资产最多' }, { label: '即将到期资产', hint: '报废预警', prompt: '有哪些资产即将到期' }] },
    { key: 'purchase', label: '采购决策', items: [{ label: '品牌与型号表现', hint: '采购决策分析', path: '/insight/brands' }, { label: '采购需求预测', hint: '需求趋势', path: '/procurement/forecast' }, { label: '未来需要采购什么？', hint: '采购建议', prompt: '未来需要采购哪些具体类别的资产' }] },
    { key: 'lifecycle', label: '生命周期', items: [{ label: '资产全生命周期档案', hint: '资产身份证', path: '/lifecycle' }, { label: '哪些资产需要报废？', hint: '处置评估', prompt: '哪些资产已达到报废条件' }] },
  ] },
  { key: 'common', label: '常用', entries: [
    { key: 'custom', label: '我的快捷', items: [] },
    { key: 'statistics', label: '常用统计', items: [{ label: '今年新增了多少资产？', hint: '年度趋势', prompt: '今年新增了多少资产' }, { label: '各部门资产价值排名', hint: '部门分析', prompt: '请按部门统计资产数量和资产价值排名' }] },
    { key: 'decision', label: '管理建议', items: [{ label: '哪些资产可以盘活？', hint: '闲置调拨建议', prompt: '哪些闲置资产适合内部调拨' }, { label: '哪些品牌维修成本低？', hint: '品牌分析', prompt: '哪些品牌维修成本低且样本量充足' }] },
    { key: 'quality', label: '数据质量', items: [{ label: '哪些资产信息不完整？', hint: '质量检查', prompt: '哪些资产缺少部门、位置或使用人信息' }, { label: '账实相符率是多少？', hint: '盘点分析', prompt: '当前资产账实相符率是多少' }] },
  ] },
]
const activeShortcutGroup = computed(() => shortcutGroups.find(group => group.key === shortcutGroup.value) || shortcutGroups[0])
const activeShortcutEntry = computed(() => activeShortcutGroup.value.entries.find(entry => entry.key === shortcutEntry.value) || activeShortcutGroup.value.entries[0])
watch(shortcutGroup, () => { shortcutEntry.value = activeShortcutGroup.value.entries[0]?.key || '' })
const activeShortcutItems = computed(() => activeShortcutEntry.value?.key?.startsWith('custom-') ? customShortcuts.value.filter(item => item.entryKey === activeShortcutEntry.value.key) : activeShortcutEntry.value?.items || [])
const filter = reactive({ keyword: '', class_id: null, state_id: null, dept_id: null, is_idle: null, min_price: null, max_price: null })
const results = ref([])
const total = ref(0)
const totalReady = ref(false)
const isProgressiveLoading = ref(false)
const page = ref(1)
  const forecast = ref([])
  const forecastMonths = ref(6)
  const forecastSort = ref('forecast_qty')
  const forecastDesc = ref(true)
  const forecastTree = computed(() => {
    const roots = []
    const index = new Map()
    for (const item of forecast.value) {
      const parts = (item.class_name || '未分类').split(' > ')
      let parent = null
      parts.forEach((part, i) => {
        const key = parts.slice(0, i + 1).join(' > ')
        let node = index.get(key)
        if (!node) {
          node = { key, class_name: part, forecast_qty: 0, basis: i === parts.length - 1 ? item.basis : '分类汇总', children: [] }
          index.set(key)
          parent ? parent.children.push(node) : roots.push(node)
        }
        if (i === parts.length - 1) node.forecast_qty += Number(item.forecast_qty || 0)
        parent = node
      })
    }
    const clean = nodes => nodes.map(n => { if (n.children.length) { n.children = clean(n.children); n.forecast_qty = n.children.reduce((s, c) => s + c.forecast_qty, 0) } else delete n.children; return n })
    return clean(roots)
  })
  const forecastDisplay = computed(() => {
    const rows = forecast.value.map(item => { const parts = (item.class_name || '未分类').split(' > '); return { ...item, class_name: parts[parts.length - 1], category_path: parts.length > 1 ? parts.slice(0, -1).join(' > ') : '一级分类' } })
    return rows.sort((a, b) => { const av = a[forecastSort.value], bv = b[forecastSort.value]; const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv), 'zh-CN'); return forecastDesc.value ? -cmp : cmp })
  })
const classes = ref([])
const states = ref([])
const depts = ref([])
  let querySequence = 0
  let queryController = null
let progressiveTimer = null
const resultTitle = computed(() => totalReady.value ? `查询结果（共${total.value}条）` : '查询结果（首屏预览）')

const doNlQuery = async () => {
  if (!nlInput.value) return
  const question = nlInput.value.trim()
  if (!question) return
  nlLoading.value = true
  try {
    lastQuestion.value = question
    const answer = await nlQuery(question, nlHistory.value.map(({ query, answer }) => ({ query, answer })))
    nlAnswer.value = answer
    nlHistory.value.unshift({ id: `${Date.now()}-${Math.random()}`, query: question, answer: answer?.answer || '' })
    nlHistory.value = nlHistory.value.slice(0, 30)
    localStorage.setItem('ai_nl_history', JSON.stringify(nlHistory.value))
  } finally { nlLoading.value = false }
}
const submitFeedback = () => { if (!feedbackType.value) return ElMessage.warning('请选择问题类型'); ElMessage.success('反馈已提交') }
const smartMatchFields = () => {
  const text = `${customForm.label} ${customForm.hint} ${customForm.prompt}`
  const fields = ['资产名称','资产编码','品牌','型号','状态','部门','使用人','购置原值','购置日期'].filter(field => text.includes(field))
  customForm.fields = fields.length ? fields.join('、') : (customForm.table === 'ai_asset' ? '资产名称、品牌、型号、部门、使用人' : '名称、编码、状态')
}
const handleFileUpload = async event => {
  const file = event.target.files?.[0]
  if (!file) return
  importFile.value = file
  const formData = new FormData(); formData.append('file', file)
  try { importPreview.value = await importAssetFile(formData, false) } catch {} finally { event.target.value = '' }
}
const commitImport = async () => {
  if (!importFile.value) return
  const formData = new FormData(); formData.append('file', importFile.value)
  importPreview.value = await importAssetFile(formData, true)
}
const restoreHistory = item => { const question = item.query || item.question || item.title || ''; if (!question) return; nlInput.value = question; lastQuestion.value = question; nlAnswer.value = item }
const removeNlHistory = index => { nlHistory.value.splice(index, 1); localStorage.setItem('ai_nl_history', JSON.stringify(nlHistory.value)) }
const clearNlHistory = () => { nlHistory.value = []; nlAnswer.value = null; localStorage.removeItem('ai_nl_history') }
const runQuickQuery = query => { nlInput.value = query; doNlQuery() }
const handleShortcut = item => {
  if (item.path) { router.push(item.path); return }
  if (item.prompt) runQuickQuery(item.prompt)
}
const saveCustomShortcut = () => {
  const entry = customForm.entry.trim(); const label = customForm.label.trim(); const prompt = customForm.prompt.trim()
  if (!entry || !label || !prompt) return
  const entryKey = `custom-${entry}`
  if (!shortcutGroups[2].entries.some(row => row.key === entryKey)) shortcutGroups[2].entries.push({ key: entryKey, label: entry, items: [] })
  customShortcuts.value.push({ entryKey, label, hint: customForm.hint.trim() || '我的快捷问题', prompt, table: customForm.table, fields: customForm.fields, custom: true })
  localStorage.setItem('ai_custom_shortcuts', JSON.stringify(customShortcuts.value))
  customForm.entry = ''; customForm.label = ''; customForm.hint = ''; customForm.prompt = ''; customForm.table = 'ai_asset'; customForm.fields = ''; customDialogVisible.value = false
  shortcutGroup.value = 'common'; shortcutEntry.value = entryKey
}
const removeCustomShortcut = item => {
  customShortcuts.value = customShortcuts.value.filter(row => row !== item)
  localStorage.setItem('ai_custom_shortcuts', JSON.stringify(customShortcuts.value))
}
const queryParams = (size, includeTotal) => {
  const params = { ...filter, page: page.value, size, include_total: includeTotal }
  Object.keys(params).forEach(k => { if (params[k] === '' || params[k] === null) delete params[k] })
  return params
}
const doQuery = async ({ progressive = false } = {}) => {
  if (progressiveTimer) { clearTimeout(progressiveTimer); progressiveTimer = null }
  if (queryController) queryController.abort()
  queryController = new AbortController()
  const signal = queryController.signal
  const sequence = ++querySequence
  totalReady.value = false
  isProgressiveLoading.value = progressive
  if (progressive) {
    const preview = await queryAssets(queryParams(20, false), signal)
    if (sequence !== querySequence) return
    results.value = preview.list
    // 首屏只取 20 条，不自动执行大表 COUNT，避免切页时后台仍运行重查询。
    isProgressiveLoading.value = false
    return
  }
  const res = await queryAssets(queryParams(20, true), signal)
  if (sequence !== querySequence) return
  results.value = res.list
  total.value = res.total
  totalReady.value = true
  isProgressiveLoading.value = false
}
const resetFilter = () => {
  Object.assign(filter, { keyword: '', class_id: null, state_id: null, dept_id: null, is_idle: null, min_price: null, max_price: null })
  page.value = 1
  results.value = []; total.value = 0; totalReady.value = false
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
  const loadForecast = async () => {
  const existing = await getForecast()
  // 进入页面只读取已有结果，不自动触发重计算。
  forecast.value = existing
}
  const runForecast = async () => { forecast.value = await computeForecast(forecastMonths.value); }
const loadModeData = () => {
  // 条件筛选由用户主动点击“查询”后执行，首次进入只展示筛选条件。
  if (isFilterView.value) { results.value = []; total.value = 0; totalReady.value = false }
  if (isForecastView.value) loadForecast()
}
const loadFilterDictionaries = async () => {
  const [classResult, stateResult, deptResult] = await Promise.allSettled([getAssetClasses(), getAssetStates(), getDepartments()])
  classes.value = classResult.status === 'fulfilled' ? classResult.value : []
  states.value = stateResult.status === 'fulfilled' ? stateResult.value : []
  depts.value = deptResult.status === 'fulfilled' ? deptResult.value : []
}
onMounted(async () => {
  try {
    const stored = JSON.parse(localStorage.getItem('ai_nl_history') || '[]')
    nlHistory.value = Array.isArray(stored) ? stored.filter(item => item && typeof item === 'object' && (item.query || item.question || item.title)).slice(0, 30) : []
    if (nlHistory.value.length) lastQuestion.value = nlHistory.value[0].query || nlHistory.value[0].question || nlHistory.value[0].title || ''
    localStorage.setItem('ai_nl_history', JSON.stringify(nlHistory.value))
  } catch { nlHistory.value = [] }
  try { customShortcuts.value = JSON.parse(localStorage.getItem('ai_custom_shortcuts') || '[]'); customShortcuts.value.forEach(item => { const key = item.entryKey || 'custom-我的快捷'; const label = key.replace(/^custom-/, ''); if (!shortcutGroups[2].entries.some(row => row.key === key)) shortcutGroups[2].entries.push({ key, label, items: [] }) }) } catch { customShortcuts.value = [] }
  loadModeData()
  if (isNlView.value) { try { aiStatus.value = await getLlmStatus() } catch {} }
  if (isFilterView.value) {
    // 筛选页只加载自身需要的字典，避免无关接口拖慢页面进入。
    await loadFilterDictionaries()
  }
})
watch(pageMode, (mode) => {
  if (mode !== 'filter') {
    // 让尚未完成的预览/补全请求失效，切页后不再更新已卸载的筛选视图。
    querySequence += 1
    if (progressiveTimer) { clearTimeout(progressiveTimer); progressiveTimer = null }
    isProgressiveLoading.value = false
  }
  loadModeData()
  if (mode === 'filter' && !classes.value.length) loadFilterDictionaries()
})
onBeforeUnmount(() => {
  querySequence += 1
  if (queryController) queryController.abort()
  if (progressiveTimer) clearTimeout(progressiveTimer)
})
</script>
<style scoped>
.category-parent { display: block; margin-top: 3px; color: #8a98aa; font-size: 11px; font-weight: 400; }
</style>

<style scoped>
.page-description { margin: 0 0 18px; color: #718198; font-size: 13px; }.card-title { font-size: 16px; font-weight: 650; color: #20334d; margin-bottom: 12px; border-left: 3px solid #1769aa; padding-left: 10px; }.result-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }.preview-state { margin-top:2px; color:#62748c; font-size:12px; }.nl-answer { padding: 16px; border: 1px solid #cfe0ef; border-left: 3px solid #1769aa; background: #f7fbff; color: #20334d; }.answer-meta { margin-top: 8px; font-size: 12px; color: #718198; }
.nl-history { margin-top: 12px; border: 1px solid #e2eaf2; background: #fbfcfe; }
.nl-history-head { display:flex; align-items:center; justify-content:space-between; padding:7px 10px; color:#53657d; font-size:12px; border-bottom:1px solid #e2eaf2; }
.nl-history-item { display:flex; align-items:center; gap:8px; padding:7px 10px; border-bottom:1px solid #eef2f6; }
.nl-history-item:last-child { border-bottom:0; }
.nl-history-question { flex:1; min-width:0; overflow:hidden; border:0; background:transparent; color:#20334d; text-align:left; text-overflow:ellipsis; white-space:nowrap; cursor:pointer; font-size:12px; }
.nl-history-question:hover { color:#1769aa; }
.nl-history-question strong,.nl-history-question small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.nl-history-question small { margin-top:3px; color:#8a98aa; font-size:11px; }
.tech-card:has(.ai-process-panel) { position:relative; min-height:calc(100vh - 150px); padding:22px 320px 160px 270px; overflow:hidden; }
.tech-card:has(.ai-process-panel) > .card-title { margin:-22px -320px 18px -270px; padding:18px 22px; border-bottom:1px solid #e2eaf2; border-left:0; }
.tech-card:has(.ai-process-panel) .nl-history { position:absolute; left:0; top:64px; bottom:0; width:245px; margin:0; border:0; border-right:1px solid #e2eaf2; background:#fff; overflow:auto; }
.tech-card:has(.ai-process-panel) .nl-search { position:absolute; left:270px; right:320px; bottom:24px; margin:0; }
.tech-card:has(.ai-process-panel) .nl-tools { position:absolute; left:270px; right:320px; bottom:0; transform:translateY(-2px); }
.tech-card:has(.ai-process-panel) .nl-answer { margin:0 !important; min-height:180px; }
.tech-card:has(.ai-process-panel) > div:last-of-type { position:absolute; left:270px; right:320px; bottom:150px; margin:0; }
.ai-process-panel { position:absolute; top:0; right:0; bottom:0; width:300px; padding:0 16px; border-left:1px solid #e2eaf2; background:#fff; color:#20334d; }
.ai-panel-title { padding:18px 0 12px; border-bottom:1px solid #e2eaf2; font-weight:650; }
.ai-step { margin:18px 0; padding-left:14px; border-left:2px solid #0f8178; font-size:13px; }
.ai-step span { display:block; margin-top:6px; color:#718198; font-size:12px; }
.feedback-title { margin:38px -16px 14px; padding-left:16px; }
.nl-empty-state { min-height:250px; padding:72px 24px; text-align:center; color:#718198; }
.nl-empty-icon { width:28px; height:28px; margin:0 auto 6px; border-radius:50%; background:#e8f4f3; color:#0f8178; display:grid; place-items:center; font-weight:700; font-size:12px; }
.nl-empty-state h3 { margin:0 0 4px; color:#20334d; font-size:14px; }
.nl-empty-state p { margin:0; font-size:12px; }
.nl-question-bubble { margin-bottom:14px; padding:11px 14px; border:1px solid #dce8f1; border-radius:8px; background:#fff; color:#20334d; }
.shortcut-context-divider { margin:158px 0 0; padding:10px 0; border-top:1px solid #e2eaf2; color:#53657d; font-size:12px; font-weight:600; }
.tech-card:has(.ai-process-panel) > div:has(.shortcut-context-divider) { min-height:190px; }
.ai-process-panel p { color:#718198; font-size:12px; line-height:1.6; }
@media (max-width:900px) { .tech-card:has(.ai-process-panel) { padding-left:16px; padding-right:16px; padding-bottom:300px; } .tech-card:has(.ai-process-panel) .nl-history,.ai-process-panel { display:none; } .tech-card:has(.ai-process-panel) .nl-search,.tech-card:has(.ai-process-panel) .nl-tools,.tech-card:has(.ai-process-panel) > div:last-of-type { left:16px; right:16px; } }
.nl-search { width:100%; }
.nl-input { width:100%; }
.nl-input { height:110px; }
.nl-input :deep(textarea) { height:110px !important; min-height:110px !important; }
.nl-input :deep(.el-textarea__inner) { min-height:180px !important; max-height:360px; padding:18px 20px; line-height:1.65; font-size:15px; resize:vertical; }
.nl-input :deep(.el-input-group__append) { vertical-align:bottom; }
.nl-input :deep(.el-input-group__append) { height:110px; padding:0; vertical-align:top; }
.nl-input :deep(.el-input-group__append .el-button) { height:110px; min-height:110px; padding:0 22px; }
.nl-tools { display:flex; align-items:center; gap:10px; margin-top:12px; color:#718198; font-size:12px; min-height:32px; }
.shortcut-tabs { display:flex; gap:8px; margin-bottom:10px; border-bottom:1px solid #e2eaf2; }
.shortcut-tab { border:0; background:transparent; color:#718198; padding:7px 12px; cursor:pointer; font-size:13px; border-bottom:2px solid transparent; }
.shortcut-tab span { margin-left:5px; color:#9aabba; font-size:11px; }
.shortcut-tab.active { color:#1769aa; border-bottom-color:#1769aa; font-weight:600; }
.shortcut-customize { margin-left:auto; border:0; background:transparent; color:#1769aa; cursor:pointer; font-size:12px; padding:7px 4px; }
.shortcut-entry-tabs { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }
.shortcut-entry { border:1px solid #dfe7f0; border-radius:5px; background:#f8fafc; color:#53657d; padding:6px 11px; cursor:pointer; font-size:12px; }
.shortcut-entry:hover, .shortcut-entry.active { border-color:#8ab8da; background:#eaf4fc; color:#1769aa; }
.shortcut-items { display:flex; flex-wrap:wrap; gap:8px; }
.shortcut-item { display:flex; flex-direction:column; align-items:flex-start; min-width:145px; padding:9px 12px; border:1px solid #dfe7f0; border-radius:6px; background:#fff; color:#20334d; cursor:pointer; text-align:left; }
.shortcut-item:hover { border-color:#8ab8da; background:#f4f9fd; }
.shortcut-item-title { font-size:13px; }
.shortcut-item small { margin-top:3px; color:#8191a7; font-size:11px; }
.shortcut-item { position:relative; }
.shortcut-remove { position:absolute; top:4px; right:7px; color:#9aabba; font-style:normal; font-size:15px; }
.shortcut-remove:hover { color:#c84b54; }
</style>
