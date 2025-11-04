<template>
  <div class="auth-layout">
    <div class="auth-container">
      <div class="auth-header">
        <h1>智能错题本</h1>
        <p>让学习更高效</p>
      </div>
      
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
//
</script>

<style scoped lang="scss">
.auth-layout {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth-container {
  width: 400px;
  padding: 40px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.auth-header {
  text-align: center;
  margin-bottom: 30px;
  
  h1 {
    font-size: 28px;
    font-weight: bold;
    color: #333;
    margin-bottom: 10px;
  }
  
  p {
    font-size: 14px;
    color: #666;
  }
}
</style>

