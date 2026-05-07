/**
 * Однократная инициализация БД через API перед e2e
 * (на пустой базе создаётся администратор; если уже есть — ответ можно игнорировать).
 * Дополнительно ждём, пока шина/API начнут отвечать на логин (холодный старт Docker).
 */

import type { FullConfig } from "@playwright/test"

async function waitForLoginReachable(base: string, username: string, password: string) {
  const deadline = Date.now() + 180_000
  while (Date.now() < deadline) {
    try {
      const loginRes = await fetch(`${base}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        signal: AbortSignal.timeout(125_000),
      })
      if (loginRes.ok) return
    } catch {
      /* cold Kafka / gateway */
    }
    await new Promise((r) => setTimeout(r, 4000))
  }
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const base = (process.env.E2E_BASE_URL ?? "http://127.0.0.1:8080").replace(/\/$/, "")
  const username = process.env.E2E_ADMIN_USER ?? "e2e-admin"
  const password = process.env.E2E_ADMIN_PASSWORD ?? "e2e-admin-pass"

  await fetch(`${base}/api/bootstrap-admin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    signal: AbortSignal.timeout(125_000),
  }).catch(() => undefined)

  await waitForLoginReachable(base, username, password)
}
