<template>
  <div class="add-error">
    <el-page-header @back="router.back()">
      <template #content>
        <span class="text-large">添加错题</span>
      </template>
    </el-page-header>
    
    <el-card style="margin-top: 20px">
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="学科">
          <el-input v-model="form.subject" />
        </el-form-item>
        
        <el-form-item label="章节">
          <el-input v-model="form.chapter" />
        </el-form-item>
        
        <el-form-item label="题目内容">
          <el-input v-model="form.question_text" type="textarea" :rows="4" />
        </el-form-item>
        
        <el-form-item label="正确答案">
          <el-input v-model="form.correct_answer" type="textarea" :rows="2" />
        </el-form-item>
        
        <el-form-item label="我的答案">
          <el-input v-model="form.user_answer" type="textarea" :rows="2" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit">提交</el-button>
          <el-button @click="router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useErrorStore } from '@/stores/error'

const router = useRouter()
const errorStore = useErrorStore()

const form = reactive({
  subject: '',
  chapter: '',
  question_text: '',
  correct_answer: '',
  user_answer: '',
})

async function handleSubmit() {
  const success = await errorStore.createError(form)
  if (success) {
    router.back()
  }
}
</script>

<style scoped lang="scss">
.add-error {
  //
}
</style>

