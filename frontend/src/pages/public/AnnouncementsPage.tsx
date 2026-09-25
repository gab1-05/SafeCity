import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CalendarDays, CheckCircle2, Info, Megaphone, Pin, Search } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/feedback";
import { announcementsApi } from "@/api/auth";
import { formatDate } from "@/lib/utils";

const AUDIENCE_STYLES: Record<string, string> = {
  public: "bg-primary/10 text-primary",
  citizens: "bg-success/10 text-success",
  staff: "bg-warning/10 text-warning",
};

export function AnnouncementsPage() {
   const [q, setQ] = useState("");
   const { data, isPending, isError, refetch } = useQuery({
     queryKey: ["announcements"],
     queryFn: announcementsApi.list,
   });

   // Filter for published announcements only
   const publishedAnnouncements = useMemo(() => {
     if (!data) return [];
     return data.results.filter((a) => a.is_published);
   }, [data]);

  const filtered = useMemo(() => {
    const source = publishedAnnouncements;
    const needle = q.trim().toLowerCase();
    if (!needle) return source;
    return source.filter(
      (a) =>
        a.title.toLowerCase().includes(needle) ||
        a.body.toLowerCase().includes(needle),
    );
  }, [publishedAnnouncements, q]);

  const pinned = filtered.filter((a) => a.is_pinned);
  const rest = filtered.filter((a) => !a.is_pinned);

  return (
    <div className="container max-w-5xl py-10">
      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold">
            <Megaphone className="h-7 w-7 text-primary" aria-hidden />
            City announcements
          </h1>
          <p className="mt-2 text-muted-foreground">
            Official notices, service advisories and response updates from city departments.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 lg:grid-cols-1">
          <div className="rounded-lg border bg-card p-3">
            <Info className="mb-1 h-4 w-4 text-primary" aria-hidden />
            <p className="text-xs font-medium">Public notices</p>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <AlertTriangle className="mb-1 h-4 w-4 text-warning" aria-hidden />
            <p className="text-xs font-medium">Emergency advisories</p>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <CheckCircle2 className="mb-1 h-4 w-4 text-success" aria-hidden />
            <p className="text-xs font-medium">Resolved campaigns</p>
          </div>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-2">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            className="pl-9"
            placeholder="Search announcements…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search announcements"
          />
        </div>
      </div>

      <div className="mt-8 space-y-4">
        {isPending && [1, 2, 3].map((i) => <Skeleton key={i} className="h-28 w-full" />)}
        {isError && <ErrorState message="Could not load announcements." onRetry={refetch} />}
        {!isPending && !isError && filtered.length === 0 && (
          <EmptyState
            title={q ? "No announcements match your search" : "No announcements yet"}
            description={
              q ? "Try a different keyword." : "Published notices will appear here."
            }
          />
        )}

        {[...pinned, ...rest].map((a) => (
          <Card
            key={a.id}
            className={a.is_pinned ? "border-primary/40 bg-primary/[0.03]" : ""}
          >
            <CardHeader className="pb-2">
              <div className="flex flex-wrap items-center gap-2">
                {a.is_pinned && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                    <Pin className="h-3 w-3" aria-hidden /> Pinned
                  </span>
                )}
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    AUDIENCE_STYLES[a.audience] ?? "bg-muted text-muted-foreground"
                  }`}
                >
                  {a.audience}
                </span>
                <span className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
                  <CalendarDays className="h-3.5 w-3.5" aria-hidden />
                  {formatDate(a.published_at ?? a.created_at)}
                </span>
              </div>
              <CardTitle className="mt-1 text-xl">{a.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-sm leading-relaxed">{a.body}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
