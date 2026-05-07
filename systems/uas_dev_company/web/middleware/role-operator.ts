/** Только роль эксплуатант. */

export default defineNuxtRouteMiddleware(() => {
  if (!import.meta.client) return
  const { syncFromStorage, role } = useAuthSession()
  syncFromStorage()
  if (!role.value) {
    return navigateTo("/login")
  }
  if (role.value !== "эксплуатант") {
    return navigateTo("/")
  }
})
