/** Черновик формы в sessionStorage: сохранение при переходах между страницами. */

import type { Ref } from "vue"

export function useFormDraft<T extends Record<string, unknown>>(storageKey: string, factory: () => T): Ref<T> {
  const data = ref(factory()) as Ref<T>

  function mergeFromStorage() {
    if (!import.meta.client) return
    const raw = sessionStorage.getItem(storageKey)
    if (!raw) return
    try {
      const parsed = JSON.parse(raw) as Partial<T>
      data.value = { ...factory(), ...parsed } as T
    } catch {
      /* ignore malformed */
    }
  }

  if (import.meta.client) {
    mergeFromStorage()
    watch(
      data,
      (v) => sessionStorage.setItem(storageKey, JSON.stringify(v)),
      { deep: true },
    )
  }

  return data
}
