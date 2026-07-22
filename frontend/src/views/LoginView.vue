<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { LockKeyhole, Moon, Sun, UserRound } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import DataFlowScene from '../components/visual/DataFlowScene.vue'
import { useTheme } from '../composables/useTheme'
import { errorMessage } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const mode = ref<'login' | 'register'>('login')
const form = reactive({ tenant_name: '', username: '', password: '', email: '' })
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()
const { theme, themeToggleLabel, applyTheme, toggleTheme } = useTheme()

async function submit() {
  if (!form.username || !form.password) return ElMessage.warning('请输入用户名和密码')
  if (mode.value === 'register' && !form.tenant_name) return ElMessage.warning('请输入团队名称')
  loading.value = true
  try {
    if (mode.value === 'login') await auth.login(form.username, form.password)
    else await auth.register(form.tenant_name, form.username, form.password, form.email)
    await router.replace(auth.user?.is_platform_admin ? '/platform' : '/dashboard')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

onMounted(applyTheme)
</script>

<template>
  <main class="login-page">
    <button class="login-theme-toggle" :aria-label="themeToggleLabel" :title="themeToggleLabel" @click="toggleTheme">
      <Sun v-if="theme === 'dark'" :size="17" /><Moon v-else :size="17" />
    </button>
    <section class="login-brand-stage">
      <DataFlowScene variant="login" :theme="theme" quality="high" />
      <div class="login-brand-lockup"><span>T2D</span><strong>T2D Cloud</strong></div>
      <div class="login-scene-copy">
        <span>Telegram → DingTalk</span>
        <h2>让消息穿越平台<br>持续抵达</h2>
        <p>统一接入、规则处理与投递，让每条消息沿着可控线路准确流转。</p>
        <div class="login-scene-stages" aria-label="消息处理流程">
          <span><b>Telegram</b><small>消息接收</small></span>
          <span><b>T2D Core</b><small>规则处理</small></span>
          <span><b>DingTalk</b><small>目标投递</small></span>
        </div>
      </div>
      <div class="login-stage-status" aria-hidden="true">
        <i /><span>接收</span><i /><span>处理</span><i /><span>投递</span>
      </div>
    </section>
    <section class="login-panel">
      <div class="login-brand login-brand--mobile"><span>T2D</span><strong>T2D Cloud</strong></div>
      <header class="login-heading"><h1>{{ mode === 'login' ? '欢迎回来' : '创建新团队账户' }}</h1><p>{{ mode === 'login' ? '登录并继续管理消息转发' : '建立独立的转发配置空间' }}</p></header>
      <div class="login-tabs" role="tablist" aria-label="账户入口">
        <button role="tab" :aria-selected="mode === 'login'" :class="{ active: mode === 'login' }" @click="mode='login'">登录</button>
        <button role="tab" :aria-selected="mode === 'register'" :class="{ active: mode === 'register' }" @click="mode='register'">注册</button>
      </div>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item v-if="mode === 'register'" label="团队名称"><el-input v-model="form.tenant_name" size="large" autocomplete="organization" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="form.username" size="large" :prefix-icon="UserRound" autocomplete="username" /></el-form-item>
        <el-form-item v-if="mode === 'register'" label="邮箱（可选）"><el-input v-model="form.email" size="large" autocomplete="email" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" size="large" type="password" show-password :prefix-icon="LockKeyhole" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" @keyup.enter="submit" /></el-form-item>
        <el-button type="primary" size="large" :loading="loading" class="login-submit" @click="submit">{{ mode === 'login' ? '登录' : '创建团队' }}</el-button>
      </el-form>
    </section>
  </main>
</template>
