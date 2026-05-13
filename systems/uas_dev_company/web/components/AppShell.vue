<script setup lang="ts">
/** Оболочка приложения: боковая панель, верхняя строка с настройками и выходом. */

import { useSidebarPrefs } from "~/composables/useSidebarPrefs"

withDefaults(defineProps<{ settingsOpen?: boolean }>(), {
  settingsOpen: false,
})
const emit = defineEmits<{
  logout: []
  openSettings: []
  closeSettings: []
  toggleSidebar: []
}>()

const { sidebarHidden, toggleSidebarHidden } = useSidebarPrefs()

function toggleMob() {
  toggleSidebarHidden()
}
</script>

<template>
  <div class="shell" data-testid="app-shell">
    <aside v-if="!sidebarHidden" class="sidebar" data-testid="sidebar">
      <div class="brand">
        Разработчик БАС
      </div>
      <nav class="nav">
        <slot name="nav" />
      </nav>
    </aside>

    <div class="shell-main">
      <header class="topbar">
        <button type="button" class="icon-btn mob-only" aria-label="Меню" @click="toggleMob">
          ≡
        </button>
        <div class="topbar-title">
          <slot name="title" />
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn-ghost" data-testid="settings-open" @click="emit('openSettings')">
            Настройки
          </button>
          <button type="button" class="btn-ghost" data-testid="logout" @click="emit('logout')">
            Выход
          </button>
        </div>
      </header>
      <main class="shell-content">
        <slot />
      </main>
    </div>
    <Teleport to="body">
      <div v-if="settingsOpen" class="backdrop" data-testid="settings-backdrop" @click.self="emit('closeSettings')" />
      <div v-if="settingsOpen" class="settings-drawer panel" role="dialog" aria-label="Настройки" data-testid="settings-panel">
        <h2 class="panel-title">Настройки</h2>
        <slot name="settings" />
        <button type="button" class="btn-secondary" data-testid="settings-close" @click="emit('closeSettings')">Закрыть</button>
      </div>
    </Teleport>
  </div>
</template>
