import request from '@/utils/request'

// 认证
export const login = (data) => request.post('/auth/login', data, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
export const getMe = () => request.get('/auth/me')

// 驾驶舱
export const getOverview = () => request.get('/dashboard/overview')
export const getClassDistribution = () => request.get('/dashboard/class-distribution')
export const getStateDistribution = () => request.get('/dashboard/state-distribution')
export const getMonthlyTrend = (months = 12) => request.get('/dashboard/monthly-trend', { params: { months } })
export const getDeptRanking = () => request.get('/dashboard/dept-ranking')
export const getWarnings = (params) => request.get('/dashboard/warnings', { params })
export const handleWarning = (id, status, remark) => request.post(`/dashboard/warnings/${id}/handle`, null, { params: { status, remark } })
export const generateMonthlyReport = (year, month) => request.post('/dashboard/report/generate-monthly', null, { params: { year, month } })
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

// 生命周期
export const getAssetDetail = (id) => request.get(`/lifecycle/asset/${id}`)
export const getDataQuality = () => request.get('/lifecycle/data-quality')
export const getAbnormalAssets = (params) => request.get('/lifecycle/abnormal-assets', { params })
export const cleanAsset = (id, field, value, reason) => request.post(`/lifecycle/asset/${id}/clean`, null, { params: { field, value, reason } })

// 报废
export const getExpireList = (params) => request.get('/scrap/expire-list', { params })
export const evaluateAsset = (id) => request.post(`/scrap/evaluate/${id}`)
export const batchEvaluate = (ids) => request.post('/scrap/batch-evaluate', ids)

// 查询
export const queryAssets = (params) => request.get('/query/assets', { params })
export const nlQuery = (query) => request.post('/query/nl-query', null, { params: { query } })
export const getForecast = () => request.get('/query/forecast')
export const computeForecast = (months) => request.post('/query/forecast/compute', null, { params: { months } })
export const getLlmHealth = () => request.get('/query/llm-health')

// 系统
export const syncAll = () => request.post('/system/sync/all')
export const syncDict = () => request.post('/system/sync/dictionaries')
export const syncAssets = () => request.post('/system/sync/assets')
export const getDepartments = () => request.get('/system/departments')
export const updateHeadcount = (id, headcount) => request.put(`/system/departments/${id}/headcount`, null, { params: { headcount } })
export const getCompanies = () => request.get('/system/companies')
export const getAssetClasses = () => request.get('/system/asset-classes')
export const getAssetStates = () => request.get('/system/asset-states')
