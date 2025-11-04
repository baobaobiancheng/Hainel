<template>
  <div class="login-view">
    <el-form
      ref="formRef"
      :model="loginForm"
      :rules="rules"
      @keyup.enter="handleLogin"
    >
      <el-form-item prop="username_or_email">
        <el-input
          v-model="loginForm.username_or_email"
          placeholder="用户名或邮箱"
          size="large"
        >
          <template #prefix>
            <el-icon><User /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      
      <el-form-item prop="password">
        <el-input
          v-model="loginForm.password"
          type="password"
          placeholder="密码"
          size="large"
          show-password
        >
          <template #prefix>
            <el-icon><Lock /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      
      <el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form-item>
    </el-form>
    
    <div class="login-footer">
      <span>还没有账号？</span>
      <router-link to="/auth/register">立即注册</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username_or_email: '',
  password: '',
})

const rules: FormRules = {
  username_or_email: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      
      try {
        const success = await userStore.login(
          loginForm.username_or_email,
          loginForm.password
        )
        
        if (success) {
          ElMessage.success('登录成功')
          const redirect = (route.query.redirect as string) || '/'
          router.push(redirect)
        }
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped lang="scss">
.login-view {
  .login-footer {
    text-align: center;
    font-size: 14px;
    color: #666;
    
    a {
      color: #409eff;
      text-decoration: none;
      margin-left: 5px;
      
      &:hover {
        text-decoration: underline;
      }
    }
  }
}
</style>

