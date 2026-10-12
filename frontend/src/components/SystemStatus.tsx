import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { API_BASE_URL } from "@/api/client";
import { cn } from "@/lib/utils";

/** Health endpoint lives at /api/health/ (one level above the /api/v1 base). */
const HEALTH_URL = `${API_BASE_URL.replace(/\/v1\/?$/, "")}/health/`;

/** Footer status dot fed by the health endpoint (60s poll). Purely informational. */
export function SystemStatus() {
  const { data, isError } = useQuery({
    queryKey: ["system-status"],
    queryFn: async (): Promise<{ status: string }> => {
      const { data } = await axios.get(HEALTH_URL);
      return data;
    },
    refetchInterval: 60_000,
    retry: 1,
    staleTime: 60_000,
  });

  const ok = !isError && data?.status === "ok";
  return (
    <span
      className="inline-flex items-center gap-1.5"
      role="status"
      aria-label={ok ? "All systems operational" : "Systems degraded"}
      title={ok ? "All systems operational" : "Systems degraded"}
    >
      <span
        aria-hidden
        className={cn(
          "inline-block h-2 w-2 rounded-full",
          ok ? "bg-success" : "bg-warning animate-pulse",
        )}
      />
      {ok ? "Operational" : "Degraded"}
    </span>
  );
}
