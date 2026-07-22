<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Plus, RefreshCw, Send } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'

const endpoint = '/connectors/telegram/accounts'
const loading = ref(false)
const accounts = ref<any[]>([])
const addVisible = ref(false)
const verifyVisible = ref(false)
const form = reactive({ name: '', api_id: '', api_hash: '', phone: '' })
const verify = reactive({ id: 0, code: '', password: '' })

async function load() {
  loading.value = true
  try { accounts.value = (await api.get(endpoint)).data.data }
  catch (error) { ElMessage.error(errorMessage(error)) }
  finally { loading.value = false }
}
function openAdd() { Object.assign(form, { name: '', api_id: '', api_hash: '', phone: '' }); addVisible.value = true }
async function create() {
  try {
    await api.post(endpoint, { ...form, api_id: Number(form.api_id) })
    addVisible.value = false
    ElMessage.success('Telegram 账号已添加')
    await load()
  } catch (error) { ElMessage.error(errorMessage(error)) }
}
async function sendCode(row: any) {
  try {
    await api.post(`${endpoint}/${row.id}/send-code`, {})
    Object.assign(verify, { id: row.id, code: '', password: '' })
    verifyVisible.value = true
    ElMessage.success('验证码已发送到 Telegram 客户端')
  } catch (error) { ElMessage.error(errorMessage(error)) }
}
async function connect() {
  try {
    await api.post(`${endpoint}/${verify.id}/verify`, { code: verify.code, password: verify.password || null })
    verifyVisible.value = false
    ElMessage.success('Telegram 账号授权成功')
    await load()
  } catch (error) { ElMessage.error(errorMessage(error)) }
}
async function disconnect(row: any) {
  try { await api.post(`${endpoint}/${row.id}/disconnect`, {}); await load() }
  catch (error) { ElMessage.error(errorMessage(error)) }
}
async function remove(row: any) {
  try {
    await ElMessageBox.confirm('确定删除此 Telegram 账号？', '删除确认')
    await api.delete(`${endpoint}/${row.id}`)
    await load()
  } catch (error) { if (error !== 'cancel') ElMessage.error(errorMessage(error)) }
}
onMounted(load)
</script>

<template>
  <PageHeader title="Telegram 账号" description="管理用于接收群组和频道消息的 Telegram 用户账号">
    <el-button :loading="loading" @click="load"><RefreshCw :size="15" />刷新</el-button>
    <el-button type="primary" @click="openAdd"><Plus :size="15" />添加账号</el-button>
  </PageHeader>
  <section class="data-panel">
    <el-table :data="accounts" v-loading="loading" empty-text="暂无 Telegram 账号">
      <el-table-column prop="name" label="账号名称" min-width="160" />
      <el-table-column prop="phone" label="手机号" min-width="170" />
      <el-table-column label="授权状态" width="120"><template #default="{ row }"><el-tag :type="row.is_authorized ? 'success' : 'warning'">{{ row.is_authorized ? '已授权' : '待授权' }}</el-tag></template></el-table-column>
      <el-table-column label="连接状态" width="120"><template #default="{ row }"><span class="status-dot" :class="row.connected ? 'success' : 'muted'" />{{ row.connected ? '已连接' : '未连接' }}</template></el-table-column>
      <el-table-column label="操作" width="260"><template #default="{ row }"><el-button v-if="!row.is_authorized" size="small" type="primary" plain @click="sendCode(row)"><Send :size="14" />发送验证码</el-button><el-button v-else size="small" @click="disconnect(row)">断开</el-button><el-button size="small" type="danger" plain @click="remove(row)">删除</el-button></template></el-table-column>
    </el-table>
  </section>
  <el-dialog v-model="addVisible" title="添加 Telegram 账号" width="540px">
    <el-alert title="API ID 和 API Hash 可在 my.telegram.org 创建应用后获取" type="info" :closable="false" style="margin-bottom:16px" />
    <el-form label-position="top"><el-form-item label="账号名称"><el-input v-model="form.name" /></el-form-item><el-form-item label="API ID"><el-input v-model="form.api_id" /></el-form-item><el-form-item label="API Hash"><el-input v-model="form.api_hash" type="password" show-password /></el-form-item><el-form-item label="手机号"><el-input v-model="form.phone" placeholder="+8613800000000" /></el-form-item></el-form>
    <template #footer><el-button @click="addVisible=false">取消</el-button><el-button type="primary" @click="create">保存并发送验证码</el-button></template>
  </el-dialog>
  <el-dialog v-model="verifyVisible" title="Telegram 验证" width="440px"><el-form label-position="top"><el-form-item label="验证码"><el-input v-model="verify.code" /></el-form-item><el-form-item label="两步验证密码"><el-input v-model="verify.password" type="password" show-password /></el-form-item></el-form><template #footer><el-button @click="verifyVisible=false">取消</el-button><el-button type="primary" @click="connect">确认授权</el-button></template></el-dialog>
</template>
