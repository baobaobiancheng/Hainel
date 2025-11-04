<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo">
        <span v-if="!collapsed">智能错题本</span>
        <span v-else>错题</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/">
          <el-icon><Dashboard /></el-icon>
          <span>工作台</span>
        </el-menu-item>
        
        <el-menu-item index="/errors">
          <el-icon><Document /></el-icon>
          <span>错题本</span>
        </el-menu-item>
        
        <el-menu-item index="/practice">
          <el-icon><Edit /></el-icon>
          <span>智能练习</span>
        </el-menu-item>
        
        <el-menu-item index="/knowledge">
          <el-icon><Connection /></el-icon>
          <span>知识图谱</span>
        </el-menu-item>
        
        <el-menu-item index="/reports">
          <el-icon><TrendCharts /></el-icon>
          <span>学习报告</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-icon" @click="toggleSidebar">
            <Fold v-if="!collapsed" />
            <Expand v-else />
          </el-icon>
        </div>
        
        <div class="header-right">
          <el-dropdown>
            <div class="user-info">
              <el-avatar :src="userStore.avatar" />
              <span class="username">{{ userStore.username }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人中心</el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 内容区 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import {
  Dashboard,
  Document,
  Edit,
  Connection,
  TrendCharts,
  Fold,
  Expand,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

const collapsed = computed(() => appStore.sidebarCollapsed)
const sidebarWidth = computed(() => (collapsed.value ? '64px' : '200px'))
const activeMenu = computed(() => route.path)

function toggleSidebar() {
  appStore.toggleSidebar()
}

function handleLogout() {
  userStore.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s;
  
  .logo {
    height: 50px;
    line-height: 50px;
    text-align: center;
    font-size: 18px;
    font-weight: bold;
    color: #fff;
    background-color: #2d3a4d;
  }
  
  .sidebar-menu {
    border-right: none;
  }
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  
  .header-left {
    .collapse-icon {
      font-size: 20px;
      cursor: pointer;
      
      &:hover {
        color: #409eff;
      }
    }
  }
  
  .header-right {
    .user-info {
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
      
      .username {
        font-size: 14px;
      }
    }
  }
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

