<template>
  <div v-if="loading" class="data-state data-state-loading"><el-skeleton :rows="rows" animated /></div>
  <el-result v-else-if="error" icon="error" :title="errorTitle" :sub-title="errorText"><template #extra><el-button type="primary" @click="$emit('retry')">重新加载</el-button></template></el-result>
  <el-empty v-else-if="empty" :description="emptyText" :image-size="imageSize" />
  <slot v-else />
</template>
<script setup>
defineProps({ loading: Boolean, error: Boolean, empty: Boolean, emptyText: { type: String, default: '暂无数据' }, errorText: { type: String, default: '数据加载失败，请重试' }, errorTitle: { type: String, default: '加载失败' }, rows: { type: Number, default: 5 }, imageSize: { type: Number, default: 72 } })
defineEmits(['retry'])
</script>
<style scoped>
.data-state{padding:18px 4px}.data-state-loading{min-height:180px}.data-state :deep(.el-skeleton__item){background:#edf2f7}.data-state :deep(.el-result){padding:24px 16px}
</style>
