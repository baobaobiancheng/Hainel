<template>
  <div class="error-list">
    <div class="page-header">
      <h1>错题本</h1>
      <el-button type="primary" @click="router.push('/errors/add')">
        <el-icon><Plus /></el-icon>
        添加错题
      </el-button>
    </div>
    
    <el-card style="margin-top: 20px">
      <el-empty v-if="errorStore.errorList.length === 0" description="暂无错题" />
      
      <el-table v-else :data="errorStore.errorList" style="width: 100%">
        <el-table-column prop="subject" label="学科" width="100" />
        <el-table-column prop="chapter" label="章节" width="150" />
        <el-table-column prop="difficulty" label="难度" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="handleView(row.id)">查看</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useErrorStore } from '@/stores/error'
import { Plus } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const errorStore = useErrorStore()

onMounted(() => {
  errorStore.fetchErrorList()
})

function handleView(id: string) {
  router.push(`/errors/${id}`)
}

async function handleDelete(id: string) {
  try {
    await ElMessageBox.confirm('确定要删除这道错题吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    await errorStore.deleteError(id)
  } catch (error) {
    // 用户取消
  }
}
</script>

<style scoped lang="scss">
.error-list {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h1 {
      font-size: 24px;
    }
  }
}
</style>

