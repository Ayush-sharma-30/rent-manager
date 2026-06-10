import Constants from "expo-constants";
import { Platform } from "react-native";
import { useAuthStore } from "@/state/auth.store";

function resolveBaseUrl(): string {
  // Set at build time (e.g. on Vercel) — Expo inlines EXPO_PUBLIC_* vars.
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, "");

  const explicit = (Constants.expoConfig?.extra as { apiBaseUrl?: string })?.apiBaseUrl;
  if (Platform.OS === "web") {
    return explicit?.replace(/\/$/, "") ?? "http://localhost:8000";
  }
  // On a device or simulator, "localhost" points at the device — use the dev host.
  const debuggerHost = Constants.expoConfig?.hostUri?.split(":")[0];
  if (debuggerHost) return `http://${debuggerHost}:8000`;
  return explicit?.replace(/\/$/, "") ?? "http://localhost:8000";
}

export const API_BASE_URL = resolveBaseUrl();

export interface ApiError extends Error {
  status: number;
  data: unknown;
}

// Dedupe concurrent refreshes: if several requests 401 at once (e.g. the
// dashboard fires two), they all await the same refresh call.
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const { refreshToken, updateTokens, signOut } = useAuthStore.getState();
  if (!refreshToken) {
    await signOut();
    return false;
  }
  try {
    const resp = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) {
      await signOut();
      return false;
    }
    const data = (await resp.json()) as { access_token: string; refresh_token: string };
    await updateTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    await signOut();
    return false;
  }
}

export async function api<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = true, headers, ...rest } = init;

  const send = (): Promise<Response> => {
    const finalHeaders: Record<string, string> = {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(headers as Record<string, string> | undefined),
    };
    if (auth) {
      const token = useAuthStore.getState().accessToken;
      if (token) finalHeaders.Authorization = `Bearer ${token}`;
    }
    return fetch(`${API_BASE_URL}${path}`, { ...rest, headers: finalHeaders });
  };

  let resp = await send();

  // Access token expired — try a single refresh, then replay the request.
  if (resp.status === 401 && auth) {
    if (!refreshPromise) refreshPromise = refreshAccessToken();
    const refreshed = await refreshPromise.finally(() => {
      refreshPromise = null;
    });
    if (refreshed) {
      resp = await send();
    }
  }

  if (resp.status === 204) {
    return undefined as T;
  }
  const text = await resp.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!resp.ok) {
    const err = new Error(
      (data as { detail?: string })?.detail || `HTTP ${resp.status}`
    ) as ApiError;
    err.status = resp.status;
    err.data = data;
    throw err;
  }
  return data as T;
}
