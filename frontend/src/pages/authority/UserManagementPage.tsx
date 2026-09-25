import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Skeleton, ErrorState, ConfirmDialog } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usersApi } from "@/api/auth";
import client, { normalizeError } from "@/api/client";
import { useToast } from "@/components/ui/toast";
import type { UserRole } from "@/types";

interface UserRow {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  department?: { name: string } | null;
  is_active?: boolean;
  is_locked?: boolean;
  locked_until?: string | null;
  false_report_count?: number;
  rejected_report_count?: number;
  is_reporting_blocked?: boolean;
  reporting_blocked_at?: string | null;
  reporting_blocked_reason?: string;
}

const ROLE_OPTIONS: UserRole[] = [
  "citizen",
  "department_staff",
  "emergency_responder",
  "volunteer",
  "city_admin",
  "superuser",
];

const ROLE_GROUPS = {
  citizen: "Citizens",
  department_staff: "Department Staff",
  emergency_responder: "Emergency Responders",
  volunteer: "Volunteers",
  city_admin: "City Admins",
  superuser: "Superusers",
} as const;

type RoleGroup = keyof typeof ROLE_GROUPS;

interface UserTableRowProps {
  u: UserRow;
  busy: boolean;
  onUnblockReporting: (id: string) => void;
  onToggleActive: (id: string) => void;
  onUnlock: (id: string) => void;
}

function UserTableRow({ u, busy, onUnblockReporting, onToggleActive, onUnlock }: UserTableRowProps) {
  return (
    <tr key={u.id} className="border-b hover:bg-accent/40">
      <td className="p-3">
        <p className="font-medium">
          {u.first_name} {u.last_name}
        </p>
        <p className="text-xs text-muted-foreground">{u.email}</p>
      </td>
      <td className="p-3 text-xs">{u.department?.name ?? "—"}</td>
      <td className="p-3 space-y-1">
        {u.is_active === false ? (
          <Badge variant="secondary">disabled</Badge>
        ) : (
          <Badge variant="success">active</Badge>
        )}
        {u.is_locked && (
          <div>
            <Badge variant="warning">locked</Badge>
          </div>
        )}
      </td>
      <td className="p-3 space-y-1 text-xs">
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">False:</span>
          <Badge variant="outline">{u.false_report_count ?? 0}</Badge>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">Rejected:</span>
          <Badge variant="outline">{u.rejected_report_count ?? 0}</Badge>
        </div>
        {u.is_reporting_blocked && (
          <Badge variant="destructive" className="text-xs">
            Reporting Blocked
          </Badge>
        )}
      </td>
      <td className="p-3 space-x-2">
        {u.is_reporting_blocked && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => onUnblockReporting(u.id)}
          >
            Unblock Reporting
          </Button>
        )}
        <Button
          size="sm"
          variant={u.is_active === false ? "default" : "outline"}
          disabled={busy || u.id === "current-user"}
          onClick={() => onToggleActive(u.id)}
        >
          {u.is_active === false ? "Activate" : "Deactivate"}
        </Button>
        {u.is_locked && (
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => onUnlock(u.id)}>
            Unlock
          </Button>
        )}
      </td>
    </tr>
  );
}

export function UserManagementPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeTab, setActiveTab] = useState<RoleGroup>("citizen");

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

  const unblockReporting = async (id: string) => {
    setBusy(true);
    try {
      await client.post(`/users/${id}/unblock-reporting/`);
      toast({ title: "Reporting access restored", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (error) {
      toast({ title: "Unblock failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const users = data?.results ?? data ?? [];
  
  const filteredUsers = users.filter((u: { role: UserRole }) => u.role === activeTab);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">User management</h1>
        <p className="text-sm text-muted-foreground">
          Manage users by role. Change roles, deactivate accounts, and unlock accounts. All changes are audited.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-6">
          {Object.entries(ROLE_GROUPS).map(([role, label]) => (
            <TabsTrigger key={role} value={role as RoleGroup}>
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        {Object.keys(ROLE_GROUPS).map((role) => (
          <TabsContent key={role} value={role as RoleGroup} className="space-y-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg capitalize">
                {ROLE_GROUPS[role as RoleGroup]} ({filteredUsers.length})
              </CardTitle>
            </div>

            {isPending && <Skeleton className="h-72 w-full" />}
            {isError && <ErrorState message="Could not load users." onRetry={refetch} />}

            {Array.isArray(filteredUsers) && filteredUsers.length > 0 && (
              <Card>
                <CardContent className="overflow-x-auto p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/50 text-left">
                        <th className="p-3 font-medium">User</th>
                        <th className="p-3 font-medium">Department</th>
                        <th className="p-3 font-medium">Status</th>
                        <th className="p-3 font-medium">Report Status</th>
                        <th className="p-3 font-medium">Actions</th>
                      </thead>
                      <tbody>
                        {filteredUsers.map((u) => (
                          <UserTableRow
                            key={u.id}
                            u={u}
                            busy={busy}
                            onUnblockReporting={unblockReporting}
                            onToggleActive={toggleActive}
                            onUnlock={unlockUser}
                          />
                        ))}
                      </tbody>
                    </table>
                  </CardContent>
                </Card>
            )}

            {!isPending && !isError && filteredUsers.length === 0 && (
              <Card className="text-center py-8">
                <CardContent>
                  <p className="text-muted-foreground">No {ROLE_GROUPS[role as RoleGroup].toLowerCase()} found.</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        ))}
      </Tabs>

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