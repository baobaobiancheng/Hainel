<template>
  <div class="dashboard">
    <h1>工作台</h1>
    <p>欢迎使用智能错题本！</p>
    
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>错题总数</span>
          </template>
          <div class="stat-value">0</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>待复习</span>
          </template>
          <div class="stat-value">0</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>已掌握</span>
          </template>
          <div class="stat-value">0</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>学习天数</span>
          </template>
          <div class="stat-value">0</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
// Dashboard 页面
</script>

<style scoped lang="scss">
.dashboard {
  h1 {
    font-size: 24px;
    margin-bottom: 10px;
  }
  
  .stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #409eff;
    text-align: center;
    padding: 20px 0;
  }
}
</style>

