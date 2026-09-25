import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import "./index.css";
import { AppRoutes } from "@/routes";
import { ToasterComponent } from "@/components/ui/toast";
import { useAuthStore } from "@/store/auth";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { initializeWebSocket } from "@/services/websocket";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 60_000,
      gcTime: 5 * 60 * 1000,
      refetchOnReconnect: true,
      refetchOnMount: "always",
    },
    mutations: {
      retry: 0,
    },
  },
});

function ThemeBootstrap() {
  const theme = useAuthStore((s) => s.theme);
  const setTheme = useAuthStore((s) => s.setTheme);
  const user = useAuthStore((s) => s.user);
  useEffect(() => {
    setTheme(theme);
  }, [theme, setTheme]);

  useEffect(() => {
    if (user) {
      initializeWebSocket();
    }
  }, [user]);

  return null;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeBootstrap />
        <ErrorBoundary>
          <AppRoutes />
        </ErrorBoundary>
        <ToasterComponent />
        {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);