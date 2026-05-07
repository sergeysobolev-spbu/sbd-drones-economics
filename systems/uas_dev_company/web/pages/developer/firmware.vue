<script setup lang="ts">
/** Подача прошивки и запрос сертификации (разработчик). */

definePageMeta({
  layout: "developer",
  middleware: "role-developer",
})

const fw = useFormDraft("uas_draft_developer_firmware", () => ({
  firmware_id: "",
  supplier: "",
  drone_type: "",
  version: "",
  firmware_hash: "",
  source_repo_url: "",
  source_commit: "",
  security_goals: "",
  authenticity_proof: "",
}))

const certifyId = ref("")
const lastSubmit = ref<Record<string, unknown> | null>(null)
const lastCertify = ref<Record<string, unknown> | null>(null)
const err = ref("")

function parseGoalsBlock(raw: string): string[] {
  const trimmed = raw.trim()
  if (!trimmed) return []
  const lineSplit = trimmed.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)
  if (lineSplit.length > 1) return lineSplit.slice(0, 10)
  if (trimmed.includes(",")) {
    return trimmed.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 10)
  }
  return [trimmed].slice(0, 10)
}

function useRepoSource(): boolean {
  return Boolean(fw.value.source_repo_url.trim() && fw.value.source_commit.trim())
}

onMounted(() => {
  if (import.meta.client) {
    certifyId.value = sessionStorage.getItem("uas_draft_certify_id") ?? ""
    watch(certifyId, (v) => sessionStorage.setItem("uas_draft_certify_id", v?.trim?.() ?? ""))
  }
})

async function submitFw() {
  err.value = ""
  lastCertify.value = null
  try {
    const goals = parseGoalsBlock(fw.value.security_goals)
    if (!goals.length) {
      err.value = "Укажите от 1 до 10 целей безопасности (по одной на строку)"
      return
    }
    const repo = fw.value.source_repo_url.trim()
    const commit = fw.value.source_commit.trim()
    const hash = fw.value.firmware_hash.trim()
    if (!hash && (!repo || !commit)) {
      err.value = "Укажите хеш сборки или пару URL репозитория + коммит"
      return
    }
    const payload: Record<string, unknown> = {
      firmware_id: fw.value.firmware_id.trim() || undefined,
      supplier: fw.value.supplier.trim(),
      drone_type: fw.value.drone_type.trim(),
      version: fw.value.version.trim(),
      firmware_hash: hash,
      source_repo_url: repo,
      source_commit: commit,
      security_goals: goals,
      authenticity_proof: fw.value.authenticity_proof.trim(),
    }
    const res = await apiFetch<Record<string, unknown>>("/api/firmware", {
      method: "POST",
      body: payload,
    })
    lastSubmit.value = res
    certifyId.value = String(res.firmware_id || fw.value.firmware_id || "").trim()
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}

async function runCertify() {
  err.value = ""
  try {
    const res = await apiFetch<Record<string, unknown>>("/api/certify", {
      method: "POST",
      body: { firmware_id: certifyId.value.trim() },
    })
    lastCertify.value = res
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}
</script>

<template>
  <div>
    <p class="muted">
      Метаданные прошивки: локальный образ (хеш) или исходники для сборки со стороны Регулятора (URL Git + SHA коммита).
    </p>
    <div v-if="err" class="alert" data-testid="dev-fw-error">
      {{ err }}
    </div>

    <div class="card stack">
      <h3 style="margin-top:0;">
        Регистрация прошивки
      </h3>
      <div class="field">
        <label>Идентификатор прошивки</label>
        <input v-model="fw.firmware_id" data-testid="fw-id" placeholder="авто если пусто" type="text">
      </div>
      <div class="field">
        <label>Поставщик</label>
        <input v-model="fw.supplier" data-testid="fw-supplier" type="text" required>
      </div>
      <div class="field">
        <label>Тип БАС</label>
        <input v-model="fw.drone_type" data-testid="fw-drone-type" type="text" required>
      </div>
      <div class="field">
        <label>Версия / ветка (для отображения)</label>
        <input v-model="fw.version" data-testid="fw-version" type="text" required>
      </div>
      <div class="field">
        <label>Хеш сборки локального образа (SHA)</label>
        <input v-model="fw.firmware_hash" data-testid="fw-hash" type="text" :required="!useRepoSource()" placeholder="если сборка уже известна серверу дрона">
      </div>
      <div class="field">
        <label>Исходники: URL репозитория Git</label>
        <input v-model="fw.source_repo_url" data-testid="fw-repo-url" type="url" placeholder="https://…">
      </div>
      <div class="field">
        <label>Исходники: SHA коммита</label>
        <input v-model="fw.source_commit" data-testid="fw-repo-commit" type="text" placeholder="40 символов">
      </div>
      <div class="field">
        <label>Цели безопасности (до 10, по одной на строку)</label>
        <textarea
          v-model="fw.security_goals"
          data-testid="fw-goals"
          rows="10"
          required
          class="textarea-goals"
          placeholder="ЦБ-1&#10;ЦБ-3"
        />
      </div>
      <div class="field">
        <label>Доказательство подлинности / реквизит договора</label>
        <input v-model="fw.authenticity_proof" data-testid="fw-proof" type="text" required>
      </div>
      <button class="btn-primary" type="button" data-testid="fw-submit" @click="submitFw">
        Отправить прошивку
      </button>
      <pre class="mono" data-testid="fw-result">{{ lastSubmit ? JSON.stringify(lastSubmit, null, 2) : "" }}</pre>
    </div>

    <div class="card stack">
      <h3 style="margin-top:0;">
        Сертификация прошивки
      </h3>
      <div class="field">
        <label>Идентификатор прошивки</label>
        <input v-model="certifyId" data-testid="certify-firmware-id" type="text" required>
      </div>
      <button class="btn-primary" type="button" data-testid="certify-submit" @click="runCertify">
        Запустить сертификацию
      </button>
      <div class="cert-result" data-testid="certify-result">
        <template v-if="lastCertify">
          <p>
            <strong>Статус:</strong> {{ lastCertify.status }}
          </p>
          <p>
            <strong>Стоимость:</strong> {{ lastCertify.certification_cost }}
          </p>
          <p>
            <strong>Сертификат:</strong> <code>{{ lastCertify.certificate_id }}</code>
          </p>
          <pre class="mono">{{ JSON.stringify(lastCertify, null, 2) }}</pre>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.muted {
  color: var(--muted);
}

.mono {
  background: var(--bg);
  padding: 12px;
  border-radius: 8px;
  overflow: auto;
  font-size: 0.8rem;
}

.textarea-goals {
  width: 100%;
  max-width: 520px;
  min-height: 200px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-family: inherit;
  font-size: 0.9rem;
  box-sizing: border-box;
  resize: vertical;
}
</style>
