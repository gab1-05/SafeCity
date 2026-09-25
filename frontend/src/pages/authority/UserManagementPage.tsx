import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Skeleton, ErrorState, ConfirmDialog } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { usersApi } from "@/api/auth";
import client, { normalizeError } from "@/api/client";
import { useToast } from "@/components/ui/toast";
import type { UserRole } from "@/types";

const ROLE_OPTIONS: UserRole[] = [
  "citizen",
  "department_staff",
  "emergency_responder",
  "volunteer",
  "city_admin",
  "superuser",
];

export function UserManagementPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const unlockUser = async (id: string) => {
    setBusy(true);
    try {
      await usersApi.unlock(id);
      toast({ title: "Account unlocked", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (error) {
      toast({ title: "Unlock failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const { data } = await client.get("/users/");
      return data;
    },
  });

  const changeRole = async (id: string, role: UserRole) => {
    setBusy(true);
    try {
      await usersApi.changeRole(id, role);
      toast({ title: `Role changed to ${role.replace("_", " ")}`, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (error) {
      toast({ title: "Change failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = async (id: string) => {
    setBusy(true);
    try {
      await client.post(`/users/${id}/deactivate/`);
      toast({ title: "User status updated", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (error) {
      toast({ title: "Update failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
      setConfirmDeactivate(null);
    }
  };

  const users = data?.results ?? data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">User management</h1>
        <p className="text-sm text-muted-foreground">
          Change roles and deactivate accounts. All changes are audited.
        </p>
      </div>

      {isPending && <Skeleton className="h-72 w-full" />}
      {isError && <ErrorState message="Could not load users." onRetry={refetch} />}

      {Array.isArray(users) && users.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-left">
                  <th className="p-3 font-medium">User</th>
                  <th className="p-3 font-medium">Role</th>
                  <th className="p-3 font-medium">Department</th>
                  <th className="p-3 font-medium">Status</th>
                  <th className="p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: { id: string; email: string; first_name: string; last_name: string; role: UserRole; department?: { name: string } | null; is_active?: boolean; is_locked?: boolean; locked_until?: string | null }) => (
                  <tr key={u.id} className="border-b hover:bg-accent/40">
                    <td className="p-3">
                      <p className="font-medium">
                        {u.first_name} {u.last_name}
                      </p>
                      <p className="text-xs text-muted-foreground">{u.email}</p>
                    </td>
                    <td className="p-3">
                      <Select
                        aria-label={`Role for ${u.email}`}
                        value={u.role}
                        disabled={busy}
                        onChange={(e) => changeRole(u.id, e.target.value as UserRole)}
                        className="w-44"
                      >
                        {ROLE_OPTIONS.map((role) => (
                          <option key={role} value={role}>
                            {role.replace("_", " ")}
                          </option>
                        ))}
                      </Select>
                    </td>
                    <td className="p-3 text-xs">{u.department?.name ?? "—"}</td>
                    <td className="p-3 space-y-1">
                      {u.is_active === false ? (
                        <Badge variant="muted">disabled</Badge>
                      ) : (
                        <Badge variant="success">active</Badge>
                      )}
                      {u.is_locked && (
                        <div>
                          <Badge variant="warning">locked</Badge>
                        </div>
                      )}
                    </td>
                    <td className="p-3 space-x-2">
                      <Button
                        size="sm"
                        variant={u.is_active === false ? "default" : "outline"}
                        disabled={busy || u.id === "current-user"}
                        onClick={() => setConfirmDeactivate(u.id)}
                      >
                        {u.is_active === false ? "Activate" : "Deactivate"}
                      </Button>
                      {u.is_locked && (
                        <Button size="sm" variant="secondary" disabled={busy} onClick={() => unlockUser(u.id)}>
                          Unlock
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={confirmDeactivate !== null}
        title="Change account status?"
        description="Deactivated users cannot log in. This action is audited."
        confirmLabel="Apply"
        destructive
        onConfirm={() => confirmDeactivate && toggleActive(confirmDeactivate)}
        onCancel={() => setConfirmDeactivate(null)}
      />
    </div>
  );
}
