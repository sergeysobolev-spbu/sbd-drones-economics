/** Сессия: JWT из localStorage (клиент только). */

const STORAGE_KEY = "uas_access_token"

export type UasRole = "администратор" | "разработчик" | "эксплуатант"

function decodeJwtJsonSegment(seg: string): string {
  const b64 = seg.replace(/-/g, "+").replace(/_/g, "/")
  const pad = "=".repeat((4 - (b64.length % 4)) % 4)
  const binary = typeof atob === "function" ? atob(b64 + pad) : ""
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return new TextDecoder().decode(bytes)
}

export function parseJwtPayload(token: string): { sub?: string; role?: string; exp?: number } | null {
  try {
    const parts = token.split(".")
    if (parts.length !== 3) return null
    const json = decodeJwtJsonSegment(parts[1])
    return JSON.parse(json) as { sub?: string; role?: string; exp?: number }
  } catch {
    return null
  }
}

export function useAuthSession() {
  const token = useState<string | null>("uas_auth_token", () => null)

  function syncFromStorage() {
    if (import.meta.client) {
      token.value = localStorage.getItem(STORAGE_KEY)
      applyHtmlTheme(localStorage.getItem("uas_theme"))
    }
  }

  function setToken(accessToken: string) {
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, accessToken)
      token.value = accessToken
    }
  }

  function clearToken() {
    if (import.meta.client) {
      localStorage.removeItem(STORAGE_KEY)
      token.value = null
    }
  }

  const username = computed(() => {
    const t = token.value
    if (!t) return null
    return parseJwtPayload(t)?.sub ?? null
  })

  const role = computed(() => {
    const t = token.value
    if (!t) return null
    const r = parseJwtPayload(t)?.role
    if (r === "администратор" || r === "разработчик" || r === "эксплуатант") return r
    return null
  })

  return {
    token,
    username,
    role,
    setToken,
    clearToken,
    syncFromStorage,
    persistTheme,
  }
}

function applyHtmlTheme(theme: string | null) {
  if (!import.meta.client) return
  const root = document.documentElement
  if (theme === "light") {
    root.classList.add("theme-light")
  } else {
    root.classList.remove("theme-light")
  }
}

export function persistTheme(light: boolean) {
  if (!import.meta.client) return
  if (light) {
    localStorage.setItem("uas_theme", "light")
    document.documentElement.classList.add("theme-light")
  } else {
    localStorage.setItem("uas_theme", "dark")
    document.documentElement.classList.remove("theme-light")
  }
}
