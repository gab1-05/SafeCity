import client from "./client";
import { tokenStore } from "./client";
import axios from "axios";
import type { Notification, User, UserRole, Paginated, Announcement } from "@/types";

const publicClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  headers: { "Content-Type": "application/json" },
});

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TwoFactorPayload {
  token: string;
}

export interface RegisterPayload {
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  password: string;
  accept_terms: boolean;
  prefers_anonymous_reporting?: boolean;
}

export interface TwoFactorSetupResponse {
  secret: string;
  otpauth_uri: string;
  recovery_codes: string[];
}

export interface TwoFactorRecoveryResponse {
  recovery_codes: string[];
}

export const authApi = {
  register: async (payload: RegisterPayload): Promise<{ detail?: string }> => {
    const { data } = await client.post("/auth/register/", payload);
    return data;
  },
  login: async (payload: LoginPayload): Promise<{ access: string; refresh: string; user: User; requires_2fa?: boolean }> => {
    const { data } = await client.post("/auth/token/", payload);
    if (data.requires_2fa) {
      return data;
    }
    tokenStore.set(data.access, data.refresh);
    return data;
  },
  verify2fa: async (payload: TwoFactorPayload): Promise<{ access: string; refresh: string; user: User }> => {
    const { data } = await client.post("/auth/token/2fa/", payload);
    tokenStore.set(data.access, data.refresh);
    return data;
  },
  /** Exchange a Google ID token (from Google Identity Services) for SafeCity JWTs. */
  googleLogin: async (idToken: string): Promise<{ access: string; refresh: string; user: User }> => {
    const { data } = await client.post("/auth/oauth/google/", { id_token: idToken });
    tokenStore.set(data.access, data.refresh);
    return data;
  },
  logout: async (): Promise<void> => {
    const refresh = tokenStore.refresh;
    if (refresh) {
      await client.post("/auth/logout/", { refresh }).catch(() => undefined);
    }
    tokenStore.clear();
  },
  me: async (): Promise<User> => {
    const { data } = await client.get("/auth/me/");
    return data;
  },
  requestPasswordReset: async (email: string): Promise<{ detail: string }> => {
    const { data } = await client.post("/auth/password/reset/", { email });
    return data;
  },
  confirmPasswordReset: async (payload: {
    uid: string;
    token: string;
    password: string;
  }): Promise<{ detail: string }> => {
    const { data } = await client.post("/auth/password/reset/confirm/", payload);
    return data;
  },
  changePassword: async (payload: {
    current_password: string;
    new_password: string;
  }): Promise<{ detail: string }> => {
    const { data } = await client.post("/auth/password/change/", payload);
    return data;
  },
  sessions: async (): Promise<
    Array<{ id: string; created_at: string; expires_at: string; active: boolean }>
  > => {
    const { data } = await client.get("/auth/sessions/");
    return data;
  },
  revokeSession: async (id: string): Promise<void> => {
    await client.delete(`/auth/sessions/${id}/`);
  },
  setup2fa: async (): Promise<TwoFactorSetupResponse> => {
    const { data } = await client.get("/auth/2fa/setup/");
    return data;
  },
  disable2fa: async (payload: TwoFactorPayload): Promise<{ detail: string }> => {
    const { data } = await client.post("/auth/2fa/disable/", payload);
    return data;
  },
  regenerateRecoveryCodes: async (payload: TwoFactorPayload): Promise<TwoFactorRecoveryResponse> => {
    const { data } = await client.post("/auth/2fa/recovery/regenerate/", payload);
    return data;
  },
};

export const notificationsApi = {
  list: async (): Promise<{ unread_count: number; results: Notification[] }> => {
    const { data } = await client.get("/notifications/");
    return data;
  },
  markRead: async (id: string): Promise<void> => {
    await client.post(`/notifications/${id}/read/`);
  },
  markAllRead: async (): Promise<void> => {
    await client.post("/notifications/read-all/");
  },
  updatePreferences: async (prefs: Record<string, unknown>): Promise<void> => {
    await client.patch("/profile/notification-preferences/", prefs);
  },
};

export const usersApi = {
  staff: async (departmentId?: string): Promise<User[]> => {
    const { data } = await client.get(
      `/users/?role=department_staff${departmentId ? `&department=${departmentId}` : ""}`,
    );
    return data.results ?? data;
  },
  changeRole: async (id: string, role: UserRole, departmentId?: string): Promise<void> => {
    await client.post(`/users/${id}/role/`, {
      role,
      department_id: departmentId ?? null,
    });
  },
  unlock: async (id: string): Promise<void> => {
    await client.post(`/users/${id}/unlock/`);
  },
};

export const announcementsApi = {
  list: async () => {
    const { data } = await publicClient.get("/announcements/");
    return data as Paginated<Announcement>;
  },
};
