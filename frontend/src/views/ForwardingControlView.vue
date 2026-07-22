<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CircleStop, Play, RefreshCw } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import MetricStrip from '../components/MetricStrip.vue'
import PageHeader from '../components/PageHeader.vue'

const endpoint='/forwarding/runtime'
const loading=ref(false),runtime=ref<any>({accounts:[]}),dashboard=ref<any>({})
const metrics=computed(()=>[
  {label:'引擎状态',value:runtime.value.running?'运行中':'已停止',note:'仅影响当前租户',tone:runtime.value.running?'green':''},
  {label:'已授权账号',value:runtime.value.accounts?.length||0,note:'Telegram 账号'},
  {label:'今日转发',value:dashboard.value.today_messages||0,note:`成功 ${dashboard.value.successful_forwards||0}`,tone:'teal'},
  {label:'失败转发',value:dashboard.value.failed_forwards||0,note:'今日'},
])
async function load(){loading.value=true;try{const[a,b]=await Promise.all([api.get(endpoint),api.get('/forwarding/dashboard')]);runtime.value=a.data.data;dashboard.value=b.data.data}catch(error){ElMessage.error(errorMessage(error))}finally{loading.value=false}}
async function toggle(action:'start'|'stop'){try{await api.post(`${endpoint}/${action}`);ElMessage.success(action==='start'?'转发引擎已启动':'转发引擎已停止');await load()}catch(error){ElMessage.error(errorMessage(error))}}
onMounted(load)
</script>
<template><PageHeader title="转发控制" description="启动或停止当前租户的消息转发引擎"><el-button @click="load"><RefreshCw :size="15"/>刷新</el-button><el-button v-if="!runtime.running" type="primary" @click="toggle('start')"><Play :size="15"/>启动转发</el-button><el-button v-else type="danger" plain @click="toggle('stop')"><CircleStop :size="15"/>停止转发</el-button></PageHeader><MetricStrip :items="metrics"/><section class="data-panel"><div class="panel-title">Telegram 账号连接状态</div><el-table :data="runtime.accounts||[]" empty-text="暂无已授权 Telegram 账号"><el-table-column prop="name" label="账号"/><el-table-column prop="phone" label="手机号"/><el-table-column label="连接状态"><template #default="{row}"><el-tag :type="row.connected?'success':'info'">{{row.connected?'已连接':'未连接'}}</el-tag></template></el-table-column></el-table></section></template>
