<script setup lang="ts">
/** Просмотр реестра и покупка доступного дрона. */

definePageMeta({
  layout: "operator",
  middleware: "role-operator",
})

const drones = ref<Record<string, unknown>[]>([])
const err = ref("")
const msg = ref("")

async function load() {
  err.value = ""
  try {
    const res = await apiFetch<{ drones: Record<string, unknown>[] }>("/api/drones")
    drones.value = res.drones
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}

async function buy(serial: string) {
  msg.value = ""
  err.value = ""
  try {
    await apiFetch("/api/purchase", {
      method: "POST",
      body: { serial_number: serial },
    })
    msg.value = "Покупка оформлена"
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}

onMounted(() => {
  load()
})
</script>

<template>
  <div>
    <h2 style="margin-top:0;">
      Зарегистрированные дроны
    </h2>
    <div v-if="msg" class="hint ok" data-testid="op-msg">
      {{ msg }}
    </div>
    <div v-if="err" class="alert" data-testid="op-error">
      {{ err }}
    </div>
    <button class="btn-secondary" type="button" @click="load">
      Обновить
    </button>
    <table class="data" data-testid="op-drones-table" style="margin-top:16px;">
      <thead>
        <tr>
          <th>Серийный номер</th>
          <th>Тип</th>
          <th>ЦБ дрона</th>
          <th>Цена</th>
          <th>Статус</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="(d, i) in drones" :key="i">
          <td><code>{{ d.serial_number }}</code></td>
          <td>{{ d.drone_type }}</td>
          <td class="goal-col">
            <span v-if="Array.isArray(d.security_goals)">{{ d.security_goals.join(', ') }}</span>
            <span v-else>{{ d.security_goals }}</span>
          </td>
          <td>{{ d.price }}</td>
          <td>{{ d.status }}</td>
          <td>
            <button
              v-if="d.status === 'available'"
              class="btn-primary"
              type="button"
              :data-testid="`buy-${d.serial_number}`"
              @click="buy(String(d.serial_number))"
            >
              Купить
            </button>
            <span v-else class="muted">—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.hint.ok {
  color: #86efac;
  margin-bottom: 12px;
}

.muted {
  color: var(--muted);
}

.goal-col {
  white-space: normal;
  max-width: 200px;
  font-size: 0.85rem;
}
</style>
