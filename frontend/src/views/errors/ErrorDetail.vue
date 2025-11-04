<template>
  <div class="error-detail">
    <el-page-header @back="router.back()">
      <template #content>
        <span class="text-large">错题详情</span>
      </template>
    </el-page-header>
    
    <el-card style="margin-top: 20px">
      <el-empty v-if="!errorStore.currentError" description="错题不存在" />
      
      <div v-else>
        <p>错题详情内容...</p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useErrorStore } from '@/stores/error'

const route = useRoute()
const router = useRouter()
const errorStore = useErrorStore()

onMounted(() => {
  const id = route.params.id as string
  errorStore.fetchErrorDetail(id)
})
</script>

<style scoped lang="scss">
.error-detail {
  //
}
</style>

