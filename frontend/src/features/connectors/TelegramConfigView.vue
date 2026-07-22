<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Plus, RefreshCw, Send } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { errorMessage } from '../../lib/api'
import PageHeader from '../../components/PageHeader.vue'
import { connectorApi, type TelegramConfig } from './api'

const loading = ref(false)
const accounts = ref<TelegramConfig[]>([])
const accountDialog = ref(false)
const verifyDialog = ref(false)
const accountForm = reactive({ name: '', api_id: '', api_hash: '', phone: '' })
const verify = reactive({ id: 0, code: '', password: '' })

async function load() {
  loading.value = true
  try {
    accounts.value = await connectorApi.telegramConfigs()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(accountForm, { name: '', api_id: '', api_hash: '', phone: '' })
  accountDialog.value = true
}

async function saveAccount() {
  try {
    await connectorApi.createTelegram({ ...accountForm, api_id: Number(accountForm.api_id) })
    accountDialog.value = false
    ElMessage.success('TG 配置已保存')
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function sendCode(row: any) {
  try {
    await connectorApi.sendTelegramCode(row.id)
    Object.assign(verify, { id: row.id, code: '', password: '' })
    verifyDialog.value = true
    ElMessage.success('验证码已发送到 Telegram App')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function verifyAccount() {
  try {
    await connectorApi.verifyTelegram(verify.id, verify.code, verify.password || null)
    verifyDialog.value = false
    ElMessage.success('TG 账号授权完成')
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function disconnect(row: any) {
  try {
    await connectorApi.disconnectTelegram(row.id)
    ElMessage.success('TG 账号已断开')
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm('确定删除该 TG 配置？', '删除确认')
    await connectorApi.deleteTelegram(row.id)
    await load()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorMessage(error))
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="TG 配置" description="配置并授权用于接收消息的 Telegram 账号">
    <el-button :loading="loading" @click="load"><RefreshCw :size="15" />刷新</el-button>
    <el-button type="primary" @click="openCreate"><Plus :size="15" />新增 TG 配置</el-button>
  </PageHeader>
  <section class="data-panel desktop-config-table">
    <el-table :data="accounts" v-loading="loading" empty-text="暂无 TG 配置">
      <el-table-column prop="name" label="配置名称" min-width="160" />
      <el-table-column prop="phone" label="登录手机号" min-width="170" />
      <el-table-column label="授权状态" width="120"><template #default="{ row }"><el-tag :type="row.is_authorized ? 'success' : 'warning'">{{ row.is_authorized ? '已授权' : '待授权' }}</el-tag></template></el-table-column>
      <el-table-column label="连接状态" width="120"><template #default="{ row }"><span class="status-dot" :class="row.connected ? 'success' : 'muted'" />{{ row.connected ? '已连接' : '未连接' }}</template></el-table-column>
      <el-table-column label="操作" width="250"><template #default="{ row }"><el-button v-if="!row.is_authorized" size="small" type="primary" plain @click="sendCode(row)"><Send :size="14" />发送验证码</el-button><el-button v-else size="small" @click="disconnect(row)">断开</el-button><el-button size="small" type="danger" plain @click="remove(row)">删除</el-button></template></el-table-column>
    </el-table>
  </section>
  <section class="mobile-config-list">
    <article v-for="row in accounts" :key="row.id" class="mobile-config-item">
      <div class="mobile-config-head"><strong>{{ row.name }}</strong><el-tag :type="row.is_authorized ? 'success' : 'warning'">{{ row.is_authorized ? '已授权' : '待授权' }}</el-tag></div>
      <dl><div><dt>登录手机号</dt><dd>{{ row.phone }}</dd></div><div><dt>连接状态</dt><dd><span class="status-dot" :class="row.connected ? 'success' : 'muted'" />{{ row.connected ? '已连接' : '未连接' }}</dd></div></dl>
      <div class="mobile-config-actions"><el-button v-if="!row.is_authorized" size="small" type="primary" plain @click="sendCode(row)"><Send :size="14" />发送验证码</el-button><el-button v-else size="small" @click="disconnect(row)">断开</el-button><el-button size="small" type="danger" plain @click="remove(row)">删除</el-button></div>
    </article>
    <div v-if="!loading && accounts.length === 0" class="mobile-config-empty">暂无 TG 配置</div>
  </section>
  <el-dialog v-model="accountDialog" title="新增 TG 配置" width="500px">
    <el-form label-position="top">
      <el-form-item label="配置名称"><el-input v-model="accountForm.name" placeholder="例如：运营频道账号" /></el-form-item>
      <el-form-item label="API ID"><el-input v-model="accountForm.api_id" inputmode="numeric" /></el-form-item>
      <el-form-item label="API Hash"><el-input v-model="accountForm.api_hash" type="password" show-password /></el-form-item>
      <el-form-item label="登录手机号"><el-input v-model="accountForm.phone" placeholder="+8613800000000" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="accountDialog = false">取消</el-button><el-button type="primary" @click="saveAccount">保存配置</el-button></template>
  </el-dialog>
  <el-dialog v-model="verifyDialog" title="完成 TG 授权" width="440px">
    <el-form label-position="top">
      <el-form-item label="Telegram 验证码"><el-input v-model="verify.code" autocomplete="one-time-code" /></el-form-item>
      <el-form-item label="两步验证密码"><el-input v-model="verify.password" type="password" show-password /></el-form-item>
    </el-form>
    <template #footer><el-button @click="verifyDialog = false">取消</el-button><el-button type="primary" @click="verifyAccount">确认授权</el-button></template>
  </el-dialog>
</template>

<style scoped>
.mobile-config-list { display: none; }
@media (max-width: 760px) {
  .desktop-config-table { display: none; }
  .mobile-config-list { display: grid; gap: 10px; }
  .mobile-config-item { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 14px; }
  .mobile-config-head, .mobile-config-actions, .mobile-config-item dl div { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .mobile-config-head strong { font-size: 14px; }
  .mobile-config-item dl { margin: 12px 0; display: grid; gap: 8px; }
  .mobile-config-item dt { color: var(--muted); font-size: 12px; }
  .mobile-config-item dd { margin: 0; font-size: 13px; }
  .mobile-config-actions { justify-content: flex-end; padding-top: 12px; border-top: 1px solid #edf1f0; }
  .mobile-config-empty { padding: 40px 16px; text-align: center; background: #fff; border: 1px solid var(--border); border-radius: 6px; color: var(--muted); font-size: 13px; }
}
</style>
