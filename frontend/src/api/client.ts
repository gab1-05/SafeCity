import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

const ACCESS_KEY = "safecity.access";
const REFRESH_KEY = "safecity.refresh";
const CHALLENGE_KEY = "safecity.challenge";

export const tokenStore = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string): void {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

/**
 * Short-lived 2FA challenge token issued by login when the account has 2FA
 * enabled. It is *not* a session — the backend rejects it everywhere except
 * the `/auth/token/2fa/` exchange, which must receive it as the bearer token.
 */
export const challengeStore = {
  get token(): string | null {
    return localStorage.getItem(CHALLENGE_KEY);
  },
  set(token: string): void {
    localStorage.setItem(CHALLENGE_KEY, token);
  },
  clear(): void {
    localStorage.removeItem(CHALLENGE_KEY);
  },
};

client.interceptors.request.use((config) => {
  // Never clobber an explicitly-provided Authorization header (the 2FA
  // exchange sends the challenge token, not the session token).
  const explicit =
    typeof config.headers.get === "function"
      ? config.headers.get("Authorization")
      : config.headers.Authorization;
  if (!explicit) {
    const token = tokenStore.access;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  
  // Add CSRF token if available
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
  if (csrfToken) {
    config.headers["X-CSRFToken"] = csrfToken;
  }

  return config;
});

/**
 * Queue refresh requests so parallel 401s trigger exactly one rotation.
 * On refresh failure the session is cleared and the user is sent to login.
 */
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.refresh;
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
      refresh,
    });
    tokenStore.set(data.access, data.refresh ?? refresh);
    return data.access as string;
  } catch {
    tokenStore.clear();
    window.location.href = "/login";
    return null;
  }
}

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retried?: boolean;
    };
    if (
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !original.url?.includes("/auth/token/")
    ) {
      original._retried = true;
      refreshPromise = refreshPromise ?? refreshAccessToken();
      const token = await refreshPromise;
      refreshPromise = null;
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return client(original);
      }
    }
    return Promise.reject(error);
  },
);

export interface NormalizedError {
  status: number;
  detail: string;
  fieldErrors: Record<string, string[]>;
}

export function normalizeError(error: unknown): NormalizedError {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { detail?: string; errors?: Record<string, string[]>; [key: string]: unknown }
      | undefined;
    const directFieldErrors =
      data && typeof data === "object"
        ? Object.fromEntries(
            Object.entries(data)
              .filter(([key, value]) => key !== "detail" && key !== "errors" && Array.isArray(value))
              .map(([key, value]) => [key, (value as unknown[]).map(String)]),
          )
        : {};
    const fieldErrors = { ...directFieldErrors, ...(data?.errors ?? {}) };
    const firstFieldError = Object.values(fieldErrors)[0]?.[0];
    return {
      status: error.response?.status ?? 0,
      detail:
        data?.detail ??
        firstFieldError ??
        (error.response?.status
          ? `Request failed (${error.response.status})`
          : "Network error — is the backend running?"),
      fieldErrors,
    };
  }
  return { status: 0, detail: "Unexpected error.", fieldErrors: {} };
}

export default client;
