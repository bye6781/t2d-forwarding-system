<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Plus, RefreshCw, Send } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'

const endpoint = '/connectors/dingtalk/bots'
const loading = ref(false), dialog = ref(false)
const bots = ref<any[]>([])
const form = reactive<any>({ id: null, name: '', webhook: '', secret: '', enabled: true })
async function load(){loading.value=true;try{bots.value=(await api.get(endpoint)).data.data}catch(error){ElMessage.error(errorMessage(error))}finally{loading.value=false}}
function edit(row?:any){Object.assign(form,row?{...row,webhook:'',secret:''}:{id:null,name:'',webhook:'',secret:'',enabled:true});dialog.value=true}
async function save(){try{const payload:any={name:form.name,enabled:form.enabled};if(form.webhook)payload.webhook=form.webhook;if(form.secret)payload.secret=form.secret;if(form.id)await api.put(`${endpoint}/${form.id}`,payload);else await api.post(endpoint,{...payload,webhook:form.webhook,secret:form.secret||''});dialog.value=false;ElMessage.success('钉钉机器人已保存');await load()}catch(error){ElMessage.error(errorMessage(error))}}
async function test(row:any){try{await api.post(`${endpoint}/${row.id}/test`,{message:'T2D Cloud 测试消息'});ElMessage.success('测试消息已发送')}catch(error){ElMessage.error(errorMessage(error))}}
async function remove(row:any){try{await ElMessageBox.confirm('确定删除此钉钉机器人？','删除确认');await api.delete(`${endpoint}/${row.id}`);await load()}catch(error){if(error!=='cancel')ElMessage.error(errorMessage(error))}}
onMounted(load)
</script>
<template>
  <PageHeader title="钉钉机器人" description="管理接收转发消息的钉钉群自定义机器人"><el-button :loading="loading" @click="load"><RefreshCw :size="15"/>刷新</el-button><el-button type="primary" @click="edit()"><Plus :size="15"/>添加机器人</el-button></PageHeader>
  <section class="data-panel"><el-table :data="bots" v-loading="loading" empty-text="暂无钉钉机器人"><el-table-column prop="name" label="机器人名称" min-width="180"/><el-table-column prop="webhook_masked" label="Webhook" min-width="360" show-overflow-tooltip/><el-table-column label="状态" width="100"><template #default="{row}"><el-tag :type="row.enabled?'success':'info'">{{row.enabled?'启用':'停用'}}</el-tag></template></el-table-column><el-table-column label="操作" width="240"><template #default="{row}"><el-button size="small" @click="edit(row)">编辑</el-button><el-button size="small" type="primary" plain @click="test(row)"><Send :size="14"/>测试</el-button><el-button size="small" type="danger" plain @click="remove(row)">删除</el-button></template></el-table-column></el-table></section>
  <el-dialog v-model="dialog" :title="form.id?'编辑钉钉机器人':'添加钉钉机器人'" width="560px"><el-form label-position="top"><el-form-item label="机器人名称"><el-input v-model="form.name"/></el-form-item><el-form-item label="Webhook"><el-input v-model="form.webhook" type="textarea" :rows="3"/></el-form-item><el-form-item label="加签密钥"><el-input v-model="form.secret" type="password" show-password/></el-form-item><el-checkbox v-model="form.enabled">启用机器人</el-checkbox></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template></el-dialog>
</template>
