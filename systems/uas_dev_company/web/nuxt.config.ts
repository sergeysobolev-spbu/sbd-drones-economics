export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: false },
  ssr: false,
  app: {
    head: {
      title: "Разработчик БАС",
      htmlAttrs: { lang: "ru" },
    },
  },
  css: ["~/assets/app.css"],
})
