import { useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, FileText, Image, MapPin, RotateCcw, Send, Star, UploadCloud, MessageSquare, Download, Maximize2, Minimize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { Skeleton, ErrorState, StatCard, ConfirmDialog } from "@/components/ui/feedback";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { incidentsApi, exportIncidentPdf, exportIncidentCsv } from "@/api/incidents";
import { normalizeError } from "@/api/client";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/store/auth";
import { formatDate, timeAgo } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { MediaLightbox } from "@/components/incident/MediaLightbox";
import type { IncidentStatus } from "@/types";

const AUTHORITY_ACTIONS: Record<string, { label: string; to: IncidentStatus; variant?: "danger" | "success" }[]> = {
  submitted: [
    { label: "Start review", to: "under_review" },
    { label: "Verify", to: "verified", variant: "success" },
    { label: "Reject", to: "rejected", variant: "danger" },
  ],
  under_review: [
    { label: "Verify", to: "verified", variant: "success" },
    { label: "Reject", to: "rejected", variant: "danger" },
  ],
  assigned: [{ label: "Start work", to: "in_progress" }],
  in_progress: [
    { label: "Request info", to: "awaiting_info" },
    { label: "Resolve", to: "resolved", variant: "success" },
  ],
  awaiting_info: [{ label: "Resume work", to: "in_progress" }],
  escalated: [{ label: "Resume work", to: "in_progress" }],
  reopened: [{ label: "Start work", to: "in_progress" }],
  resolved: [{ label: "Close", to: "closed" }],
};

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [comment, setComment] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [confirmStatus, setConfirmStatus] = useState<IncidentStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [rating, setRating] = useState<number>(0);
  const [reopening, setReopening] = useState(false);
  const [resolutionComment, setResolutionComment] = useState("");
  const [uploading, setUploading] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState<{ index: number; media: any[] } | null>(null);
  const mediaInputRef = useRef<HTMLInputElement>(null);

  const isAuthority =
    user?.role === "department_staff" ||
    user?.role === "city_admin" ||
    user?.role === "superuser" ||
    user?.role === "emergency_responder";

  const { data: incident, isPending, isError } = useQuery({
    queryKey: ["incident", id],
    queryFn: () => incidentsApi.get(id!),
    enabled: !!id,
  });

  const { data: timeline } = useQuery({
    queryKey: ["incident", id, "timeline"],
    queryFn: () => incidentsApi.timeline(id!),
    enabled: !!id,
  });

  const { data: comments } = useQuery({
    queryKey: ["incident", id, "comments"],
    queryFn: () => incidentsApi.comments(id!),
    enabled: !!id,
  });

  const { data: media } = useQuery({
    queryKey: ["incident", id, "media"],
    queryFn: () => incidentsApi.media(id!),
    enabled: !!id,
  });

  if (isPending) return <Skeleton className="h-96 w-full" />;
  if (isError || !incident)
    return <ErrorState message="Could not load this incident." onRetry={() => window.location.reload()} />;

  const actions = isAuthority ? (AUTHORITY_ACTIONS[incident.status] ?? []) : [];

  const isReporter = incident.is_reporter === true;

  const applyStatus = async (status: IncidentStatus, note: string) => {
    setBusy(true);
    try {
      await incidentsApi.changeStatus(id!, status, note, status === "resolved" ? note : "");
      toast({ title: `Status updated to ${status.replace("_", " ")}`, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    } catch (error) {
      toast({ title: "Update failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
      setConfirmStatus(null);
    }
  };

  const confirmFixed = async () => {
    setBusy(true);
    try {
      await incidentsApi.confirm(id!, {
        rating: rating > 0 ? rating : undefined,
        comment: resolutionComment.trim() || "Citizen confirmed the issue is resolved.",
      });
      toast({ title: "Thanks for confirming!", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
    } catch (error) {
      toast({ title: "Confirmation failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const reopen = async () => {
    setBusy(true);
    try {
      await incidentsApi.reopen(
        id!,
        resolutionComment.trim() || "Citizen reports the issue is not fixed.",
      );
      toast({ title: "Report reopened — staff notified", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
    } catch (error) {
      toast({ title: "Reopen failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
      setReopening(false);
    }
  };

  const submitComment = async (mediaId?: string) => {
    if (!comment.trim()) return;
    setBusy(true);
    try {
      await incidentsApi.addComment(id!, comment.trim(), isInternal, mediaId);
      setComment("");
      queryClient.invalidateQueries({ queryKey: ["incident", id, "comments"] });
      toast({ title: isInternal ? "Internal note added" : "Update posted", variant: "success" });
    } catch (error) {
      toast({ title: "Comment failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const uploadEvidence = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    const failed: string[] = [];
    for (const file of Array.from(files).slice(0, 6)) {
      try {
        await incidentsApi.uploadMedia(id!, file);
      } catch {
        failed.push(file.name);
      }
    }
    if (mediaInputRef.current) mediaInputRef.current.value = "";
    queryClient.invalidateQueries({ queryKey: ["incident", id, "media"] });
    toast({
      title: failed.length ? "Some evidence could not be uploaded" : "Evidence uploaded",
      description: failed.length ? failed.join(", ") : undefined,
      variant: failed.length ? "error" : "success",
    });
    setUploading(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link to={-1 as never} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
        <div className="flex items-center gap-2">
<Button
             variant="outline"
             size="sm"
             onClick={() => exportIncidentCsv({})}
             disabled={isPending}
           >
             <FileText className="h-4 w-4" /> Export CSV
           </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => exportIncidentPdf(id!)}
            disabled={isPending}
          >
            <Download className="h-4 w-4" /> Export PDF
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">{incident.reference_number}</p>
          <h1 className="text-2xl font-bold">{incident.title}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <SeverityBadge severity={incident.severity} critical={incident.is_emergency} />
          <StatusBadge status={incident.status} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Category" value={incident.category?.name ?? "—"} />
        <StatCard label="Department" value={incident.department_name ?? "Pending routing"} />
        <StatCard
          label="Assigned to"
          value={incident.assigned_staff_name ?? "Unassigned"}
          tone={incident.assigned_staff_name ? "default" : "warning"}
        />
        <StatCard
          label="SLA deadline"
          value={incident.sla_deadline ? formatDate(incident.sla_deadline) : "—"}
          tone={incident.is_overdue || incident.sla_breached ? "danger" : "default"}
          hint={incident.is_overdue ? "This incident is overdue" : undefined}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-sm">{incident.description}</p>
              {incident.address_public && (
                <p className="mt-3 flex items-center gap-1 text-sm text-muted-foreground">
                  <MapPin className="h-4 w-4" /> {incident.address_public}
                  {incident.ward_name ? ` · ${incident.ward_name}` : ""}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Evidence</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                ref={mediaInputRef}
                type="file"
                className="sr-only"
                accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,application/pdf"
                multiple
                onChange={(e) => uploadEvidence(e.target.files)}
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground">
                  Add photos, videos or PDFs if the original upload failed or new evidence is available.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={uploading}
                  onClick={() => mediaInputRef.current?.click()}
                >
                  <UploadCloud className="h-4 w-4" />
                  {uploading ? "Uploading..." : "Upload evidence"}
                </Button>
              </div>
              {media && media.length > 0 ? (
                <ul className="grid gap-2 sm:grid-cols-2">
                  {media.map((item) => (
                    <li key={item.id} className="flex items-center gap-3 rounded-md border p-3 text-sm">
                      {item.media_type === "image" ? (
                        <Image className="h-4 w-4 text-primary" aria-hidden />
                      ) : (
                        <FileText className="h-4 w-4 text-primary" aria-hidden />
                      )}
                      <a
                        href={item.url ?? "#"}
                        target="_blank"
                        rel="noreferrer"
                        className="min-w-0 flex-1 truncate hover:text-primary"
                        onClick={(e) => {
                          if (item.media_type === "image") {
                            e.preventDefault();
                            setLightboxOpen({ index: media.indexOf(item), media });
                          }
                        }}
                      >
                        {item.caption || `${item.media_type} evidence`}
                      </a>
                      <span className="text-xs text-muted-foreground">
                        {(item.size_bytes / 1024 / 1024).toFixed(1)} MB
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          setLightboxOpen({ index: media.indexOf(item), media });
                        }}
                        aria-label="View fullscreen"
                      >
                        <Maximize2 className="h-4 w-4" />
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                  No evidence files uploaded yet.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Workflow actions (authority) */}
          {actions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Workflow actions</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {actions.map((action) => (
                  <Button
                    key={action.to}
                    size="sm"
                    variant={action.variant === "danger" ? "danger" : action.variant === "success" ? "success" : "default"}
                    disabled={busy}
                    onClick={() => setConfirmStatus(action.to)}
                  >
                    {action.label}
                  </Button>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Citizen resolution confirmation */}
          {incident.status === "resolved" && isReporter && !incident.citizen_confirmed_resolution && (
            <Card className="border-success/40 bg-success/5">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base text-success">
                  <CheckCircle2 className="h-5 w-5" aria-hidden />
                  Marked as resolved — can you confirm?
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm">
                  The department says this issue is fixed. Please check the location and tell us
                  whether it's actually resolved.
                </p>
                {incident.resolution_summary && (
                  <p className="rounded-md bg-muted p-3 text-sm">{incident.resolution_summary}</p>
                )}
                <div className="flex items-center gap-1" role="radiogroup" aria-label="Satisfaction rating">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={rating === value}
                      aria-label={`${value} star${value > 1 ? "s" : ""}`}
                      onClick={() => setRating(value)}
                      className="rounded p-1 hover:bg-accent"
                    >
                      <Star
                        className={cn(
                          "h-6 w-6",
                          value <= rating ? "fill-warning text-warning" : "text-muted-foreground",
                        )}
                      />
                    </button>
                  ))}
                </div>
                <Textarea
                  placeholder="Add a short note for the team..."
                  value={resolutionComment}
                  onChange={(e) => setResolutionComment(e.target.value)}
                  aria-label="Resolution feedback"
                />
                <div className="flex flex-wrap gap-2">
                  <Button variant="success" onClick={confirmFixed} disabled={busy}>
                    <CheckCircle2 className="h-4 w-4" /> Yes, it's fixed
                  </Button>
                  <Button variant="outline" onClick={() => setReopening(true)} disabled={busy}>
                    <RotateCcw className="h-4 w-4" /> Not fixed — reopen
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Reopen confirmation */}
          {reopening && (
            <Card className="border-warning/50 bg-warning/5">
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <p className="text-sm">
                  Reopen this report? The assigned staff will be notified immediately.
                </p>
                <div className="flex gap-2">
                  <Button variant="danger" size="sm" onClick={reopen} disabled={busy}>
                    Reopen report
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setReopening(false)}>
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Comments */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Updates & discussion {isAuthority ? "(public + internal)" : ""}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-3">
                {comments?.map((c) => (
                  <li
                    key={c.id}
                    className={
                      c.is_internal
                        ? "rounded-md border border-warning/40 bg-warning/5 p-3 text-sm"
                        : "rounded-md border p-3 text-sm"
                    }
                  >
                    <p className="font-medium">
                      {c.author_name}
                      {c.is_internal && (
                        <span className="ml-2 rounded bg-warning/20 px-1.5 py-0.5 text-xs text-warning">
                          internal
                        </span>
                      )}
                    </p>
                    <p className="mt-1 whitespace-pre-line">{c.body}</p>
                    {c.media_url && (
                      <div className="mt-2">
                        <img
                          src={c.media_url}
                          alt="Commented photo"
                          className="max-h-32 rounded border cursor-pointer"
                          onClick={() => setLightboxOpen({ index: 0, media: [{ id: c.id, url: c.media_url, media_type: "image", caption: "Photo comment" }] })}
                        />
                      </div>
                    )}
                    <div className="mt-2 flex items-center gap-2">
                      <p className="text-xs text-muted-foreground">{timeAgo(c.created_at)}</p>
                      {!c.media && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 text-xs"
                          onClick={() => setComment(`@${c.author_name} `)}
                          aria-label="Reply"
                        >
                          <MessageSquare className="h-3 w-3" />
                        </Button>
                      )}
                      {media && media.length > 0 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 text-xs"
                          onClick={() => {}}
                          aria-label="Comment on photo"
                        >
                          <Image className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </li>
                ))}
                {comments?.length === 0 && (
                  <li className="text-sm text-muted-foreground">No updates yet.</li>
                )}
              </ul>
              <div className="space-y-2">
                <Textarea
                  placeholder={isAuthority ? "Post a public update or an internal note…" : "Add a comment…"}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  aria-label="Write a comment"
                />
                {isAuthority && (
                  <label className="flex items-center gap-2 text-sm text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={isInternal}
                      onChange={(e) => setIsInternal(e.target.checked)}
                    />
                    Internal note (not visible to citizens)
                  </label>
                )}
                <Button size="sm" onClick={submitComment} disabled={busy || !comment.trim()}>
                  <Send className="h-4 w-4" /> Post
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Timeline sidebar */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="relative space-y-4 border-l pl-4">
              {timeline?.map((event) => (
                <li key={event.id} className="text-sm">
                  <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-primary" />
                  <p className="font-medium">
                    {event.to_status.replace("_", " ")}
                    {event.is_internal && (
                      <span className="ml-2 rounded bg-warning/20 px-1 py-0.5 text-xs text-warning">
                        internal
                      </span>
                    )}
                  </p>
                  {event.note && <p className="text-muted-foreground">{event.note}</p>}
                  <p className="text-xs text-muted-foreground">
                    {event.actor} · {timeAgo(event.created_at)}
                  </p>
                </li>
              ))}
              {timeline?.length === 0 && (
                <li className="text-sm text-muted-foreground">No events recorded yet.</li>
              )}
            </ol>
          </CardContent>
        </Card>
      </div>

      <ConfirmDialog
        open={confirmStatus !== null}
        title={`Change status to "${confirmStatus?.replace("_", " ")}"?`}
        description="This action is audited and will notify the relevant people."
        confirmLabel="Apply change"
        destructive={confirmStatus === "rejected"}
        onConfirm={() => confirmStatus && applyStatus(confirmStatus, "")}
        onCancel={() => setConfirmStatus(null)}
      />

      {lightboxOpen && (
        <MediaLightbox
          media={lightboxOpen.media}
          initialIndex={lightboxOpen.index}
          onClose={() => setLightboxOpen(null)}
          onCommentOnMedia={(mediaId) => {
            setLightboxOpen(null);
            // Pre-fill comment with reference to this media
            setComment(`@photo ${mediaId} `);
          }}
        />
      )}
    </div>
  );
}
