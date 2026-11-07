// Interface text. English strings are the keys (gettext style); another language only needs a
// dictionary from English to that language. Missing entries fall back to English.
import az from "./az.js";

const DICTIONARIES = { en: {}, az };
const STORAGE_KEY = "tms.language";

let language = "en";
try {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && DICTIONARIES[saved]) language = saved;
} catch {
  /* storage unavailable */
}

export const LANGUAGES = Object.keys(DICTIONARIES);
export const currentLanguage = () => language;

export function setLanguage(code) {
  if (!DICTIONARIES[code]) return;
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch {
    /* storage unavailable */
  }
  window.location.reload();
}

// t("Sent to {count} students", { count: 3 })
export function t(text, vars) {
  const template = DICTIONARIES[language][text] ?? text;
  return vars ? template.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`)) : template;
}
