<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Plus, RefreshCw } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import { limitLabel, planLabel, planPrice } from '../lib/entitlements'
import { useAuthStore } from '../stores/auth'
import MetricStrip from '../components/MetricStrip.vue'
import PageHeader from '../components/PageHeader.vue'

const auth = useAuthStore()
const tab = ref('team')
const loading = ref(false)
const dialog = ref(false)
const profile = ref<any>({})
const usage = ref<any>({})
const members = ref<any[]>([])
const form = reactive<any>({ id: null, username: '', password: '', email: '', role: 'member', is_active: true })
const canManageTeam = computed(() => Boolean(auth.user?.is_platform_admin))
const supportedPlans = ['free', 'basic', 'pro', 'enterprise']
const metrics = computed(() => [
  { label: '团队成员', value: members.value.length, note: `上限 ${limitLabel(profile.value.member_limit, profile.value.is_unlimited)}` },
  { label: '当前套餐', value: planLabel(profile.value), note: profile.value.plan === 'pro' ? '¥19,800 · 配额无限' : '套餐由平台管理员调整', tone: 'teal' },
  { label: '今日用量', value: usage.value.today_messages || 0, note: `剩余 ${limitLabel(usage.value.remaining, usage.value.is_unlimited)}` },
])

async function load() {
  loading.value = true
  try {
    const [a, b, c] = await Promise.all([api.get('/tenant/profile'), api.get('/tenant/usage'), api.get('/tenant/members')])
    profile.value = a.data.data
    usage.value = b.data.data
    members.value = c.data.data
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function edit(row?: any) {
  Object.assign(form, row ? { ...row, password: '' } : { id: null, username: '', password: '', email: '', role: 'member', is_active: true })
  dialog.value = true
}

async function save() {
  try {
    if (form.id) await api.put(`/tenant/members/${form.id}`, { role: form.role, is_active: form.is_active })
    else await api.post('/tenant/members', form)
    dialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm('确定删除该成员？', '删除确认')
    await api.delete(`/tenant/members/${row.id}`)
    await load()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorMessage(error))
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="组织与计费" description="成员权限、套餐和用量">
    <el-button @click="load"><RefreshCw :size="15" />刷新</el-button>
    <el-button v-if="tab === 'team' && canManageTeam" type="primary" @click="edit()"><Plus :size="15" />新增成员</el-button>
  </PageHeader>
  <MetricStrip :items="metrics" />
  <el-tabs v-model="tab" class="section-tabs">
    <el-tab-pane label="团队成员" name="team" />
    <el-tab-pane label="订阅套餐" name="billing" />
  </el-tabs>
  <section v-if="tab === 'team'" class="data-panel">
    <el-table :data="members" v-loading="loading">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="role" label="角色" />
      <el-table-column label="状态"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column prop="last_login" label="最后登录" />
      <el-table-column v-if="canManageTeam" label="操作" width="160"><template #default="{ row }"><el-button size="small" :disabled="row.role === 'owner'" @click="edit(row)">编辑</el-button><el-button size="small" type="danger" plain :disabled="row.role === 'owner'" @click="remove(row)">删除</el-button></template></el-table-column>
    </el-table>
  </section>
  <section v-else class="plan-list">
    <div v-for="plan in supportedPlans" :key="plan" class="plan-row">
      <div><strong>{{ plan === 'pro' ? '专业版' : plan }}</strong><span>{{ planPrice(plan) }}{{ plan === 'pro' ? ' · 配额无限' : '' }}</span></div>
      <el-tag v-if="profile.plan === plan" type="success">当前套餐</el-tag>
    </div>
    <div class="plan-row"><div><strong>套餐管理</strong><span>套餐仅可由平台管理员调整</span></div><strong>{{ profile.is_unlimited ? '∞' : '按套餐限制' }}</strong></div>
  </section>
  <el-dialog v-model="dialog" :title="form.id ? '编辑成员' : '新增成员'" width="500px">
    <el-form label-position="top">
      <el-form-item label="用户名"><el-input v-model="form.username" :disabled="Boolean(form.id)" /></el-form-item>
      <el-form-item v-if="!form.id" label="初始密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
      <el-form-item v-if="!form.id" label="邮箱"><el-input v-model="form.email" /></el-form-item>
      <el-form-item label="角色"><el-select v-model="form.role" style="width:100%"><el-option label="管理员" value="admin" /><el-option label="成员" value="member" /><el-option label="观察者" value="viewer" /></el-select></el-form-item>
      <el-checkbox v-if="form.id" v-model="form.is_active">启用账号</el-checkbox>
    </el-form>
    <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
  </el-dialog>
</template>
