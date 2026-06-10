import { useCallback } from "react";

import { useLocaleStore } from "@/state/locale.store";
import { TRANSLATIONS, type Dict, type Locale } from "@/i18n/translations";

export type { Locale } from "@/i18n/translations";
export { LOCALES } from "@/i18n/translations";

export type TVars = Record<string, string | number>;

function interpolate(template: string, vars?: TVars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in vars ? String(vars[key]) : match
  );
}

/** Look up a key for a given locale, falling back to English, then the key itself. */
export function translate(locale: Locale, key: string, vars?: TVars): string {
  const dict: Dict = TRANSLATIONS[locale] ?? TRANSLATIONS.en;
  const template = dict[key] ?? TRANSLATIONS.en[key] ?? key;
  return interpolate(template, vars);
}

/**
 * Returns a translate function bound to the current app locale. Components that
 * call this re-render when the locale changes (the store value is a dependency).
 */
export function useT(): (key: string, vars?: TVars) => string {
  const locale = useLocaleStore((s) => s.locale);
  return useCallback((key: string, vars?: TVars) => translate(locale, key, vars), [locale]);
}
