/** Предпочтения сайдбара (скрыть/показать колонку навигации). */

export function useSidebarPrefs() {
  const sidebarHidden = useState<boolean>("uas_sidebar_hidden", () => false)

  function load() {
    if (!import.meta.client) return
    sidebarHidden.value = localStorage.getItem("uas_sidebar_hidden") === "1"
  }

  function persist(val: boolean) {
    sidebarHidden.value = val
    if (import.meta.client) {
      localStorage.setItem("uas_sidebar_hidden", val ? "1" : "0")
    }
  }

  function toggleSidebarHidden() {
    persist(!sidebarHidden.value)
  }

  onMounted(() => {
    load()
  })

  return {
    sidebarHidden,
    persist,
    toggleSidebarHidden,
    load,
  }
}
