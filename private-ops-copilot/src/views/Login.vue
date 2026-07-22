<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref(null)
const form = ref({
  username: '',
  password: '',
})
const errorMessage = ref('')
const loading = ref(false)

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function handleLogin() {
  formRef.value?.validate((valid) => {
    if (!valid) return

    loading.value = true
    errorMessage.value = ''

    // 模拟登录延迟
    setTimeout(() => {
      try {
        const result = authStore.login(form.value.username, form.value.password)
        if (result.success) {
          ElMessage.success('登录成功')
          router.push(result.redirect)
        } else {
          errorMessage.value = result.message
        }
      } finally {
        loading.value = false
      }
    }, 800)
  })
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <!-- 品牌Logo -->
      <div class="logo-area">
        <div class="logo-icon">
          <el-icon :size="48"><ChatDotRound /></el-icon>
        </div>
        <h1 class="logo-title">私域运营 Copilot</h1>
        <p class="logo-subtitle">Private Domain Operations Copilot</p>
      </div>

      <!-- 登录表单 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>

        <!-- 错误提示 -->
        <transition name="el-fade-in">
          <div v-if="errorMessage" class="error-message">
            <el-icon><CircleCloseFilled /></el-icon>
            <span>{{ errorMessage }}</span>
          </div>
        </transition>
      </el-form>

      <!-- 底部提示 -->
      <div class="login-footer">
        <span>测试账号：siyu / shequn / neirong / fuzeren / pinpai</span>
        <span>统一密码：123456</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 420px;
  padding: 48px 40px 32px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.logo-area {
  text-align: center;
  margin-bottom: 36px;
}

.logo-icon {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  color: #ffffff;
  margin-bottom: 16px;
}

.logo-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 6px;
}

.logo-subtitle {
  font-size: 13px;
  color: #909399;
  margin: 0;
}

.login-form {
  margin-top: 8px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
}

.error-message {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 0;
  color: #f56c6c;
  font-size: 14px;
}

.login-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
  font-size: 12px;
  color: #c0c4cc;
}
</style>
