<template>
  <div><div class="page-description">支持按资产类别比较品牌，也支持直接查询指定品牌；样本不足时不作强推荐。</div>
    <div class="tech-card"><div class="toolbar"><el-radio-group v-model="mode" @change="load"><el-radio-button label="category">按资产类别</el-radio-button><el-radio-button label="brand">按品牌</el-radio-button></el-radio-group><el-select v-if="mode==='category'" v-model="classId" clearable filterable placeholder="选择资产类别" style="width:240px"><el-option v-for="c in classes" :key="c.class_id" :value="c.class_id" :label="c.class_name"/></el-select><el-input v-else v-model="brand" clearable placeholder="输入品牌名称" style="width:220px" @keyup.enter="load"/><el-input-number v-model="minSample" :min="1" :max="1000"/><span class="hint">最小样本量</span><el-button type="primary" @click="load">刷新分析</el-button></div>
      <el-alert v-if="!rows.length" type="warning" :closable="false">当前条件下品牌或维修数据不足，暂时无法形成有意义的比较。</el-alert><el-table v-else :data="rows" stripe><el-table-column prop="brand" label="品牌"/><el-table-column prop="assets" label="资产数"/><el-table-column prop="repairs" label="维修工单"/><el-table-column prop="repair_rate" label="维修频率"/><el-table-column prop="repair_fee" label="维修费用(元)"/><el-table-column prop="idle_rate" label="闲置率"><template #default="{row}">{{row.idle_rate}}%</template></el-table-column><el-table-column label="数据可信度"><template #default="{row}"><el-tag :type="row.confidence==='sufficient'?'success':'warning'">{{row.confidence==='sufficient'?'样本充足':'样本不足'}}</el-tag></template></el-table-column><el-table-column prop="recommendation" label="采购建议"/><el-table-column label="证据"><template #default="{row}">资产{{row.evidence.asset_count}}，维修{{row.evidence.repair_work_orders}}单</template></el-table-column></el-table>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { getBrandInsights, getAssetClasses } from '@/api'
const rows=ref([]), classes=ref([]), mode=ref('category'), brand=ref(''), classId=ref(null), minSample=ref(10)
const load=async()=>{const r=await getBrandInsights({class_id:mode.value==='category'?(classId.value||undefined):undefined, brand:mode.value==='brand'?(brand.value||undefined):undefined, min_sample:minSample.value}); rows.value=r.list||[]}
onMounted(async()=>{classes.value=await getAssetClasses(); load()})
</script>
<style scoped>.page-description{margin-bottom:18px;color:#718198}.toolbar{display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap}.hint{color:#62748c;font-size:13px;margin-right:auto}</style>
