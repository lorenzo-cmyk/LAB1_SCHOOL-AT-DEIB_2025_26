import { createI18n } from "vue-i18n";

import en from "./locales/en.json";

const getSavedLocale = () => {
  try {
    const raw = localStorage.getItem("mininetGuiSettings");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.language || null;
  } catch (error) {
    return null;
  }
};

const i18n = createI18n({
  legacy: true,
  locale: getSavedLocale() || "en",
  fallbackLocale: "en",
  messages: { en },
});

export default i18n;
