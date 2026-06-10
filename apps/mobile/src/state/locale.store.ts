import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import type { Locale } from "@/i18n/translations";

const STORAGE_KEY = "rent_manager_locale";
const SUPPORTED: Locale[] = ["en", "hi", "kn"];

interface LocaleStore {
  locale: Locale;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setLocale: (locale: Locale) => Promise<void>;
}

export const useLocaleStore = create<LocaleStore>((set) => ({
  locale: "en",
  hydrated: false,
  async hydrate() {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw && (SUPPORTED as string[]).includes(raw)) {
        set({ locale: raw as Locale, hydrated: true });
        return;
      }
    } catch {
      // ignore — fall back to default
    }
    set({ hydrated: true });
  },
  async setLocale(locale) {
    set({ locale });
    try {
      await AsyncStorage.setItem(STORAGE_KEY, locale);
    } catch {
      // ignore persistence failure; in-memory value still applies
    }
  },
}));
