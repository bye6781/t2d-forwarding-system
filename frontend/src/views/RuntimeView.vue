<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CircleStop, Play, RefreshCw } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import MetricStrip from '../components/MetricStrip.vue';import PageHeader from '../components/PageHeader.vue'
const loading=ref(false),runtime=ref<any>({accounts:[]}),records=ref<any[]>([]),total=ref(0);const metrics=computed(()=>[{label:'引擎状态',value:runtime.value.running?'运行中':'已停止',note:'仅影响当前租户',tone:runtime.value.running?'green':''},{label:'授权来源',value:runtime.value.accounts?.length||0,note:'Telegram 账号'},{label:'转发记录',value:total.value,note:'历史记录',tone:'teal'}])
async function load(){loading.value=true;try{const[a,b]=await Promise.all([api.get('/forwarding/runtime'),api.get('/forwarding/records?limit=50&offset=0')]);runtime.value=a.data.data;records.value=b.data.data.items;total.value=b.data.data.total}catch(e){ElMessage.error(errorMessage(e))}finally{loading.value=false}}
async function toggle(action:string){try{await api.post(`/forwarding/runtime/${action}`);ElMessage.success(action==='start'?'转发已启动':'转发已停止');await load()}catch(e){ElMessage.error(errorMessage(e))}}
onMounted(load)
</script>
<template><PageHeader title="运行中心" description="控制当前租户转发任务并查看投递结果"><el-button @click="load"><RefreshCw :size="15"/>刷新</el-button><el-button v-if="!runtime.running" type="primary" @click="toggle('start')"><Play :size="15"/>启动</el-button><el-button v-else type="danger" plain @click="toggle('stop')"><CircleStop :size="15"/>停止</el-button></PageHeader><MetricStrip :items="metrics"/><section class="data-panel"><div class="panel-title">最近转发记录</div><el-table :data="records" v-loading="loading"><el-table-column prop="telegram_chat_id" label="来源 Chat"/><el-table-column prop="dingtalk_bot_id" label="目标 Bot"/><el-table-column prop="message_type" label="类型" width="100"/><el-table-column prop="content_preview" label="内容" show-overflow-tooltip/><el-table-column label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='success'?'success':'danger'">{{row.status}}</el-tag></template></el-table-column><el-table-column prop="processing_time_ms" label="耗时(ms)" width="110"/><el-table-column prop="created_at" label="时间" min-width="170"/></el-table></section></template>
