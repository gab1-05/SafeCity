import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Megaphone, Pin, Send, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/feedback";
import { useToast } from "@/components/ui/toast";
import client, { normalizeError } from "@/api/client";
import { formatDate, timeAgo } from "@/lib/utils";

interface Announcement {
  id: string;
  title: string;
  body: string;
  audience: string;
  is_pinned: boolean;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
}

export function AnnouncementAdminPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState("public");
  const [isPinned, setIsPinned] = useState(false);
  const [busy, setBusy] = useState(false);

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["admin-announcements"],
    queryFn: async (): Promise<Announcement[]> => {
      const { data } = await client.get("/announcements/");
      // Admin endpoint returns published + drafts for authorized callers.
      return Array.isArray(data) ? data : data.results;
    },
  });

  const create = async () => {
    if (!title.trim() || !body.trim()) return;
    setBusy(true);
    try {
      const { data: created } = await client.post("/announcements/", {
        title: title.trim(),
        body: body.trim(),
        audience,
        is_pinned: isPinned,
      });
      await client.post(`/announcements/${created.id}/publish/`);
      toast({ title: "Announcement published", variant: "success" });
      setTitle("");
      setBody("");
      setIsPinned(false);
      queryClient.invalidateQueries({ queryKey: ["admin-announcements"] });
      queryClient.invalidateQueries({ queryKey: ["announcements"] });
    } catch (error) {
      toast({
        title: "Publish failed",
        description: normalizeError(error).detail,
        variant: "error",
      });
    } finally {
      setBusy(false);
    }
  };

  const unpublish = async (a: Announcement) => {
    setBusy(true);
    try {
      await client.patch(`/announcements/${a.id}/`, { is_published: false });
      queryClient.invalidateQueries({ queryKey: ["admin-announcements"] });
      queryClient.invalidateQueries({ queryKey: ["announcements"] });
      toast({ title: "Unpublished", variant: "success" });
    } catch (error) {
      toast({ title: "Update failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (a: Announcement) => {
    setBusy(true);
    try {
      await client.delete(`/announcements/${a.id}/`);
      queryClient.invalidateQueries({ queryKey: ["admin-announcements"] });
      queryClient.invalidateQueries({ queryKey: ["announcements"] });
      toast({ title: "Deleted", variant: "success" });
    } catch (error) {
      toast({ title: "Delete failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const togglePin = async (a: Announcement) => {
    setBusy(true);
    try {
      await client.patch(`/announcements/${a.id}/`, { is_pinned: !a.is_pinned });
      queryClient.invalidateQueries({ queryKey: ["admin-announcements"] });
      queryClient.invalidateQueries({ queryKey: ["announcements"] });
      toast({ title: a.is_pinned ? "Pinned announcement removed" : "Announcement pinned", variant: "success" });
    } catch (error) {
      toast({ title: "Pin update failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Megaphone className="h-6 w-6 text-primary" aria-hidden /> Announcements
        </h1>
        <p className="text-sm text-muted-foreground">
          Publish official notices to the public announcements page.
        </p>
      </div>

      {/* Composer */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">New announcement</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="ann-title">Title</Label>
            <Input
              id="ann-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              placeholder="e.g. Scheduled water maintenance in Ward 4"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ann-body">Body</Label>
            <Textarea
              id="ann-body"
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="What should citizens know? Blank lines create paragraphs."
            />
          </div>
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="ann-audience">Audience</Label>
              <Select
                id="ann-audience"
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                className="w-40"
              >
                <option value="public">Public</option>
                <option value="citizens">Citizens</option>
                <option value="staff">Staff</option>
              </Select>
            </div>
            <label className="flex items-center gap-2 pb-2 text-sm">
              <input
                type="checkbox"
                checked={isPinned}
                onChange={(e) => setIsPinned(e.target.checked)}
              />
              Pin to top
            </label>
            <Button onClick={create} disabled={busy || !title.trim() || !body.trim()}>
              <Send className="h-4 w-4" /> Publish
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Existing */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">All announcements</h2>
        {isPending && <Skeleton className="h-24 w-full" />}
        {isError && <ErrorState message="Could not load announcements." onRetry={refetch} />}
        {data?.length === 0 && (
          <EmptyState title="Nothing published yet" description="Use the form above." />
        )}
        {data?.map((a) => (
          <Card key={a.id}>
            <CardContent className="flex items-start justify-between gap-4 p-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  {a.is_pinned && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                      <Pin className="h-3 w-3" aria-hidden /> Pinned
                    </span>
                  )}
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      a.is_published
                        ? "bg-success/10 text-success"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {a.is_published ? "published" : "draft"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {a.audience} ·{" "}
                    {a.published_at
                      ? `published ${formatDate(a.published_at)}`
                      : `created ${timeAgo(a.created_at)}`}
                  </span>
                </div>
                <p className="mt-1 font-medium">{a.title}</p>
                <p className="mt-0.5 line-clamp-2 text-sm text-muted-foreground">{a.body}</p>
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label="Toggle pin"
                  onClick={() => togglePin(a)}
                  disabled={busy}
                >
                  <Pin className="h-4 w-4" />
                </Button>
                {a.is_published && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => unpublish(a)}
                    disabled={busy}
                  >
                    Unpublish
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="danger"
                  aria-label="Delete announcement"
                  onClick={() => remove(a)}
                  disabled={busy}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
