<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const showTopbar = computed(() => {
  return route.path !== '/login' && authStore.isLoggedIn
})

function handleLogout() {
  authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <div>
    <header v-if="showTopbar" class="app-topbar">
      <div class="app-brand">私域运营 Copilot</div>
      <div class="user-area">
        <span class="user-info">
          {{ authStore.username }}
          <span class="role-name">{{ authStore.roleName }}</span>
        </span>
        <el-button size="small" plain @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </header>
    <router-view />
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

#app {
  width: 100%;
  min-height: 100vh;
}

.app-topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.04);
}

.app-brand {
  font-weight: 700;
  color: #303133;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  color: #303133;
  font-size: 14px;
}

.role-name {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
