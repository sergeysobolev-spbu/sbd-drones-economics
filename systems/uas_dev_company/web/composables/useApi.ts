/** HTTP-клиент к бекенду за nginx (`/api/`). */

export async function apiFetch<T>(
  path: string,
  opts: {
    method?: string
    body?: Record<string, unknown> | object
    headers?: Record<string, string>
  } = {},
) {
  const { token } = useAuthSession()
  const headers: Record<string, string> = {
    ...(opts.headers ?? {}),
  }
  if (token.value) {
    headers.Authorization = `Bearer ${token.value}`
  }

  const method = opts.method || "GET"

  try {
    return await $fetch<T>(path, {
      method,
      headers,
      body: method === "GET" || method === "HEAD" ? undefined : opts.body,
      timeout: 180_000,
    })
  } catch (e: unknown) {
    const x = e as { data?: { error?: string }; message?: string; statusMessage?: string }
    throw new Error(x?.data?.error || x?.message || x?.statusMessage || "request failed")
  }
}
