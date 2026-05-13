<script setup lang="ts">
/** Форма входа и разовая инициализация первого администратора. */

definePageMeta({
  layout: "default",
  middleware: "auth-redirect-from-login",
})

const username = ref("")
const password = ref("")
const bootstrapUser = ref("")
const bootstrapPass = ref("")
const showBootstrap = ref(false)
const err = ref("")
const pending = ref(false)

const { setToken, syncFromStorage } = useAuthSession()

onMounted(() => {
  syncFromStorage()
})

async function login() {
  err.value = ""
  pending.value = true
  try {
    const res = await $fetch<{ access_token: string }>("/api/login", {
      method: "POST",
      body: {
        username: username.value.trim(),
        password: password.value,
      },
      timeout: 90_000,
    })
    setToken(res.access_token)
    navigateTo("/")
  } catch (e: unknown) {
    const msg = (e as { data?: { error?: string }; message?: string }).data?.error || (e as Error).message
    err.value = typeof msg === "string" ? msg : "Ошибка входа"
  } finally {
    pending.value = false
  }
}

async function bootstrap() {
  err.value = ""
  pending.value = true
  try {
    await $fetch("/api/bootstrap-admin", {
      method: "POST",
      body: {
        username: bootstrapUser.value.trim(),
        password: bootstrapPass.value,
      },
      timeout: 90_000,
    })
    showBootstrap.value = false
    username.value = bootstrapUser.value.trim()
    bootstrapPass.value = ""
  } catch (e: unknown) {
    const msg = (e as { data?: { error?: string }; message?: string }).data?.error || (e as Error).message
    err.value = typeof msg === "string" ? msg : "Ошибка инициализации"
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="panel card">
      <h1>Вход</h1>
      <div v-if="err" class="alert" data-testid="login-error">
        {{ err }}
      </div>
      <form class="stack" @submit.prevent="login">
        <div class="field">
          <label for="u">Имя пользователя</label>
          <input id="u" v-model="username" data-testid="login-username" type="text" autocomplete="username" required>
        </div>
        <div class="field">
          <label for="p">Пароль</label>
          <input id="p" v-model="password" data-testid="login-password" type="password" autocomplete="current-password" required>
        </div>
        <button class="btn-primary" type="submit" data-testid="login-submit" :disabled="pending">
          Войти
        </button>
      </form>
      <button type="button" class="btn-muted" data-testid="login-toggle-bootstrap" @click="showBootstrap = !showBootstrap">
        Первый запуск БД
      </button>
      <div v-if="showBootstrap" class="stack boot">
        <h2>Создать администратора</h2>
        <div class="field">
          <label for="bu">Логин</label>
          <input id="bu" v-model="bootstrapUser" data-testid="bootstrap-username" type="text" required>
        </div>
        <div class="field">
          <label for="bp">Пароль</label>
          <input id="bp" v-model="bootstrapPass" data-testid="bootstrap-password" type="password" required>
        </div>
        <button class="btn-secondary" type="button" data-testid="bootstrap-submit" :disabled="pending" @click="bootstrap">
          Инициализировать
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.panel {
  padding: 28px;
  max-width: 400px;
}

.boot {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

h1 {
  margin-top: 0;
}
</style>
