import { useState, useEffect } from "react";
import { Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { incidentsApi } from "@/api/incidents";
import { normalizeError } from "@/api/client";
import { formatDate } from "@/lib/utils";
import { useSearchParams } from "react-router-dom";

export function TrackIncidentPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [reference, setReference] = useState("");
  const [submitted, setSubmitted] = useState("");

  // Auto-populate from URL query param on mount
  useEffect(() => {
    const ref = searchParams.get("ref");
    if (ref) {
      setReference(ref);
      setSubmitted(ref.trim().toUpperCase());
    }
  }, [searchParams]);

  const { data, isPending, error } = useQuery({
    queryKey: ["track", submitted],
    queryFn: () => incidentsApi.track(submitted),
    enabled: submitted.length > 5,
    retry: false,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const ref = reference.trim().toUpperCase();
    setSubmitted(ref);
    setSearchParams({ ref });
  };

  return (
    <div className="container max-w-2xl py-12">
      <h1 className="text-2xl font-bold">Track your report</h1>
      <p className="mt-2 text-muted-foreground">
        Enter the reference number from your submission (e.g. SC-MUM-2026-000123).
      </p>
      <form
        className="mt-6 flex gap-2"
        onSubmit={handleSubmit}
      >
        <div className="flex-1 space-y-2">
          <Label htmlFor="reference" className="sr-only">
            Reference number
          </Label>
          <Input
            id="reference"
            placeholder="SC-MUM-2026-000123"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
          />
        </div>
        <Button type="submit">
          <Search className="h-4 w-4" /> Track
        </Button>
      </form>

      {submitted && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Result</CardTitle>
          </CardHeader>
          <CardContent>
            {isPending && <p className="text-muted-foreground">Searching…</p>}
            {error && (
              <p className="text-danger">
                {normalizeError(error).status === 404
                  ? "No public report found for that reference number."
                  : normalizeError(error).detail}
              </p>
            )}
            {data && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={data.status} />
                  <SeverityBadge severity={data.severity} critical={data.is_emergency} />
                </div>
                <h2 className="text-lg font-semibold">{data.title}</h2>
                <p className="text-sm text-muted-foreground">{data.description}</p>
                <dl className="grid gap-1 text-sm">
                  <div className="flex gap-2">
                    <dt className="font-medium">Reference:</dt>
                    <dd>{data.reference_number}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="font-medium">Category:</dt>
                    <dd>{data.category?.name ?? "—"}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="font-medium">Department:</dt>
                    <dd>{data.department_name ?? "Pending routing"}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="font-medium">Reported:</dt>
                    <dd>{formatDate(data.created_at)}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="font-medium">Resolved:</dt>
                    <dd>{data.resolved_at ? formatDate(data.resolved_at) : "Not yet"}</dd>
                  </div>
                </dl>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
