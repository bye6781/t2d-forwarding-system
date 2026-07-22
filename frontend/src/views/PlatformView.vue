<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus, RefreshCw, Users } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import { planPrice } from '../lib/entitlements'
import MetricStrip from '../components/MetricStrip.vue'
import PageHeader from '../components/PageHeader.vue'

const loading=ref(false); const stats=ref<any>({}); const tenants=ref<any[]>([])
const tenantDialog=ref(false);const memberDialog=ref(false);const selectedTenant=ref<any>({});const members=ref<any[]>([])
const memberForm=ref<any>({id:null,username:'',password:'',email:'',role:'viewer',is_active:true})
const formatDate=(value:string)=>value?new Date(value).toLocaleString('zh-CN',{hour12:false}):'-'
const metrics=computed(()=>[
  {label:'租户总数',value:stats.value.total_tenants||0,note:'不含平台内部租户'},
  {label:'活跃用户',value:stats.value.active_users||0,note:'当前启用账号',tone:'teal'},
  {label:'今日转发',value:stats.value.today_messages||0,note:'全平台消息'},
  {label:'活跃订阅',value:stats.value.active_subscriptions||0,note:'有效套餐',tone:'green'},
])
async function load(){loading.value=true;try{const [a,b]=await Promise.all([api.get('/platform/stats'),api.get('/platform/tenants')]);stats.value=a.data.data;tenants.value=b.data.data}catch(e){ElMessage.error(errorMessage(e))}finally{loading.value=false}}
async function changePlan(row:any,plan:string){try{await api.put(`/platform/tenants/${row.id}/plan`,{plan});row.plan=plan;ElMessage.success('套餐已更新')}catch(e){ElMessage.error(errorMessage(e))}}
async function changeStatus(row:any,status:string){try{await api.put(`/platform/tenants/${row.id}/status`,{status});row.status=status;ElMessage.success('租户状态已更新')}catch(e){ElMessage.error(errorMessage(e))}}
async function openAuthorizations(row:any){selectedTenant.value=row;tenantDialog.value=true;try{const r=await api.get(`/platform/tenants/${row.id}/members`);members.value=r.data.data}catch(e){ElMessage.error(errorMessage(e))}}
function editMember(row?:any){memberForm.value=row?{...row,password:''}:{id:null,username:'',password:'',email:'',role:'viewer',is_active:true};memberDialog.value=true}
async function saveMember(){try{const base=`/platform/tenants/${selectedTenant.value.id}/members`;if(memberForm.value.id)await api.put(`${base}/${memberForm.value.id}`,{role:memberForm.value.role,is_active:memberForm.value.is_active});else await api.post(base,memberForm.value);memberDialog.value=false;await openAuthorizations(selectedTenant.value);ElMessage.success('成员授权已更新')}catch(e){ElMessage.error(errorMessage(e))}}
async function removeMember(row:any){try{await ElMessageBox.confirm('确定删除该成员？','删除确认');await api.delete(`/platform/tenants/${selectedTenant.value.id}/members/${row.id}`);await openAuthorizations(selectedTenant.value)}catch(e){if(e!=='cancel')ElMessage.error(errorMessage(e))}}
onMounted(load)
</script>
<template>
  <PageHeader title="平台管理" description="租户、订阅和平台运行概况"><el-button :loading="loading" @click="load"><RefreshCw :size="15" />刷新</el-button></PageHeader>
  <MetricStrip :items="metrics" />
  <section class="data-panel"><div class="table-toolbar"><div><h2>租户列表</h2><span>共 {{ tenants.length }} 个租户</span></div><el-input clearable placeholder="搜索租户" style="width:240px" /></div>
    <el-table :data="tenants" v-loading="loading" row-key="id"><el-table-column prop="id" label="ID" width="80"/><el-table-column prop="name" label="租户名称" min-width="180"/><el-table-column prop="slug" label="标识" min-width="140"/><el-table-column prop="user_count" label="用户" width="90"/>
      <el-table-column label="套餐" width="220"><template #default="{row}"><el-select :model-value="row.plan" @change="changePlan(row,$event)"><el-option v-for="p in ['free','basic','pro','enterprise']" :key="p" :label="`${p} · ${planPrice(p)}${p==='pro'?' · 无限':''}`" :value="p"/></el-select></template></el-table-column>
      <el-table-column label="状态" width="140"><template #default="{row}"><el-select :model-value="row.status" @change="changeStatus(row,$event)"><el-option label="启用" value="active"/><el-option label="暂停" value="suspended"/></el-select></template></el-table-column>
      <el-table-column label="授权" width="130"><template #default="{row}"><el-button size="small" @click="openAuthorizations(row)"><Users :size="14"/>成员授权</el-button></template></el-table-column>
      <el-table-column label="创建时间" min-width="190"><template #default="{row}">{{ formatDate(row.created_at) }}</template></el-table-column></el-table>
  </section>
  <el-dialog v-model="tenantDialog" :title="`${selectedTenant.name || ''} · 成员授权`" width="760px"><div class="table-toolbar"><span>只有平台管理员可以变更角色和账号状态</span><el-button type="primary" @click="editMember()"><Plus :size="14"/>新增成员</el-button></div><el-table :data="members"><el-table-column prop="username" label="用户名"/><el-table-column prop="email" label="邮箱"/><el-table-column prop="role" label="角色"/><el-table-column label="状态"><template #default="{row}">{{row.is_active?'启用':'停用'}}</template></el-table-column><el-table-column label="操作" width="160"><template #default="{row}"><el-button size="small" :disabled="row.role==='owner'" @click="editMember(row)">编辑</el-button><el-button size="small" type="danger" plain :disabled="row.role==='owner'" @click="removeMember(row)">删除</el-button></template></el-table-column></el-table></el-dialog>
  <el-dialog v-model="memberDialog" :title="memberForm.id?'调整成员授权':'新增成员'" width="480px"><el-form label-position="top"><el-form-item label="用户名"><el-input v-model="memberForm.username" :disabled="Boolean(memberForm.id)"/></el-form-item><el-form-item v-if="!memberForm.id" label="初始密码"><el-input v-model="memberForm.password" type="password" show-password/></el-form-item><el-form-item v-if="!memberForm.id" label="邮箱"><el-input v-model="memberForm.email"/></el-form-item><el-form-item label="角色"><el-select v-model="memberForm.role" style="width:100%"><el-option label="管理员" value="admin"/><el-option label="成员" value="member"/><el-option label="观察者" value="viewer"/></el-select></el-form-item><el-checkbox v-if="memberForm.id" v-model="memberForm.is_active">启用账号</el-checkbox></el-form><template #footer><el-button @click="memberDialog=false">取消</el-button><el-button type="primary" @click="saveMember">保存</el-button></template></el-dialog>
</template>
