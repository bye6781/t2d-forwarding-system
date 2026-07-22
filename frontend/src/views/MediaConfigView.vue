<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { api, errorMessage } from '../lib/api'
import PageHeader from '../components/PageHeader.vue'

const endpoint='/policies/media'
const loading=ref(false),testType=ref('photo'),testSize=ref(1),testResult=ref('')
const policy=reactive<any>({max_file_size_bytes:52428800,allowed_types:['photo','video','document'],thumbnail_enabled:true,thumbnail_max_width:320,thumbnail_quality:75,forward_as_link:false})
async function load(){loading.value=true;try{Object.assign(policy,(await api.get(endpoint)).data.data)}catch(error){ElMessage.error(errorMessage(error))}finally{loading.value=false}}
async function save(){try{await api.put(endpoint,policy);ElMessage.success('媒体配置已保存')}catch(error){ElMessage.error(errorMessage(error))}}
async function test(){try{const r=await api.post(`${endpoint}/test`,{media_type:testType.value,file_size_bytes:testSize.value*1048576});testResult.value=r.data.data.allowed?'允许转发':`拒绝：${r.data.data.reason||'不符合策略'}`}catch(error){ElMessage.error(errorMessage(error))}}
onMounted(load)
</script>
<template><PageHeader title="媒体配置" description="管理媒体大小、允许类型、缩略图和链接转发策略"><el-button @click="load"><RefreshCw :size="15"/>刷新</el-button><el-button type="primary" @click="save">保存配置</el-button></PageHeader><section class="form-panel"><el-form label-position="top" class="settings-form"><el-form-item label="最大文件大小 (MB)"><el-input-number :model-value="Math.round(policy.max_file_size_bytes/1048576)" :min="1" :max="100" @change="policy.max_file_size_bytes=Number($event)*1048576"/></el-form-item><el-form-item label="允许的媒体类型"><el-checkbox-group v-model="policy.allowed_types"><el-checkbox v-for="type in ['photo','video','document','audio','voice','sticker']" :key="type" :value="type">{{type}}</el-checkbox></el-checkbox-group></el-form-item><el-form-item label="缩略图"><el-switch v-model="policy.thumbnail_enabled"/></el-form-item><el-form-item label="缩略图最大宽度"><el-input-number v-model="policy.thumbnail_max_width" :min="64" :max="4096"/></el-form-item><el-form-item label="缩略图质量"><el-slider v-model="policy.thumbnail_quality"/></el-form-item><el-checkbox v-model="policy.forward_as_link">超限媒体按公开链接转发</el-checkbox></el-form></section><section class="data-panel media-test"><div class="panel-title">策略测试</div><div class="policy-test"><el-select v-model="testType"><el-option v-for="type in ['photo','video','document','audio','voice','sticker']" :key="type" :label="type" :value="type"/></el-select><el-input-number v-model="testSize" :min="0" :max="500"/><el-button @click="test">测试</el-button><span>{{testResult}}</span></div></section></template>
