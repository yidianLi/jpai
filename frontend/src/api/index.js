import request from '@/utils/request'

// 认证
export const login = (data) => request.post('/auth/login', data, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
export const getMe = () => request.get('/auth/me')

// 驾驶舱
export const getOverview = () => request.get('/dashboard/overview')
export const getActionItems = () => request.get('/dashboard/action-items')
export const getClassDistribution = () => request.get('/dashboard/class-distribution')
export const getStateDistribution = () => request.get('/dashboard/state-distribution')
export const getMonthlyTrend = (months = 12) => request.get('/dashboard/monthly-trend', { params: { months } })
export const getOperationalEffectiveness = (months = 12, deptId) => request.get('/dashboard/operational-effectiveness', { params: { months, dept_id: deptId } })
export const getDeptRanking = () => request.get('/dashboard/dept-ranking')
export const getWarnings = (params) => request.get('/dashboard/warnings', { params })
export const handleWarning = (id, status, remark) => request.post(`/dashboard/warnings/${id}/handle`, null, { params: { status, remark } })
export const generateMonthlyReport = (year, month) => request.post('/dashboard/report/generate-monthly', null, { params: { year, month } })
export const getReportJob = (jobId) => request.get(`/dashboard/report-jobs/${encodeURIComponent(jobId)}`)
export const cancelReportJob = (jobId) => request.post(`/dashboard/report-jobs/${encodeURIComponent(jobId)}/cancel`)
export const retryReportJob = (jobId) => request.post(`/dashboard/report-jobs/${encodeURIComponent(jobId)}/retry`)
export const getReports = (params) => request.get('/dashboard/reports', { params })

// 盘点
export const getCheckTasks = () => request.get('/check/tasks')
export const getCheckDetail = (bid, params) => request.get(`/check/tasks/${bid}/detail`, { params })
export const getCheckDiagnosis = (bid) => request.get(`/check/tasks/${bid}/diagnosis`)
export const getOptimizedPath = () => request.get('/check/optimized-path')

// 闲置
export const getIdlePool = (params) => request.get('/idle/pool', { params })
export const getIdleStats = () => request.get('/idle/stats')
export const refreshIdle = () => request.post('/idle/refresh')
export const markTransfer = (id) => request.post(`/idle/${id}/transfer`)
export const getTransferSuggestions = (params) => request.get('/transfer/suggestions', { params })
export const createTransferSuggestion = (data) => request.post('/transfer/suggestions', data)
export const confirmTransfer = (id, remark = '') => request.post(`/transfer/suggestions/${id}/receiver-confirm`, { remark })
export const rejectTransfer = (id, remark = '') => request.post(`/transfer/suggestions/${id}/receiver-reject`, { remark })
export const executeTransfer = (id) => request.post(`/transfer/suggestions/${id}/execute`)
export const cancelTransfer = (id, remark = '') => request.post(`/transfer/suggestions/${id}/cancel`, { remark })
export const getBrandInsights = (params) => request.get('/insight/brands', { params })
export const getModelInsights = (params) => request.get('/insight/models', { params })
export const getModelEvidence = (params) => request.get('/insight/models/evidence', { params })
export const explainInsight = (data) => request.post('/insight/explain', data)
export const previewProcurement = (params) => request.post('/procurement/preview', null, { params })
export const aiPreviewProcurement = (text) => request.post('/procurement/ai-preview', { request: text })
export const saveProcurementSuggestion = (data) => request.post('/procurement/suggestions', data)
export const getProcurementSuggestions = () => request.get('/procurement/suggestions')
export const confirmProcurementSuggestion = (id) => request.post(`/procurement/suggestions/${id}/confirm`)

// 生命周期
export const getAssetDetail = (id) => request.get(`/lifecycle/asset/${id}`)
export const getDataQuality = () => request.get('/lifecycle/data-quality')
export const getQualityIssues = (params) => request.get('/lifecycle/quality-issues', { params })
export const actionQualityIssue = (id, action, data = {}) => request.post(`/lifecycle/quality-issues/${id}/action`, null, { params: { action, ...data } })
export const getAbnormalAssets = (params) => request.get('/lifecycle/abnormal-assets', { params })
export const cleanAsset = (id, field, value, reason) => request.post(`/lifecycle/asset/${id}/clean`, null, { params: { field, value, reason } })

// 报废
export const getExpireList = (params) => request.get('/scrap/expire-list', { params })
export const evaluateAsset = (id) => request.post(`/scrap/evaluate/${id}`)
export const batchEvaluate = (ids) => request.post('/scrap/batch-evaluate', ids)

// 查询
export const queryAssets = (params, signal) => request.get('/query/assets', { params, signal })
export const nlQuery = (query, history = []) => request.post('/query/nl-query', { query, history })
export const importAssetFile = (formData, commit = false) => request.post(`/query/import-file?commit=${commit}`, formData, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 })
export const getForecast = () => request.get('/query/forecast')
export const computeForecast = (months) => request.post('/query/forecast/compute', null, { params: { months } })
export const getLlmHealth = () => request.get('/query/llm-health')
export const getLlmStatus = () => request.get('/query/llm-status')
export const getJobStatus = (jobId) => request.get(`/orchestration/jobs/${encodeURIComponent(jobId)}`)
export const getPersistentJob = (jobId) => request.get(`/jobs/${encodeURIComponent(jobId)}`)
export const cancelPersistentJob = (jobId) => request.post(`/jobs/${encodeURIComponent(jobId)}/cancel`)

// 系统
export const syncAll = () => request.post('/system/sync/all')
export const syncDict = () => request.post('/system/sync/dictionaries')
export const syncAssets = () => request.post('/system/sync/assets')
export const getDepartments = () => request.get('/system/departments')
export const updateHeadcount = (id, headcount) => request.put(`/system/departments/${id}/headcount`, null, { params: { headcount } })
export const getCompanies = () => request.get('/system/companies')
export const getAssetClasses = () => request.get('/system/asset-classes')
export const getAssetStates = () => request.get('/system/asset-states')
export const getAiConfig = () => request.get('/system/ai-config')
export const updateAiConfig = (data) => request.put('/system/ai-config', data)
export const getAiUsage = (days = 30) => request.get('/system/ai-usage', { params: { days } })
export const getAiUsageLogs = (params) => request.get('/system/ai-usage/logs', { params })
