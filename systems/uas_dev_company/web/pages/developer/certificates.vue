<script setup lang="ts">
/** Список сертифицированных прошивок / сертификатов. */

definePageMeta({
  layout: "developer",
  middleware: "role-developer",
})

const rows = ref<Record<string, unknown>[]>([])
const err = ref("")

async function load() {
  err.value = ""
  try {
    const res = await apiFetch<{ certificates: Record<string, unknown>[] }>("/api/certificates")
    rows.value = res.certificates
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
      Сертифицированные прошивки
    </h2>
    <div v-if="err" class="alert">
      {{ err }}
    </div>
    <button class="btn-secondary" type="button" @click="load">
      Обновить
    </button>
    <table class="data" data-testid="cert-table" style="margin-top:16px;">
      <thead>
        <tr>
          <th>Сертификат</th>
          <th>Прошивка</th>
          <th>ЦБ (прошивка)</th>
          <th>Тип</th>
          <th>Стоимость</th>
          <th>ДВБ, КБ</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(c, i) in rows" :key="i">
          <td><code>{{ c.certificate_id }}</code></td>
          <td><code>{{ c.firmware_id }}</code></td>
          <td class="goal-col">
            <span v-if="Array.isArray(c.security_goals)">{{ c.security_goals.join(', ') }}</span>
            <span v-else>{{ c.security_goals }}</span>
          </td>
          <td>{{ c.drone_type }}</td>
          <td>{{ c.certification_cost }}</td>
          <td>{{ c.dvb_size_kb }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.goal-col {
  white-space: normal;
  max-width: 260px;
}
</style>

