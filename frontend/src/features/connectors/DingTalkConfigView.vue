<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Copy, Plus, RefreshCw, Send } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { errorMessage } from '../../lib/api'
import PageHeader from '../../components/PageHeader.vue'
import { connectorApi, type DingTalkConfig } from './api'

const loading = ref(false)
const bots = ref<DingTalkConfig[]>([])
const dialog = ref(false)
const form = reactive<any>({ id: null, name: '', webhook: '', secret: '', enabled: true })

async function load() {
  loading.value = true
  try {
    bots.value = await connectorApi.dingTalkConfigs()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function edit(row?: any) {
  Object.assign(form, row ? { id: row.id, name: row.name, webhook: row.webhook, secret: row.secret || '', enabled: row.enabled } : { id: null, name: '', webhook: '', secret: '', enabled: true })
  dialog.value = true
}

async function save() {
  try {
    const payload = { name: form.name, webhook: form.webhook, secret: form.secret, enabled: form.enabled }
    if (form.id) await connectorApi.updateDingTalk(form.id, payload)
    else await connectorApi.createDingTalk(payload)
    dialog.value = false
    ElMessage.success('钉钉配置已保存')
    await load()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function maskedWebhook(webhook: string) {
  if (!webhook) return '-'
  const token = webhook.split('access_token=')[1]
  return token ? `${webhook.split('access_token=')[0]}access_token=••••${token.slice(-6)}` : webhook
}

async function copyWebhook(webhook: string) {
  await navigator.clipboard.writeText(webhook)
  ElMessage.success('Webhook 已复制')
}

async function test(row: any) {
  try {
    await connectorApi.testDingTalk(row.id)
    ElMessage.success('测试消息已发送')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm('确定删除该钉钉配置？', '删除确认')
    await connectorApi.deleteDingTalk(row.id)
    await load()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorMessage(error))
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="钉钉配置" description="配置接收转发消息的钉钉群机器人">
    <el-button :loading="loading" @click="load"><RefreshCw :size="15" />刷新</el-button>
    <el-button type="primary" @click="edit()"><Plus :size="15" />新增钉钉配置</el-button>
  </PageHeader>
  <section class="data-panel desktop-config-table">
    <el-table :data="bots" v-loading="loading" empty-text="暂无钉钉配置">
      <el-table-column prop="name" label="配置名称" min-width="170" />
      <el-table-column label="Webhook 地址" min-width="380"><template #default="{ row }"><div class="webhook-cell"><span>{{ maskedWebhook(row.webhook) }}</span><el-button class="icon-button" text title="复制 Webhook" @click="copyWebhook(row.webhook)"><Copy :size="14" /></el-button></div></template></el-table-column>
      <el-table-column label="启用状态" width="110"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已启用' : '已停用' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="240"><template #default="{ row }"><el-button size="small" @click="edit(row)">编辑</el-button><el-button size="small" type="primary" plain @click="test(row)"><Send :size="14" />测试</el-button><el-button size="small" type="danger" plain @click="remove(row)">删除</el-button></template></el-table-column>
    </el-table>
  </section>
  <section class="mobile-config-list">
    <article v-for="row in bots" :key="row.id" class="mobile-config-item">
      <div class="mobile-config-head"><strong>{{ row.name }}</strong><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已启用' : '已停用' }}</el-tag></div>
      <div class="mobile-webhook"><span>{{ maskedWebhook(row.webhook) }}</span><el-button class="icon-button" text title="复制 Webhook" @click="copyWebhook(row.webhook)"><Copy :size="14" /></el-button></div>
      <div class="mobile-config-actions"><el-button size="small" @click="edit(row)">编辑</el-button><el-button size="small" type="primary" plain @click="test(row)"><Send :size="14" />测试</el-button><el-button size="small" type="danger" plain @click="remove(row)">删除</el-button></div>
    </article>
    <div v-if="!loading && bots.length === 0" class="mobile-config-empty">暂无钉钉配置</div>
  </section>
  <el-dialog v-model="dialog" :title="form.id ? '编辑钉钉配置' : '新增钉钉配置'" width="540px">
    <el-form label-position="top">
      <el-form-item label="配置名称"><el-input v-model="form.name" placeholder="例如：运营通知群" /></el-form-item>
      <el-form-item label="Webhook 地址"><el-input v-model="form.webhook" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="加签密钥"><el-input v-model="form.secret" type="password" show-password /></el-form-item>
      <el-checkbox v-model="form.enabled">启用该配置</el-checkbox>
    </el-form>
    <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="save">保存配置</el-button></template>
  </el-dialog>
</template>

<style scoped>
.webhook-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
.webhook-cell span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #465255; }
.webhook-cell .icon-button { flex: 0 0 30px; width: 30px; height: 30px; }
.mobile-config-list { display: none; }
@media (max-width: 760px) {
  .desktop-config-table { display: none; }
  .mobile-config-list { display: grid; gap: 10px; }
  .mobile-config-item { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 14px; min-width: 0; }
  .mobile-config-head, .mobile-config-actions, .mobile-webhook { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .mobile-config-head strong { font-size: 14px; }
  .mobile-webhook { margin: 12px 0; padding: 9px 10px; background: #f7f9f9; border-radius: 5px; }
  .mobile-webhook span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #596568; font-size: 12px; }
  .mobile-webhook .icon-button { flex: 0 0 30px; width: 30px; height: 30px; }
  .mobile-config-actions { justify-content: flex-end; padding-top: 12px; border-top: 1px solid #edf1f0; }
  .mobile-config-empty { padding: 40px 16px; text-align: center; background: #fff; border: 1px solid var(--border); border-radius: 6px; color: var(--muted); font-size: 13px; }
}
</style>
