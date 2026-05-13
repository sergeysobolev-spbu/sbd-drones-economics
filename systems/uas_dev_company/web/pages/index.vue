<script setup lang="ts">
/** Корень: перенаправление по роли после проверки токена. */

definePageMeta({
  layout: "default",
})

function go() {
  const { syncFromStorage, role } = useAuthSession()
  syncFromStorage()
  if (!role.value) {
    navigateTo("/login")
    return
  }
  if (role.value === "администратор") {
    navigateTo("/admin/users")
    return
  }
  if (role.value === "разработчик") {
    navigateTo("/developer/firmware")
    return
  }
  navigateTo("/operator/drones")
}

onMounted(() => {
  go()
})
</script>

<template>
  <p class="page muted">
    Перенаправление…
  </p>
</template>

<style scoped>
.muted {
  color: var(--muted);
}
</style>
