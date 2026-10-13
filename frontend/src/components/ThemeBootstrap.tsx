import { useEffect } from "react";
import { useAuthStore } from "@/store/auth";
import { disconnectWebSocket, initializeWebSocket } from "@/services/websocket";

/**
 * Side-effect-only root component: keeps the persisted theme in sync and
 * opens the WebSocket once a user session exists. Renders nothing.
 */
export function ThemeBootstrap() {
  const theme = useAuthStore((s) => s.theme);
  const setTheme = useAuthStore((s) => s.setTheme);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    setTheme(theme);
  }, [theme, setTheme]);

  useEffect(() => {
    if (user) {
      initializeWebSocket();
    } else {
      // Never leave a stale authenticated socket open after logout.
      disconnectWebSocket();
    }
  }, [user]);

  return null;
}
