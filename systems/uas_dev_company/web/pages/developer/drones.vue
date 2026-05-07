<script setup lang="ts">
/** Реестр дронов разработчика и регистрация новых. */

definePageMeta({
  layout: "developer",
  middleware: "role-developer",
})

type CertRow = {
  certificate_id: string
  firmware_id: string
  drone_type?: string
  security_goals?: string[]
}

const reg = useFormDraft("uas_draft_developer_drones", () => ({
  serial_number: "",
  drone_type: "",
  price: 0,
  selected_certificate_id: "",
  goal_toggles: {} as Record<string, boolean>,
  cert_filter: "",
}))

const drones = ref<Record<string, unknown>[]>([])
const certs = ref<CertRow[]>([])
const loaded = ref(false)
const msg = ref("")
const err = ref("")

const filteredCerts = computed(() => {
  const q = reg.value.cert_filter.trim().toLowerCase()
  if (!q) return certs.value
  return certs.value.filter(
    (c) =>
      String(c.certificate_id).toLowerCase().includes(q) ||
      String(c.firmware_id).toLowerCase().includes(q) ||
      String(c.drone_type ?? "").toLowerCase().includes(q),
  )
})

const selectedCertGoals = computed(() => {
  const id = reg.value.selected_certificate_id
  if (!id) return [] as string[]
  const row = certs.value.find((c) => c.certificate_id === id)
  const g = row?.security_goals
  return Array.isArray(g) ? g : []
})

function toggleAllGoals(on: boolean) {
  const next = { ...reg.value.goal_toggles }
  for (const g of selectedCertGoals.value) next[g] = on
  reg.value.goal_toggles = next
}

function applyCertSelection(certId: string) {
  reg.value.selected_certificate_id = certId
  const row = certs.value.find((c) => c.certificate_id === certId)
  if (!row) return
  if (reg.value.drone_type.trim() === "") {
    reg.value.drone_type = String(row.drone_type ?? "").trim()
  }
  const next: Record<string, boolean> = {}
  for (const g of Array.isArray(row.security_goals) ? row.security_goals : []) {
    next[g] = true
  }
  reg.value.goal_toggles = next
}

async function loadCerts() {
  try {
    const res = await apiFetch<{ certificates: CertRow[] }>("/api/certificates")
    certs.value = res.certificates ?? []
    if (reg.value.selected_certificate_id && certs.value.some((c) => c.certificate_id === reg.value.selected_certificate_id)) {
      applyCertSelection(reg.value.selected_certificate_id)
    }
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}

async function load() {
  err.value = ""
  try {
    const res = await apiFetch<{ drones: Record<string, unknown>[] }>("/api/drones")
    drones.value = res.drones
  } catch (e: unknown) {
    err.value = (e as Error).message
  } finally {
    loaded.value = true
  }
}

function collectSelectedGoals(): string[] {
  return selectedCertGoals.value.filter((g) => reg.value.goal_toggles[g])
}

async function register() {
  msg.value = ""
  err.value = ""
  const certId = reg.value.selected_certificate_id.trim()
  const row = certs.value.find((c) => c.certificate_id === certId)
  if (!row) {
    err.value = "Выберите сертификат из списка"
    return
  }
  const sg = collectSelectedGoals()
  if (!sg.length) {
    err.value = "Выберите хотя бы одну цель безопасности аппаратной конфигурации"
    return
  }
  try {
    await apiFetch("/api/register-drone", {
      method: "POST",
      body: {
        serial_number: reg.value.serial_number.trim(),
        drone_type: reg.value.drone_type.trim(),
        firmware_id: row.firmware_id,
        certificate_id: certId,
        security_goals: sg,
        price: Number(reg.value.price),
      },
    })
    msg.value = "Дрон зарегистрирован"
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}

onMounted(() => {
  loadCerts()
  load()
})
</script>

<template>
  <div>
    <h2 style="margin-top:0;">
      Реестр дронов
    </h2>
    <div v-if="msg" class="hint ok">
      {{ msg }}
    </div>
    <div v-if="err" class="alert" data-testid="dev-drones-error">
      {{ err }}
    </div>

    <div class="card stack">
      <h3>Новый дрон</h3>
      <div class="field">
        <label>Сертифицированная прошивка / сертификат (фильтр)</label>
        <input v-model="reg.cert_filter" data-testid="drone-cert-filter" type="search" placeholder="фильтр по id сертификата, прошивки…" class="full">
      </div>
      <div class="field">
        <label>Выбор пары прошивка–сертификат</label>
        <select
          v-model="reg.selected_certificate_id"
          data-testid="drone-cert-select"
          required
          @change="applyCertSelection(reg.selected_certificate_id)"
        >
          <option disabled value="">
            — выберите —
          </option>
          <option v-for="c in filteredCerts" :key="c.certificate_id" :value="c.certificate_id">
            {{ c.certificate_id }} · FW {{ c.firmware_id }} · {{ c.drone_type }}
          </option>
        </select>
      </div>
      <div class="field">
        <label>Цели безопасности (поднабор ЦБ сертификата, подходит к аппаратуре дрона)</label>
        <div v-if="!selectedCertGoals.length" class="muted small">
          Сначала выберите сертификат
        </div>
        <div v-else class="goal-rows">
          <button type="button" class="btn-secondary btn-tiny" data-testid="drone-goals-all" @click="toggleAllGoals(true)">
            Все
          </button>
          <button type="button" class="btn-muted btn-tiny" data-testid="drone-goals-none" @click="toggleAllGoals(false)">
            Снять всё
          </button>
          <label v-for="(g, idx) in selectedCertGoals" :key="g" class="row-check">
            <input
              v-model="reg.goal_toggles[g]"
              type="checkbox"
              :data-testid="`drone-goal-${idx}`"
            >
            <span>{{ g }}</span>
          </label>
        </div>
      </div>
      <div class="field">
        <label>Серийный номер</label>
        <input v-model="reg.serial_number" data-testid="drone-serial" type="text" required class="full">
      </div>
      <div class="field">
        <label>Тип БАС</label>
        <input v-model="reg.drone_type" data-testid="drone-type" type="text" required class="full">
      </div>
      <div class="field">
        <label>Цена</label>
        <input v-model.number="reg.price" data-testid="drone-price" type="number" min="0" step="1" class="full">
      </div>
      <button class="btn-primary" type="button" data-testid="drone-register-submit" @click="register">
        Зарегистрировать
      </button>
    </div>

    <div class="card">
      <h3>Все дроны</h3>
      <table class="data" data-testid="dev-drones-table">
        <thead>
          <tr>
            <th>Серийный номер</th>
            <th>Прошивка</th>
            <th>Сертификат</th>
            <th>ЦБ дрона</th>
            <th>Стоимость серт.</th>
            <th>ДВБ</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!loaded">
            <td colspan="7" class="muted" data-testid="dev-drones-loading">
              Загрузка…
            </td>
          </tr>
          <template v-else>
            <tr v-for="(d, i) in drones" :key="i">
              <td><code>{{ d.serial_number }}</code></td>
              <td><code>{{ d.firmware_id }}</code></td>
              <td><code>{{ d.certificate_id }}</code></td>
              <td class="goals-cell">
                <span v-if="Array.isArray(d.security_goals)">{{ d.security_goals.join(', ') }}</span>
                <span v-else>{{ d.security_goals }}</span>
              </td>
              <td>{{ d.certification_cost }}</td>
              <td>{{ d.dvb_size_kb }}</td>
              <td>{{ d.status }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.hint.ok {
  color: #86efac;
  margin-bottom: 12px;
}

html.theme-light .hint.ok {
  color: #166534;
}

.full {
  max-width: 100% !important;
}

.small {
  font-size: 0.85rem;
}

.goal-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.btn-tiny {
  padding: 4px 10px;
  font-size: 0.85rem;
  margin-right: 8px;
}

.row-check {
  display: flex;
  align-items: center;
  gap: 8px;
}

.goals-cell {
  white-space: normal;
  max-width: 220px;
}

.muted {
  color: var(--muted);
}
</style>
