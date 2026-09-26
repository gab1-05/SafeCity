import client from "./client";
import { challengeStore, tokenStore } from "./client";
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

/** Normal login: full session issued immediately. */
export interface LoginSuccess {
  access: string;
  refresh: string;
  user: User;
  requires_2fa?: false;
}

/** 2FA challenge: `access` is a 2-minute challenge token; no refresh yet. */
export interface LoginChallenge {
  access: string;
  refresh?: undefined;
  user: User;
  requires_2fa: true;
}

export type LoginResult = LoginSuccess | LoginChallenge;

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
  /** Optional elevated-role request — account is still created as citizen. */
  requested_role?: string;
  requested_department_id?: string;
  role_request_reason?: string;
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
  login: async (payload: LoginPayload): Promise<LoginResult> => {
    const { data } = await client.post<LoginResult>("/auth/token/", payload);
    if (data.requires_2fa) {
      // `access` is a 2-minute 2FA challenge, not a session: stash it so
      // verify2fa can send it as the Authorization header.
      if (data.access) challengeStore.set(data.access);
      return data;
    }
    tokenStore.set(data.access, data.refresh);
    return data;
  },
  verify2fa: async (payload: TwoFactorPayload): Promise<{ access: string; refresh: string; user: User }> => {
    const challenge = challengeStore.token;
    const { data } = await client.post("/auth/token/2fa/", payload, {
      headers: challenge ? { Authorization: `Bearer ${challenge}` } : undefined,
    });
    challengeStore.clear();
    tokenStore.set(data.access, data.refresh);
    return data;
  },
  /** Exchange a Google ID token (from Google Identity Services) for SafeCity JWTs.
   * Same endpoint handles both login and signup: first-time users are
   * auto-provisioned as citizens. Optional role-request fields apply only
   * on first signup (citizen account + pending admin approval). */
  googleLogin: async (
    idToken: string,
    roleRequest?: { requested_role?: string; requested_department_id?: string; role_request_reason?: string },
  ): Promise<{ access: string; refresh: string; user: User }> => {
    const { data } = await client.post("/auth/oauth/google/", {
      id_token: idToken,
      ...roleRequest,
    });
    tokenStore.set(data.access, data.refresh);
    return data;
  },
  logout: async (): Promise<void> => {
    const refresh = tokenStore.refresh;
    if (refresh) {
      await client.post("/auth/logout/", { refresh }).catch(() => undefined);
    }
    tokenStore.clear();
    challengeStore.clear();
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
  /** Confirm setup with the first TOTP token — this is what actually enables 2FA. */
  enable2fa: async (payload: TwoFactorPayload): Promise<{ detail: string }> => {
    const { data } = await client.post("/auth/2fa/setup/", payload);
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
  staff: async (departmentId?: string, roles?: string[]): Promise<User[]> => {
    const roleFilter = roles ?? ["department_staff", "emergency_responder", "volunteer"];
    const roleQuery = roleFilter.map((r) => `role=${r}`).join("&");
    const { data } = await client.get(
      `/users/?${roleQuery}${departmentId ? `&department=${departmentId}` : ""}`,
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
  unblockReporting: async (id: string): Promise<void> => {
    await client.post(`/users/${id}/unblock-reporting/`);
  },
};

export const announcementsApi = {
  list: async () => {
    const { data } = await publicClient.get("/announcements/");
    return data as Paginated<Announcement>;
  },
};

export interface RoleRequest {
  id: string;
  user: string;
  user_email: string;
  user_name: string;
  current_role: UserRole;
  requested_role: UserRole;
  department: string | null;
  department_name: string | null;
  reason: string;
  status: "pending" | "approved" | "rejected";
  reviewed_by: string | null;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export const roleRequestsApi = {
  /** Admin: pending queue (or ?status=all). Users: own requests. */
  list: async (status = "pending"): Promise<RoleRequest[]> => {
    const { data } = await client.get(`/users/role-requests/?status=${status}`);
    return data.results ?? data;
  },
  create: async (payload: {
    requested_role: string;
    department_id?: string | null;
    reason?: string;
  }): Promise<RoleRequest> => {
    const { data } = await client.post("/users/role-requests/", payload);
    return data;
  },
  review: async (id: string, decision: "approve" | "reject"): Promise<RoleRequest> => {
    const { data } = await client.post(`/users/role-requests/${id}/review/`, { decision });
    return data;
  },
};

export const departmentsApi = {
  list: async (): Promise<Array<{ id: string; name: string; code: string }>> => {
    const { data } = await client.get("/departments/");
    return data.results ?? data;
  },
};
