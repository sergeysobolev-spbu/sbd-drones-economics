/** Уже вошёл — уводим из формы входа в рабочую область по роли. */

export default defineNuxtRouteMiddleware(() => {
  if (!import.meta.client) return
  const { syncFromStorage, role } = useAuthSession()
  syncFromStorage()
  if (!role.value) return
  if (role.value === "администратор") {
    return navigateTo("/admin/users")
  }
  if (role.value === "разработчик") {
    return navigateTo("/developer/firmware")
  }
  if (role.value === "эксплуатант") {
    return navigateTo("/operator/drones")
  }
})
