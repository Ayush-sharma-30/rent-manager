import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import type { Organization, User } from "@/api/types";

const STORAGE_KEY = "rent_manager_auth";

interface PersistedAuth {
  accessToken: string;
  refreshToken: string;
  user: User;
  organization: Organization;
}

interface AuthStore {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  organization: Organization | null;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  signIn: (auth: PersistedAuth) => Promise<void>;
  updateTokens: (accessToken: string, refreshToken: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  organization: null,
  hydrated: false,
  async hydrate() {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as PersistedAuth;
        set({
          accessToken: parsed.accessToken,
          refreshToken: parsed.refreshToken,
          user: parsed.user,
          organization: parsed.organization,
          hydrated: true,
        });
        return;
      }
    } catch {
      // ignore
    }
    set({ hydrated: true });
  },
  async signIn(auth) {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
    set({
      accessToken: auth.accessToken,
      refreshToken: auth.refreshToken,
      user: auth.user,
      organization: auth.organization,
    });
  },
  async updateTokens(accessToken, refreshToken) {
    const { user, organization } = useAuthStore.getState();
    set({ accessToken, refreshToken });
    if (user && organization) {
      await AsyncStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ accessToken, refreshToken, user, organization })
      );
    }
  },
  async signOut() {
    await AsyncStorage.removeItem(STORAGE_KEY);
    set({ accessToken: null, refreshToken: null, user: null, organization: null });
  },
}));
