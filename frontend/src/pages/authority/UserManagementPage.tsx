import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Skeleton, ErrorState, ConfirmDialog } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { departmentsApi, roleRequestsApi, usersApi, type RoleRequest } from "@/api/auth";
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

const ROLE_GROUPS = {
  citizen: "Citizens",
  department_staff: "Department Staff",
  emergency_responder: "Emergency Responders",
  volunteer: "Volunteers",
  city_admin: "City Admins",
  superuser: "Superusers",
} as const;

type RoleGroup = keyof typeof ROLE_GROUPS;

// What each role can do. Enforcement is server-side (role field +
// permission checks); changing a user's role below *is* changing their
// permissions. City admins / superusers are assigned directly, never
// self-requested at signup.
const ROLE_PERMISSION_SUMMARY: Record<UserRole, string[]> = {
  citizen: ["Report incidents", "Track own reports", "View public incidents"],
  volunteer: ["Citizen powers", "View verified / in-progress / resolved"],
  department_staff: ["Manage own department's incidents", "Internal notes (own dept)"],
  emergency_responder: ["Assigned + high/critical emergencies", "Update assigned status"],
  city_admin: ["All incidents", "Manage users", "Review requests", "Announcements"],
  superuser: ["Full system access"],
};

interface ManagedUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  department?: { id?: string; name: string } | null;
  is_active?: boolean;
  is_locked?: boolean;
  locked_until?: string | null;
  false_report_count?: number;
  rejected_report_count?: number;
  is_reporting_blocked?: boolean;
}

interface UserTableBodyProps {
  users: ManagedUser[];
  busy: boolean;
  departments: Array<{ id: string; name: string }>;
  onUnblockReporting: (id: string) => void;
  onToggleActive: (id: string) => void;
  onUnlock: (id: string) => void;
  onChangeRole: (id: string, role: UserRole, departmentId: string | null) => void;
}

function UserRow({
  u,
  busy,
  departments,
  onUnblockReporting,
  onToggleActive,
  onUnlock,
  onChangeRole,
}: {
  u: ManagedUser;
  busy: boolean;
  departments: Array<{ id: string; name: string }>;
  onUnblockReporting: (id: string) => void;
  onToggleActive: (id: string) => void;
  onUnlock: (id: string) => void;
  onChangeRole: (id: string, role: UserRole, departmentId: string | null) => void;
}) {
  const [role, setRole] = useState<UserRole>(u.role);
  const [departmentId, setDepartmentId] = useState<string>(u.department?.id ?? "");
  const dirty = role !== u.role || departmentId !== (u.department?.id ?? "");

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
          <Badge variant="danger" className="text-xs">
            Reporting Blocked
          </Badge>
        )}
      </td>
      <td className="p-3">
        <div className="min-w-40 space-y-1">
          <Select
            aria-label={`Role for ${u.email}`}
            value={role}
            disabled={busy}
            onChange={(e) => setRole(e.target.value as UserRole)}
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r.replace("_", " ")}
              </option>
            ))}
          </Select>
          <Select
            aria-label={`Department for ${u.email}`}
            value={departmentId}
            disabled={busy}
            onChange={(e) => setDepartmentId(e.target.value)}
          >
            <option value="">No department</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </Select>
          <p className="text-[11px] text-muted-foreground" title={ROLE_PERMISSION_SUMMARY[role].join(" · ")}>
            {ROLE_PERMISSION_SUMMARY[role][0]}
          </p>
          {dirty && (
            <Button
              size="sm"
              disabled={busy}
              onClick={() => onChangeRole(u.id, role, departmentId || null)}
            >
              Save role
            </Button>
          )}
        </div>
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

function UserTableBody({ users, busy, departments, onUnblockReporting, onToggleActive, onUnlock, onChangeRole }: UserTableBodyProps) {
  return (
    <tbody>
      {users.map((u) => (
        <UserRow
          key={u.id}
          u={u}
          busy={busy}
          departments={departments}
          onUnblockReporting={onUnblockReporting}
          onToggleActive={onToggleActive}
          onUnlock={onUnlock}
          onChangeRole={onChangeRole}
        />
      ))}
    </tbody>
  );
}

function RoleRequestsPanel({
  requests,
  busy,
  onReview,
}: {
  requests: RoleRequest[] | undefined;
  busy: boolean;
  onReview: (id: string, decision: "approve" | "reject") => void;
}) {
  if (!requests || requests.length === 0) return null;
  return (
    <Card className="border-warning/40">
      <CardHeader>
        <CardTitle className="text-lg">Pending role requests ({requests.length})</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {requests.map((r) => (
          <div
            key={r.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3 text-sm"
          >
            <div>
              <p className="font-medium">
                {r.user_name} <span className="font-normal text-muted-foreground">({r.user_email})</span>
              </p>
              <p className="text-xs text-muted-foreground">
                {r.current_role.replace("_", " ")} →{" "}
                <span className="font-medium text-foreground">{r.requested_role.replace("_", " ")}</span>
                {r.department_name ? ` · ${r.department_name}` : ""}
              </p>
              {r.reason && <p className="mt-1 text-xs italic">“{r.reason}”</p>}
            </div>
            <div className="flex gap-2">
              <Button size="sm" disabled={busy} onClick={() => onReview(r.id, "approve")}>
                Approve
              </Button>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => onReview(r.id, "reject")}>
                Reject
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
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

  const { data: departmentsData } = useQuery({
    queryKey: ["departments"],
    queryFn: departmentsApi.list,
    staleTime: 5 * 60 * 1000,
  });
  const departments = departmentsData ?? [];

  const { data: roleRequests, refetch: refetchRoleRequests } = useQuery({
    queryKey: ["role-requests", "pending"],
    queryFn: () => roleRequestsApi.list("pending"),
  });

  const changeRole = async (id: string, role: UserRole, departmentId: string | null) => {
    setBusy(true);
    try {
      await usersApi.changeRole(id, role, departmentId ?? undefined);
      toast({ title: `Role changed to ${role.replace("_", " ")}`, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (error) {
      toast({ title: "Change failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const reviewRoleRequest = async (id: string, decision: "approve" | "reject") => {
    setBusy(true);
    try {
      await roleRequestsApi.review(id, decision);
      toast({
        title: decision === "approve" ? "Role request approved" : "Role request rejected",
        variant: "success",
      });
      refetchRoleRequests();
      queryClient.invalidateQueries({ queryKey: ["users"] });
    } catch (error) {
      toast({ title: "Review failed", description: normalizeError(error).detail, variant: "error" });
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

      <RoleRequestsPanel requests={roleRequests} busy={busy} onReview={reviewRoleRequest} />

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as RoleGroup)} className="w-full">
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
                        <th className="p-3 font-medium">Role & Permissions</th>
                        <th className="p-3 font-medium">Actions</th>
                      </tr>
                    </thead>
                      <UserTableBody
                        users={filteredUsers}
                        busy={busy}
                        departments={departments}
                        onUnblockReporting={unblockReporting}
                        onToggleActive={toggleActive}
                        onUnlock={unlockUser}
                        onChangeRole={changeRole}
                      />
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