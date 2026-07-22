<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Download, RefreshCw } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import MetricStrip from '../components/MetricStrip.vue'
import PageHeader from '../components/PageHeader.vue'

const tab=ref('operations'),loading=ref(false),rows=ref<any[]>([]),total=ref(0),summary=ref<any>({})
const metrics=computed(()=>[
  {label:'操作记录',value:summary.value.total_operations||0,note:'最近 7 天'},
  {label:'登录次数',value:summary.value.total_logins||0,note:`失败 ${summary.value.failed_logins||0}`,tone:'teal'},
  {label:'API 请求',value:summary.value.total_api_calls||0,note:`平均 ${summary.value.avg_api_duration_ms||0}ms`},
])
async function load(){loading.value=true;try{const endpoint=tab.value==='operations'?'operations':tab.value==='logins'?'logins':'requests';const[a,b]=await Promise.all([api.get(`/audit/${endpoint}?limit=100&offset=0`),api.get('/audit/summary')]);rows.value=a.data.data.items;total.value=a.data.data.total;summary.value=b.data.data}catch(error){ElMessage.error(errorMessage(error))}finally{loading.value=false}}
async function download(){try{const r=await api.get('/audit/export',{responseType:'blob'});const url=URL.createObjectURL(r.data);const anchor=document.createElement('a');anchor.href=url;anchor.download='audit_logs.csv';anchor.click();URL.revokeObjectURL(url)}catch(error){ElMessage.error(errorMessage(error))}}
watch(tab,load);onMounted(load)
</script>
<template><PageHeader title="审计日志" description="查看操作记录、登录日志和 API 请求追踪"><el-button @click="load"><RefreshCw :size="15"/>刷新</el-button><el-button @click="download"><Download :size="15"/>导出 CSV</el-button></PageHeader><MetricStrip :items="metrics"/><el-tabs v-model="tab" class="section-tabs"><el-tab-pane label="操作日志" name="operations"/><el-tab-pane label="登录日志" name="logins"/><el-tab-pane label="API 请求" name="requests"/></el-tabs><section class="data-panel"><div class="table-toolbar"><span>共 {{total}} 条记录</span></div><el-table :data="rows" v-loading="loading"><el-table-column prop="created_at" label="时间" min-width="170"/><el-table-column prop="username" label="用户" min-width="120"/><el-table-column v-if="tab==='operations'" prop="action" label="操作"/><el-table-column v-if="tab==='operations'" prop="target" label="目标"/><el-table-column v-if="tab==='logins'" prop="action" label="结果"/><el-table-column v-if="tab==='requests'" prop="method" label="方法" width="90"/><el-table-column v-if="tab==='requests'" prop="path" label="路径" min-width="240"/><el-table-column v-if="tab==='requests'" prop="response_status" label="状态" width="90"/><el-table-column v-if="tab==='requests'" prop="duration_ms" label="耗时(ms)" width="110"/><el-table-column prop="detail" label="详情" show-overflow-tooltip/></el-table></section></template>
