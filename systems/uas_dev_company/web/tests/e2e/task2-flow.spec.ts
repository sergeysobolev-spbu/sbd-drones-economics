/**
 * Задача 2 + 5: сквозной поток через UI после globalSetup (/api/bootstrap-admin).
 * Требует запущенный docker-compose с nginx на E2E_BASE_URL.
 */

import { expect, test } from "@playwright/test"

const adminUser = process.env.E2E_ADMIN_USER ?? "e2e-admin"
const adminPass = process.env.E2E_ADMIN_PASSWORD ?? "e2e-admin-pass"

async function login(page: import("@playwright/test").Page, user: string, pass: string) {
  await page.goto("/login")
  await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 60_000 })
  await page.getByTestId("login-username").fill(user)
  await page.getByTestId("login-password").fill(pass)
  // Avoid flaky "element not stable" on the submit button (focus/layout).
  await page.getByTestId("login-password").press("Enter")
  await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 150_000 })
}

async function logout(page: import("@playwright/test").Page) {
  await page.getByTestId("logout").click({ force: true })
  await expect(page.getByTestId("login-username")).toBeVisible({ timeout: 10_000 })
}

test.describe.configure({ mode: "serial" })

test.describe("Задача 2 — полный поток UI", () => {
  test("администратор, разработчик, эксплуатант и сценарии ТЗ", async ({ page }) => {
    const id = `${Date.now()}`
    const devName = `dev_${id}`
    const opName = `op_${id}`
    const devPass = "DevPass!1"
    const opPass = "OpPass!1"
    const fwId = `fw-e2e-${id}`
    const serial = `DRONE-${id}`
    let certificateId = ""

    await login(page, adminUser, adminPass)

    await expect(page.getByTestId("nav-admin-users")).toBeVisible()

    await page.getByTestId("user-create-username").fill(devName)
    await page.getByTestId("user-create-role").selectOption("разработчик")
    await page.getByTestId("user-create-password").fill(devPass)
    await page.getByTestId("user-create-submit").click({ force: true })
    await expect(page.getByTestId("users-table")).toContainText(devName)

    await page.getByTestId("user-create-username").fill(opName)
    await page.getByTestId("user-create-role").selectOption("эксплуатант")
    await page.getByTestId("user-create-password").fill(opPass)
    await page.getByTestId("user-create-submit").click({ force: true })
    await expect(page.getByTestId("users-table")).toContainText(opName)

    await page.getByTestId(`user-block-${opName}`).click({ force: true })
    await logout(page)

    await page.goto("/login")
    await page.getByTestId("login-username").fill(opName)
    await page.getByTestId("login-password").fill(opPass)
    await page.getByTestId("login-password").press("Enter")
    await expect(page.getByTestId("login-error")).toBeVisible({ timeout: 120_000 })

    await login(page, adminUser, adminPass)
    await page.getByTestId(`user-block-${opName}`).click({ force: true })
    await logout(page)

    await login(page, opName, opPass)

    await logout(page)
    await login(page, devName, devPass)

    await page.getByTestId("nav-dev-fw").click({ force: true })
    await page.getByTestId("fw-id").fill(fwId)
    await page.getByTestId("fw-supplier").fill("contractor-team")
    await page.getByTestId("fw-drone-type").fill("survey")
    await page.getByTestId("fw-version").fill("2026.e2e.1")
    await page.getByTestId("fw-hash").fill(`sha256-e2e-${id}`)
    await page.getByTestId("fw-goals").fill("ЦБ-1\nЦБ-3")
    await page.getByTestId("fw-proof").fill("proof-e2e")
    await page.getByTestId("fw-submit").click({ force: true })
    await expect(page.getByTestId("fw-result")).toContainText(fwId)

    await page.getByTestId("certify-firmware-id").fill(fwId)
    await page.getByTestId("certify-submit").click({ force: true })
    await expect(page.getByTestId("certify-result")).toContainText("certified")
    await expect(page.getByTestId("certify-result")).toContainText("1000")

    certificateId =
      (
        await page
          .getByTestId("certify-result")
          .locator("code")
          .first()
          .textContent()
      )
        ?.trim() ?? ""
    expect(certificateId.length).toBeGreaterThan(8)

    await page.getByTestId("nav-dev-cert").click({ force: true })
    await expect(page.getByTestId("cert-table")).toContainText(fwId)
    await expect(page.getByTestId("cert-table")).toContainText("ЦБ-1")

    await page.getByTestId("nav-dev-drones").click({ force: true })
    await page.getByTestId("drone-cert-select").selectOption({ value: certificateId.trim() })
    await expect(page.getByTestId("drone-goal-0")).toBeChecked()
    await page.getByTestId("drone-serial").fill(serial)
    await page.getByTestId("drone-type").fill("survey")
    await page.getByTestId("drone-price").fill("55000")
    await page.getByTestId("drone-register-submit").click({ force: true })
    await expect(page.getByTestId("dev-drones-table")).toContainText(serial)
    await expect(page.getByTestId("dev-drones-table")).toContainText("ЦБ-1")

    await logout(page)
    await login(page, opName, opPass)

    await expect(page.getByTestId("op-drones-table")).toContainText(serial)
    await expect(page.getByTestId("op-drones-table")).toContainText("ЦБ-1")
    await page.getByTestId(`buy-${serial}`).click({ force: true })
    await expect(page.getByTestId("op-msg")).toContainText("Покупка", { timeout: 15_000 })
  })

  test("настройки: панель открывается и закрывается", async ({ page }) => {
    await login(page, adminUser, adminPass)
    await page.getByTestId("settings-open").click({ force: true })
    await expect(page.getByTestId("settings-panel")).toBeVisible()
    await page.getByTestId("settings-close").click({ force: true })
    await expect(page.getByTestId("settings-panel")).toBeHidden()
  })

  test("светлая тема задаёт класс html.theme-light", async ({ page }) => {
    await login(page, adminUser, adminPass)
    await page.getByTestId("settings-open").click({ force: true })
    const lightCheckbox = page.locator('label:has-text("Светлая тема") input[type="checkbox"]')
    await lightCheckbox.check({ force: true })
    const cls = await page.evaluate(() => document.documentElement.className)
    expect(cls.includes("theme-light")).toBeTruthy()
    await lightCheckbox.uncheck({ force: true })
    const clsDark = await page.evaluate(() => document.documentElement.className)
    expect(clsDark.includes("theme-light")).toBeFalsy()
  })

  test("фильтр сертификатов и выбор только части ЦБ дрона", async ({ page }) => {
    const id = `${Date.now()}-tg`
    await login(page, adminUser, adminPass)

    await page.getByTestId("user-create-username").fill(`dev_goal_${id}`)
    await page.getByTestId("user-create-role").selectOption("разработчик")
    await page.getByTestId("user-create-password").fill("DevGoal!9")
    await page.getByTestId("user-create-submit").click({ force: true })
    await logout(page)

    const devName = `dev_goal_${id}`
    await login(page, devName, "DevGoal!9")

    await page.goto("/developer/firmware")
    const fwUid = `fw-goals-${id}`
    await page.getByTestId("fw-id").fill(fwUid)
    await page.getByTestId("fw-supplier").fill("tg")
    await page.getByTestId("fw-drone-type").fill("test")
    await page.getByTestId("fw-version").fill("1")
    await page.getByTestId("fw-hash").fill(`sha256-${id}`)
    await page.getByTestId("fw-goals").fill("ЦБ-1\nЦБ-2\nЦБ-3")
    await page.getByTestId("fw-proof").fill("proof")
    await page.getByTestId("fw-submit").click({ force: true })
    await expect(page.getByTestId("fw-result")).toContainText(fwUid)

    await page.getByTestId("certify-firmware-id").fill(fwUid)
    await page.getByTestId("certify-submit").click({ force: true })
    await expect(page.getByTestId("certify-result")).toContainText("cert-drone")

    const cert =
      (
        await page.getByTestId("certify-result").locator("code").first().textContent()
      )?.trim() ?? ""

    await page.goto("/developer/drones")
    await page.getByTestId("drone-cert-filter").fill(fwUid.slice(0, 12))
    await page.getByTestId("drone-cert-select").selectOption({ value: cert })

    await page.getByTestId("drone-goals-none").click({ force: true })
    await page.getByTestId("drone-goal-0").check({ force: true })

    await page.getByTestId("drone-serial").fill(`SN-G-${id}`)
    await page.getByTestId("drone-type").fill("test")
    await page.getByTestId("drone-price").fill("100")
    await page.getByTestId("drone-register-submit").click({ force: true })

    await expect(page.getByTestId("dev-drones-table")).toContainText(`SN-G-${id}`, { timeout: 20_000 })
    await expect(page.getByTestId("dev-drones-table")).toContainText("ЦБ-1")
  })
})
