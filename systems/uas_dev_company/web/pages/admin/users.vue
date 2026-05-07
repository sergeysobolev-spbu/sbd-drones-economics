<script setup lang="ts">
/** Список пользователей CRUD для администратора. */

definePageMeta({
  layout: "admin",
  middleware: "role-admin",
})

type Row = {
  username: string
  role: string
  is_active?: number | boolean
}

const users = ref<Row[]>([])
const nu = ref({ username: "", role: "разработчик", password: "" })
const msg = ref("")
const err = ref("")
const loaded = ref(false)

async function load() {
  err.value = ""
  try {
    const res = await apiFetch<{ users: Row[] }>("/api/users")
    users.value = res.users
  } catch (e: unknown) {
    err.value = (e as Error).message
  } finally {
    loaded.value = true
  }
}

async function createUser() {
  msg.value = ""
  err.value = ""
  try {
    await apiFetch("/api/users", {
      method: "POST",
      body: {
        username: nu.value.username.trim(),
        role: nu.value.role,
        password: nu.value.password,
      },
    })
    nu.value.password = ""
    nu.value.username = ""
    msg.value = "Пользователь создан"
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}

async function toggleBlock(u: Row) {
  msg.value = ""
  err.value = ""
  try {
    const active = !!(u.is_active === 1 || u.is_active === true)
    await apiFetch(`/api/users/${encodeURIComponent(u.username)}`, {
      method: "PATCH",
      body: { is_active: !active },
    })
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message
  }
}

async function remove(u: Row) {
  if (!confirm(`Удалить пользователя ${u.username}?`)) return
  msg.value = ""
  err.value = ""
  try {
    await apiFetch(`/api/users/${encodeURIComponent(u.username)}`, {
      method: "DELETE",
    })
    msg.value = "Удалено"
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
      Учётные записи
    </h2>
    <div v-if="msg" class="hint ok" data-testid="admin-banner">
      {{ msg }}
    </div>
    <div v-if="err" class="alert" data-testid="admin-error">
      {{ err }}
    </div>

    <div class="card stack">
      <h3>Создание пользователя</h3>
      <div class="row">
        <div class="field">
          <label>Логин</label>
          <input v-model="nu.username" data-testid="user-create-username" type="text">
        </div>
        <div class="field">
          <label>Роль</label>
          <select v-model="nu.role" data-testid="user-create-role">
            <option value="разработчик">
              разработчик
            </option>
            <option value="эксплуатант">
              эксплуатант
            </option>
            <option value="администратор">
              администратор
            </option>
          </select>
        </div>
        <div class="field">
          <label>Пароль</label>
          <input v-model="nu.password" data-testid="user-create-password" type="password">
        </div>
        <button class="btn-primary" type="button" data-testid="user-create-submit" @click="createUser">
          Создать
        </button>
      </div>
    </div>

    <div class="card">
      <h3>Пользователи</h3>
      <table class="data" data-testid="users-table">
        <thead>
          <tr>
            <th>Логин</th>
            <th>Роль</th>
            <th>Активен</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-if="!loaded">
            <td colspan="4" class="muted" data-testid="users-loading">
              Загрузка…
            </td>
          </tr>
          <template v-else>
            <tr v-for="u in users" :key="u.username">
              <td data-testid="user-row-name">{{ u.username }}</td>
              <td>{{ u.role }}</td>
              <td>{{ u.is_active === 1 || u.is_active === true ? 'да' : 'нет' }}</td>
              <td class="row-actions">
                <button
                  class="btn-muted"
                  type="button"
                  :data-testid="`user-block-${u.username}`"
                  @click="toggleBlock(u)"
                >
                  {{ u.is_active === 1 || u.is_active === true ? 'Заблокировать' : 'Разблокировать' }}
                </button>
                <button class="btn-danger" type="button" :data-testid="`user-delete-${u.username}`" @click="remove(u)">
                  Удалить
                </button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: flex-end;
}

.hint.ok {
  color: #86efac;
  margin-bottom: 12px;
}

html.theme-light .hint.ok {
  color: #166534;
}
</style>
