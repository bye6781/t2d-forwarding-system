<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'

const endpoint='/forwarding/records'
const loading=ref(false),rows=ref<any[]>([]),total=ref(0),status=ref(''),page=ref(1),limit=50
async function load(){loading.value=true;try{const offset=(page.value-1)*limit;const query=status.value?`&status=${status.value}`:'';const r=await api.get(`${endpoint}?limit=${limit}&offset=${offset}${query}`);rows.value=r.data.data.items;total.value=r.data.data.total}catch(error){ElMessage.error(errorMessage(error))}finally{loading.value=false}}
function filter(){page.value=1;load()}
onMounted(load)
</script>
<template><PageHeader title="转发记录" description="查看消息转发历史、处理结果和错误原因"><el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="filter"><el-option label="成功" value="success"/><el-option label="失败" value="failed"/></el-select><el-button @click="load"><RefreshCw :size="15"/>刷新</el-button></PageHeader><section class="data-panel"><el-table :data="rows" v-loading="loading" empty-text="暂无转发记录"><el-table-column prop="telegram_chat_id" label="来源 Chat" min-width="140"/><el-table-column prop="dingtalk_bot_id" label="目标机器人" min-width="130"/><el-table-column prop="message_type" label="类型" width="100"/><el-table-column prop="content_preview" label="内容预览" min-width="260" show-overflow-tooltip/><el-table-column label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='success'?'success':'danger'">{{row.status}}</el-tag></template></el-table-column><el-table-column prop="error_message" label="错误" min-width="180" show-overflow-tooltip/><el-table-column prop="processing_time_ms" label="耗时(ms)" width="100"/><el-table-column prop="created_at" label="时间" min-width="180"/></el-table><div class="pagination-row"><el-pagination v-model:current-page="page" :page-size="limit" :total="total" layout="prev, pager, next, total" @current-change="load"/></div></section></template>
