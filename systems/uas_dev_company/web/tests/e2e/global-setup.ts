/**
 * Однократная инициализация БД через API перед e2e
 * (на пустой базе создаётся администратор; если уже есть — ответ можно игнорировать).
 * Дополнительно ждём, пока шина/API начнут отвечать на логин (холодный старт Docker).
 */

import type { FullConfig } from "@playwright/test"

async function waitForHealth(base: string, timeoutMs: number) {
  const deadline = Date.now() + timeoutMs
  let lastStatus = 0
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`${base}/health`, { signal: AbortSignal.timeout(15_000) })
      lastStatus = r.status
      if (r.ok) return
    } catch {
      /* nginx / gateway starting */
    }
    await new Promise((r) => setTimeout(r, 3000))
  }
  throw new Error(`e2e globalSetup: ${base}/health not OK within ${timeoutMs}ms (last HTTP ${lastStatus})`)
}

/** Ждём, пока nginx отдаёт страницу входа (web_portal), а не 502. */
async function waitForLoginPage(base: string, timeoutMs: number) {
  const deadline = Date.now() + timeoutMs
  let lastStatus = 0
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`${base}/login`, {
        signal: AbortSignal.timeout(15_000),
        redirect: "follow",
      })
      lastStatus = r.status
      if (r.ok) return
    } catch {
      /* web_portal / nginx starting */
    }
    await new Promise((r) => setTimeout(r, 2000))
  }
  throw new Error(`e2e globalSetup: ${base}/login (HTML) not OK within ${timeoutMs}ms (last HTTP ${lastStatus})`)
}

async function waitForLoginReachable(base: string, username: string, password: string) {
  const deadline = Date.now() + 300_000
  let lastStatus = 0
  while (Date.now() < deadline) {
    try {
      const loginRes = await fetch(`${base}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        signal: AbortSignal.timeout(95_000),
      })
      lastStatus = loginRes.status
      if (loginRes.ok) return
    } catch {
      /* cold Kafka / gateway */
    }
    await new Promise((r) => setTimeout(r, 4000))
  }
  throw new Error(
    `e2e globalSetup: /api/login did not succeed within deadline (last HTTP ${lastStatus}). ` +
      `Check stack (nginx, api_gateway, kafka, security_monitor, user_management_worker) and GATEWAY_AUTH_PROXY_TIMEOUT_S.`,
  )
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const base = (process.env.E2E_BASE_URL ?? "http://127.0.0.1:8080").replace(/\/$/, "")
  const username = process.env.E2E_ADMIN_USER ?? "e2e-admin"
  const password = process.env.E2E_ADMIN_PASSWORD ?? "e2e-admin-pass"

  await waitForHealth(base, 240_000)
  await waitForLoginPage(base, 180_000)

  await fetch(`${base}/api/bootstrap-admin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    signal: AbortSignal.timeout(125_000),
  }).catch(() => undefined)

  await waitForLoginReachable(base, username, password)
}
