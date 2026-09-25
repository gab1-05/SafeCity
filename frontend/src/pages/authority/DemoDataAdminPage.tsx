import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, Download, RefreshCw, Trash2, Upload, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import client, { normalizeError } from "@/api/client";

interface DemoUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  department?: string | null;
}

interface DemoIncident {
  id: string;
  reference_number: string;
  title: string;
  status: string;
  severity: string;
  category?: string | null;
}

export function DemoDataAdminPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [action, setAction] = useState<"users" | "incidents" | "categories" | "wards">("users");
  const [importData, setImportData] = useState("");

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ["demo-users"],
    queryFn: async (): Promise<DemoUser[]> => {
      const { data } = await client.get("/users/");
      return Array.isArray(data) ? data : data.results;
    },
  });

  const { data: incidents, isLoading: incidentsLoading } = useQuery({
    queryKey: ["demo-incidents"],
    queryFn: async (): Promise<DemoIncident[]> => {
      const { data } = await client.get("/incidents/?page_size=100");
      return data.results ?? data;
    },
  });

  const seedMutation = useMutation({
    mutationFn: async (type: string) => {
      const { data } = await client.post("/admin/seed/", { type });
      return data;
    },
    onSuccess: (data, type) => {
      toast({ title: `Demo ${type} seeded successfully`, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["demo-users"] });
      queryClient.invalidateQueries({ queryKey: ["demo-incidents"] });
    },
    onError: (error) => {
      toast({ title: "Seeding failed", description: normalizeError(error).detail, variant: "error" });
    },
  });

  const clearMutation = useMutation({
    mutationFn: async (type: string) => {
      await client.post("/admin/seed/clear/", { type });
    },
    onSuccess: (data, type) => {
      toast({ title: `Demo ${type} cleared`, variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["demo-users"] });
      queryClient.invalidateQueries({ queryKey: ["demo-incidents"] });
    },
    onError: (error) => {
      toast({ title: "Clear failed", description: normalizeError(error).detail, variant: "error" });
    },
  });

  const exportData = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const importMutation = useMutation({
    mutationFn: async ({ type, payload }: { type: string; payload: any }) => {
      await client.post("/admin/seed/import/", { type, data: payload });
    },
    onSuccess: () => {
      toast({ title: "Data imported successfully", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["demo-users"] });
      queryClient.invalidateQueries({ queryKey: ["demo-incidents"] });
      setImportData("");
    },
    onError: (error) => {
      toast({ title: "Import failed", description: normalizeError(error).detail, variant: "error" });
    },
  });

  const handleImport = () => {
    try {
      const payload = JSON.parse(importData);
      importMutation.mutate({ type: action, payload });
    } catch {
      toast({ title: "Invalid JSON", variant: "error" });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Database className="h-6 w-6 text-primary" aria-hidden /> Demo Data Manager
        </h1>
        <p className="text-sm text-muted-foreground">
          Manage demo data for development and testing. Only available in development mode.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {["users", "incidents", "categories", "wards"].map((tab) => (
          <Button
            key={tab}
            variant={action === tab ? "default" : "outline"}
            onClick={() => setAction(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </Button>
        ))}
      </div>

      {/* Seed/Clear Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Actions</CardTitle>
          <CardDescription>Seed or clear demo data with one click</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <div className="flex gap-2 flex-wrap">
            <Button
              onClick={() => seedMutation.mutate("users")}
              disabled={seedMutation.isPending}
            >
              {seedMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" /> Seeding...
                </>
              ) : (
                <>
                  <Database className="h-4 w-4" /> Seed Users
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => seedMutation.mutate("incidents")}
              disabled={seedMutation.isPending}
            >
              <Database className="h-4 w-4" /> Seed Incidents
            </Button>
            <Button
              variant="outline"
              onClick={() => seedMutation.mutate("categories")}
              disabled={seedMutation.isPending}
            >
              <Database className="h-4 w-4" /> Seed Categories
            </Button>
            <Button
              variant="outline"
              onClick={() => seedMutation.mutate("wards")}
              disabled={seedMutation.isPending}
            >
              <Database className="h-4 w-4" /> Seed Wards
            </Button>
          </div>
          <div className="flex gap-2 flex-wrap border-l pl-4 ml-4">
            <Button
              variant="danger"
              onClick={() => clearMutation.mutate("users")}
              disabled={clearMutation.isPending}
            >
              <Trash2 className="h-4 w-4" /> Clear Users
            </Button>
            <Button
              variant="danger"
              onClick={() => clearMutation.mutate("incidents")}
              disabled={clearMutation.isPending}
            >
              <Trash2 className="h-4 w-4" /> Clear Incidents
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Export/Import */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Export / Import</CardTitle>
          <CardDescription>Backup or restore demo data as JSON</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              onClick={() => users && exportData(users, "safecity-demo-users.json")}
              disabled={usersLoading}
            >
              <Download className="h-4 w-4" /> Export Users
            </Button>
            <Button
              variant="outline"
              onClick={() => incidents && exportData(incidents, "safecity-demo-incidents.json")}
              disabled={incidentsLoading}
            >
              <Download className="h-4 w-4" /> Export Incidents
            </Button>
          </div>
          <div className="space-y-2">
            <Label htmlFor="import-json">Import JSON</Label>
            <Textarea
              id="import-json"
              rows={4}
              value={importData}
              onChange={(e) => setImportData(e.target.value)}
              placeholder='Paste JSON data to import... e.g. [{"email": "test@example.com", "role": "citizen", "full_name": "Test User"}]'
            />
            <Button onClick={handleImport} disabled={importMutation.isPending || !importData.trim()}>
              <Upload className="h-4 w-4" /> {importMutation.isPending ? "Importing..." : "Import Data"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Current Data Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Current Data Preview</CardTitle>
          <CardDescription>View existing demo data in the system</CardDescription>
        </CardHeader>
        <CardContent>
          {action === "users" && (
            <div className="space-y-2">
              {usersLoading ? (
                <div className="animate-pulse space-y-2">
                  {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-muted rounded" />)}
                </div>
              ) : users?.length === 0 ? (
                <p className="text-sm text-muted-foreground">No demo users found</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-4">Email</th>
                        <th className="pb-2 pr-4">Name</th>
                        <th className="pb-2 pr-4">Role</th>
                        <th className="pb-2 pr-4">Department</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users?.map((u) => (
                        <tr key={u.id} className="border-b last:border-0">
                          <td className="py-2 pr-4">{u.email}</td>
                          <td className="py-2 pr-4">{u.full_name}</td>
                          <td className="py-2 pr-4">
                            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                              {u.role}
                            </span>
                          </td>
                          <td className="py-2 pr-4 text-muted-foreground">{u.department ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {action === "incidents" && (
            <div className="space-y-2">
              {incidentsLoading ? (
                <div className="animate-pulse space-y-2">
                  {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-muted rounded" />)}
                </div>
              ) : incidents?.length === 0 ? (
                <p className="text-sm text-muted-foreground">No demo incidents found</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-4">Reference</th>
                        <th className="pb-2 pr-4">Title</th>
                        <th className="pb-2 pr-4">Status</th>
                        <th className="pb-2 pr-4">Severity</th>
                        <th className="pb-2 pr-4">Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {incidents?.map((i) => (
                        <tr key={i.id} className="border-b last:border-0">
                          <td className="py-2 pr-4 font-mono">{i.reference_number}</td>
                          <td className="py-2 pr-4">{i.title}</td>
                          <td className="py-2 pr-4">{i.status}</td>
                          <td className="py-2 pr-4">{i.severity}</td>
                          <td className="py-2 pr-4 text-muted-foreground">{i.category ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {action === "categories" && (
            <p className="text-sm text-muted-foreground">Categories are managed via the categories API endpoint.</p>
          )}

          {action === "wards" && (
            <p className="text-sm text-muted-foreground">Wards are managed via the wards API endpoint.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}