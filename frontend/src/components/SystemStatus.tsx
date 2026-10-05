import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";

/** Footer status dot fed by /api/health/ (60s poll). Purely informational. */
export function SystemStatus() {
  const { data, isError } = useQuery({
    queryKey: ["system-status"],
    queryFn: async (): Promise<{ status: string }> => {
      const res = await fetch("/api/health/");
      if (!res.ok) throw new Error("unhealthy");
      return res.json();
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
