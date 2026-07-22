<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, RadioTower, Sun } from 'lucide-vue-next'
import { useTheme } from '../composables/useTheme'
import { buildNavigation } from '../router/navigation'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const mobileOpen = ref(false)
const navigation = computed(() => buildNavigation(auth.user))
const pageTitle = computed(() => String(route.meta.title || 'T2D Cloud'))
const { theme, themeToggleLabel, applyTheme, toggleTheme } = useTheme()

function signOut() { auth.logout(); router.replace('/login') }
function unauthorized() { signOut() }

onMounted(() => {
  applyTheme()
  window.addEventListener('t2d:unauthorized', unauthorized)
})
onUnmounted(() => window.removeEventListener('t2d:unauthorized', unauthorized))
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <div class="app-frame" :class="{ collapsed }">
    <aside class="sidebar" :class="{ open: mobileOpen }">
      <div class="brand">
        <span class="brand-mark">T2D</span>
        <div v-if="!collapsed" class="brand-copy"><strong>T2D Cloud</strong><small>Forwarding Console</small></div>
      </div>
      <nav aria-label="主导航">
        <section v-for="group in navigation" :key="group.label" class="nav-group" :aria-label="group.label">
          <span v-if="!collapsed" class="nav-label">{{ group.label }}</span>
          <router-link v-for="item in group.items" :key="item.key" :to="item.path" :title="collapsed ? item.label : undefined" @click="mobileOpen=false">
            <component :is="item.icon" :size="17" :stroke-width="1.7" /><span v-if="!collapsed">{{ item.label }}</span>
          </router-link>
        </section>
      </nav>
      <button class="collapse-button" :aria-label="collapsed ? '展开菜单' : '收起菜单'" @click="collapsed=!collapsed">
        <PanelLeftOpen v-if="collapsed" :size="17" /><PanelLeftClose v-else :size="17" />
        <span v-if="!collapsed">收起菜单</span>
      </button>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <button class="icon-button mobile-menu" aria-label="打开菜单" @click="mobileOpen=true"><Menu :size="20" /></button>
        <div class="topbar-trail"><i /><strong>{{ pageTitle }}</strong></div>
        <div class="network-state"><RadioTower :size="14" /><span>消息网络</span><i /><i /><i /></div>
        <div class="account">
          <button class="theme-toggle" :aria-label="themeToggleLabel" :title="themeToggleLabel" @click="toggleTheme"><Sun v-if="theme==='dark'" :size="17"/><Moon v-else :size="17"/></button>
          <span class="avatar">{{ auth.user?.username?.slice(0,1).toUpperCase() }}</span>
          <div class="account-copy"><b>{{ auth.user?.username }}</b><small>{{ auth.user?.is_platform_admin ? '平台管理员' : auth.user?.role }}</small></div>
          <button class="icon-button" aria-label="退出登录" title="退出登录" @click="signOut"><LogOut :size="18" /></button>
        </div>
      </header>
      <main id="main-content" class="content" tabindex="-1">
        <router-view v-slot="{ Component, route: viewRoute }">
          <Transition name="route-shift" mode="out-in">
            <div :key="viewRoute.path" class="route-surface">
              <component :is="Component" />
            </div>
          </Transition>
        </router-view>
      </main>
    </div>
    <div v-if="mobileOpen" class="scrim" aria-hidden="true" @click="mobileOpen=false"></div>
  </div>
</template>
