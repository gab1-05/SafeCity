import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { UserRole } from "@/types";

interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
  full_name: string;
  department?: string | null;
}

type ThemeMode = "light" | "dark" | "system";

interface AuthState {
  user: AuthUser | null;
  theme: ThemeMode;
  resolvedTheme: "light" | "dark";
  setUser: (user: AuthState["user"]) => void;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  initializeTheme: () => void;
}

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolveTheme(theme: ThemeMode): "light" | "dark" {
  if (theme === "system") return getSystemTheme();
  return theme;
}

function applyTheme(resolved: "light" | "dark") {
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(resolved);
  root.style.colorScheme = resolved;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      theme: "system",
      resolvedTheme: "dark",

      setUser: (user) => {
        if (user) localStorage.setItem("safecity.user", JSON.stringify(user));
        else localStorage.removeItem("safecity.user");
        set({ user });
      },

      setTheme: (theme: ThemeMode) => {
        const resolved = resolveTheme(theme);
        applyTheme(resolved);
        set({ theme, resolvedTheme: resolved });
      },

      toggleTheme: () => {
        const { theme } = get();
        const nextTheme = theme === "dark" ? "light" : theme === "light" ? "system" : "dark";
        get().setTheme(nextTheme);
      },

      initializeTheme: () => {
        const { theme } = get();
        const resolved = resolveTheme(theme);
        applyTheme(resolved);
        set({ resolvedTheme: resolved });

        if (typeof window !== "undefined") {
          const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
          const handler = () => {
            if (get().theme === "system") {
              const resolved = getSystemTheme();
              applyTheme(resolved);
              set({ resolvedTheme: resolved });
            }
          };
          mediaQuery.addEventListener("change", handler);
          return () => mediaQuery.removeEventListener("change", handler);
        }
      },
    }),
    {
      name: "safecity.auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        theme: state.theme,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.initializeTheme();
        }
      },
    }
  )
);

/** Role gates used by route guards (UX only; backend enforces the truth). */
export const roleCan = {
  viewAuthorityDashboard: (role?: UserRole) =>
    role === "department_staff" || role === "city_admin" || role === "superuser",
  manageSystem: (role?: UserRole) => role === "city_admin" || role === "superuser",
  respondEmergencies: (role?: UserRole) => role === "emergency_responder",
  reportIncidents: (role?: UserRole) =>
    role === "citizen" || role === "city_admin" || role === "superuser" ||
    role === "department_staff",
};