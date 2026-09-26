import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ConfirmDialog } from "@/components/ui/feedback";
import { authApi, departmentsApi, notificationsApi, roleRequestsApi } from "@/api/auth";
import client, { normalizeError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { formatDate } from "@/lib/utils";

export function ProfilePage() {
  const { user, setUser } = useAuthStore();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [profile, setProfile] = useState({ first_name: "", last_name: "", phone: "", language: "en" });
  const [prefs, setPrefs] = useState({ in_app: true, email: true, sms: false });
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const me = await authApi.me();
      setProfile({
        first_name: me.first_name,
        last_name: me.last_name,
        phone: me.phone ?? "",
        language: me.language ?? "en",
      });
      return me;
    },
  });

  const { data: sessions } = useQuery({
    queryKey: ["sessions"],
    queryFn: authApi.sessions,
  });

  useQuery({
    queryKey: ["prefs"],
    queryFn: async () => {
      const { data } = await client.get("/profile/notification-preferences/");
      setPrefs({ in_app: data.in_app, email: data.email, sms: data.sms });
      return data;
    },
  });

  useEffect(() => {
    if (user && profile.first_name) {
      setUser({ ...user, full_name: `${profile.first_name} ${profile.last_name}`.trim() });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.first_name, profile.last_name]);

  const saveProfile = async () => {
    setBusy(true);
    try {
      const { data: me } = await client.patch("/auth/me/", profile);
      queryClient.setQueryData(["me"], me);
      toast({ title: "Profile updated", variant: "success" });
    } catch (error) {
      toast({ title: "Update failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const savePrefs = async (next: typeof prefs) => {
    setPrefs(next);
    try {
      await notificationsApi.updatePreferences(next);
    } catch {
      /* preferences are best-effort until saved explicitly */
    }
  };

  const requestDeletion = async () => {
    try {
      await client.post("/profile/deletion-request/", {});
      toast({
        title: "Deletion request submitted",
        description: "An administrator will process your request.",
        variant: "success",
      });
    } catch (error) {
      toast({ title: "Request failed", description: normalizeError(error).detail, variant: "error" });
    }
  };

  const revokeSession = async (id: string) => {
    try {
      await authApi.revokeSession(id);
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      toast({ title: "Session revoked", variant: "success" });
    } catch (error) {
      toast({ title: "Could not revoke session", description: normalizeError(error).detail, variant: "error" });
    }
  };

  const { data: departments } = useQuery({
    queryKey: ["departments"],
    queryFn: departmentsApi.list,
    staleTime: 5 * 60 * 1000,
  });

  const { data: myRoleRequests, refetch: refetchRoleRequests } = useQuery({
    queryKey: ["my-role-requests"],
    queryFn: () => roleRequestsApi.list("all"),
  });

  const pendingRequest = myRoleRequests?.find((r) => r.status === "pending");

  const submitRoleRequest = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const requested_role = String(form.get("requested_role") || "");
    const department_id = String(form.get("department_id") || "") || null;
    const reason = String(form.get("reason") || "");
    if (!requested_role) return;
    setBusy(true);
    try {
      await roleRequestsApi.create({ requested_role, department_id, reason });
      toast({
        title: "Role request submitted",
        description: "An administrator will review your request.",
        variant: "success",
      });
      refetchRoleRequests();
    } catch (error) {
      toast({ title: "Request failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Profile & privacy</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Personal details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="first_name">First name</Label>
              <Input
                id="first_name"
                value={profile.first_name}
                onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">Last name</Label>
              <Input
                id="last_name"
                value={profile.last_name}
                onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input
              id="phone"
              value={profile.phone}
              onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="language">Language</Label>
            <Select
              id="language"
              value={profile.language}
              onChange={(e) => setProfile({ ...profile, language: e.target.value })}
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी (Hindi)</option>
              <option value="mr">मराठी (Marathi)</option>
            </Select>
          </div>
          <Button onClick={saveProfile} disabled={busy}>
            Save profile
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Notification preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(
            [
              ["in_app", "In-app notifications"],
              ["email", "Email notifications"],
              ["sms", "SMS notifications"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center gap-3 text-sm">
              <input
                type="checkbox"
                checked={prefs[key]}
                onChange={(e) => savePrefs({ ...prefs, [key]: e.target.checked })}
              />
              {label}
            </label>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4 text-primary" aria-hidden />
            Session security
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {sessions?.map((session) => (
              <li key={session.id} className="flex items-center justify-between gap-3 rounded-md border p-3 text-sm">
                <div>
                  <p className="font-medium">{session.active ? "Active session" : "Revoked session"}</p>
                  <p className="text-xs text-muted-foreground">
                    Created {formatDate(session.created_at)} · expires {formatDate(session.expires_at)}
                  </p>
                </div>
                {session.active && (
                  <Button variant="outline" size="sm" onClick={() => revokeSession(session.id)}>
                    Revoke
                  </Button>
                )}
              </li>
            ))}
            {sessions?.length === 0 && (
              <li className="text-sm text-muted-foreground">No active sessions found.</li>
            )}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Role & permissions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Current role: <span className="font-medium text-foreground">{user?.role?.replace("_", " ")}</span>
            {user?.department && <> · {user.department}</>}
          </p>
          {pendingRequest ? (
            <p className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
              Pending request: <span className="font-medium">{pendingRequest.requested_role.replace("_", " ")}</span>
              {" "}— an administrator will review it.
            </p>
          ) : (
            <form onSubmit={submitRoleRequest} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="requested_role">Request an elevated role</Label>
                <Select id="requested_role" name="requested_role" defaultValue="">
                  <option value="" disabled>
                    Select a role…
                  </option>
                  <option value="volunteer">Volunteer — help with verified incidents</option>
                  <option value="department_staff">Department staff — manage department incidents</option>
                  <option value="emergency_responder">Emergency responder — handle emergencies</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="department_id">Department (for department staff)</Label>
                <Select id="department_id" name="department_id" defaultValue="">
                  <option value="">None</option>
                  {(departments ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="reason">Why do you need this role?</Label>
                <Input id="reason" name="reason" placeholder="Brief justification for the admin" />
              </div>
              <Button type="submit" variant="outline" size="sm" disabled={busy}>
                Submit role request
              </Button>
            </form>
          )}
          {myRoleRequests && myRoleRequests.length > 0 && (
            <ul className="space-y-1 text-xs text-muted-foreground">
              {myRoleRequests.slice(0, 5).map((r) => (
                <li key={r.id}>
                  {r.requested_role.replace("_", " ")} — {r.status}
                  {r.reviewed_at ? ` (reviewed ${new Date(r.reviewed_at).toLocaleDateString()})` : ""}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border-danger/40">
        <CardHeader>
          <CardTitle className="text-base text-danger">Account deletion</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Requests are reviewed by an administrator. Your reports remain for audit purposes
            but your personal details are removed.
          </p>
          <Button variant="danger" className="mt-3" onClick={() => setDeleteOpen(true)}>
            Request account deletion
          </Button>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteOpen}
        title="Request account deletion?"
        description="An administrator will review and process this request."
        confirmLabel="Submit request"
        destructive
        onConfirm={requestDeletion}
        onCancel={() => setDeleteOpen(false)}
      />
    </div>
  );
}
