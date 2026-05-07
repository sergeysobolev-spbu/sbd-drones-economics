<script setup lang="ts">
/** Интерфейс эксплуатанта. */

const settingsOpen = ref(false)
const { clearToken, syncFromStorage, persistTheme } = useAuthSession()
const { sidebarHidden, persist, load } = useSidebarPrefs()
const themeLight = ref(false)

function logout() {
  clearToken()
  navigateTo("/login")
}

onMounted(() => {
  syncFromStorage()
  load()
  themeLight.value = typeof localStorage !== "undefined" && localStorage.getItem("uas_theme") === "light"
})

function applyTheme(light: boolean) {
  themeLight.value = light
  persistTheme(light)
}
</script>

<template>
  <AppShell
    :settings-open="settingsOpen"
    @logout="logout"
    @open-settings="settingsOpen = true"
    @close-settings="settingsOpen = false"
  >
    <template #nav>
      <NuxtLink to="/operator/drones" data-testid="nav-op-drones">Дроны</NuxtLink>
    </template>
    <template #title>
      Панель эксплуатанта
    </template>
    <template #settings>
      <div class="stack">
        <label class="row-check">
          <input type="checkbox" :checked="sidebarHidden" @change="persist(($event.target as HTMLInputElement).checked)">
          <span>Скрыть боковую панель</span>
        </label>
        <label class="row-check">
          <input type="checkbox" :checked="themeLight" @change="applyTheme(($event.target as HTMLInputElement).checked)">
          <span>Светлая тема интерфейса</span>
        </label>
      </div>
    </template>
    <slot />
  </AppShell>
</template>

<style scoped>
.row-check {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
</style>
