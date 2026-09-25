import { useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  BarChart3,
  Database,
  FileWarning,
  Gauge,
  LayoutDashboard,
  LogOut,
  Map,
  Megaphone,
  Menu,
  Monitor,
  Moon,
  PlusCircle,
  ScrollText,
  ShieldCheck,
  Sun,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";
import { authApi, notificationsApi } from "@/api/auth";
import { cn } from "@/lib/utils";
import { CommandPalette } from "@/components/CommandPalette";
import { wsService } from "@/services/websocket";
import { useToast } from "@/components/ui/toast";

const NAV_BY_ROLE: Record<string, Array<{ to: string; label: string; icon: React.ReactNode }>> = {
  citizen: [
    { to: "/dashboard", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" /> },
    { to: "/report", label: "Report Incident", icon: <PlusCircle className="h-4 w-4" /> },
    { to: "/incidents", label: "My Reports", icon: <FileWarning className="h-4 w-4" /> },
  ],
  department_staff: [
    { to: "/operations", label: "Operations", icon: <LayoutDashboard className="h-4 w-4" /> },
    { to: "/queue", label: "Incident Queue", icon: <FileWarning className="h-4 w-4" /> },
    { to: "/incidents", label: "My Reports", icon: <FileWarning className="h-4 w-4" /> },
    { to: "/analytics", label: "Analytics", icon: <BarChart3 className="h-4 w-4" /> },
  ],
  emergency_responder: [
    { to: "/queue", label: "Emergency Queue", icon: <FileWarning className="h-4 w-4" /> },
    { to: "/operations", label: "Operations", icon: <LayoutDashboard className="h-4 w-4" /> },
  ],
  volunteer: [
    { to: "/queue", label: "Community Feed", icon: <FileWarning className="h-4 w-4" /> },
  ],
  city_admin: [
    { to: "/admin", label: "Admin Overview", icon: <Gauge className="h-4 w-4" /> },
    { to: "/operations", label: "Operations", icon: <LayoutDashboard className="h-4 w-4" /> },
    { to: "/queue", label: "Incident Queue", icon: <FileWarning className="h-4 w-4" /> },
    { to: "/analytics", label: "Analytics", icon: <BarChart3 className="h-4 w-4" /> },
    { to: "/admin/announcements", label: "Announcements", icon: <Megaphone className="h-4 w-4" /> },
    { to: "/admin/users", label: "Users", icon: <Users className="h-4 w-4" /> },
    { to: "/admin/audit", label: "Audit Logs", icon: <ScrollText className="h-4 w-4" /> },
    { to: "/admin/demo-data", label: "Demo Data", icon: <Database className="h-4 w-4" /> },
  ],
  superuser: [
    { to: "/admin", label: "Admin Overview", icon: <Gauge className="h-4 w-4" /> },
    { to: "/operations", label: "Operations", icon: <LayoutDashboard className="h-4 w-4" /> },
    { to: "/queue", label: "Incident Queue", icon: <FileWarning className="h-4 w-4" /> },
    { to: "/analytics", label: "Analytics", icon: <BarChart3 className="h-4 w-4" /> },
    { to: "/admin/announcements", label: "Announcements", icon: <Megaphone className="h-4 w-4" /> },
    { to: "/admin/users", label: "Users", icon: <Users className="h-4 w-4" /> },
    { to: "/admin/audit", label: "Audit Logs", icon: <ScrollText className="h-4 w-4" /> },
    { to: "/admin/demo-data", label: "Demo Data", icon: <Database className="h-4 w-4" /> },
  ],
};

function ThemeToggle() {
  const { theme, setTheme } = useAuthStore();

  const modes = [
    { value: "light" as const, label: "Light", icon: <Sun className="h-5 w-5" /> },
    { value: "dark" as const, label: "Dark", icon: <Moon className="h-5 w-5" /> },
    { value: "system" as const, label: "System", icon: <Monitor className="h-5 w-5" /> },
  ];

  return (
    <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1" role="group" aria-label="Theme selection">
      {modes.map((mode) => (
        <button
          key={mode.value}
          onClick={() => setTheme(mode.value)}
          className={`flex items-center justify-center w-10 h-10 rounded-md transition-all ${
            theme === mode.value
              ? "bg-primary text-primary-foreground shadow-sm"
              : "text-muted-foreground hover:bg-background hover:text-foreground"
          }`}
          aria-label={mode.label}
          aria-pressed={theme === mode.value}
        >
          {mode.icon}
        </button>
      ))}
    </div>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [unreadCount, setUnreadCount] = useState(0);

  const { data: notifications } = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
    refetchInterval: 30_000,
  });

  useEffect(() => {
    if (notifications?.unread_count !== undefined) {
      setUnreadCount(notifications.unread_count);
    }
  }, [notifications?.unread_count]);

  useEffect(() => {
    const unsubscribe = wsService.on("notification", (payload: any) => {
      setUnreadCount((prev) => prev + 1);
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast({
        title: payload.title ?? "New notification",
        description: payload.body,
        variant: payload.type === "emergency" ? "error" : "info",
      });
    });

    const unsubscribeIncident = wsService.on("incident_update", (payload: any) => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["incident", payload.id] });
    });

    return () => {
      unsubscribe();
      unsubscribeIncident();
    };
  }, [queryClient, toast]);

  const nav = NAV_BY_ROLE[user?.role ?? "citizen"] ?? NAV_BY_ROLE.citizen;

  const handleLogout = async () => {
    await authApi.logout();
    setUser(null);
    queryClient.clear();
    navigate("/login");
  };

  const NavLinkItem = ({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) => {
    const active = location.pathname === to || location.pathname.startsWith(`${to}/`);
    return (
      <Link
        to={to}
        onClick={() => setMobileOpen(false)}
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
          active
            ? "bg-primary/10 text-primary border-l-2 border-primary"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
        )}
        aria-current={active ? "page" : undefined}
      >
        <span className="flex h-5 w-5 items-center justify-center">{icon}</span>
        {label}
      </Link>
    );
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar (mobile overlay) */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}

      {/* Sidebar (desktop) */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 border-r bg-card transition-transform duration-300 ease-in-out md:static md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Sidebar navigation"
      >
        <div className="flex h-16 items-center justify-between border-b px-4">
          <Link to="/dashboard" className="flex items-center gap-2 font-bold text-primary">
            <ShieldCheck className="h-7 w-7" aria-hidden />
            <span className="text-lg">SafeCity</span>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {nav.map((item) => (
            <NavLinkItem key={item.to} {...item} />
          ))}
        </nav>
        <div className="absolute bottom-0 w-full border-t p-3">
          <Link
            to="/map"
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
          >
            <Map className="h-4 w-4" aria-hidden />
            Public Map
          </Link>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 px-4 md:px-6 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="hidden md:block">
              <span className="text-sm font-medium text-muted-foreground">
                {user
                  ? `${user.full_name} · ${user.role.replace(/_/g, " ")}`
                  : ""}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <Link to="/notifications" className="relative" aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}>
              <Button variant="ghost" size="icon">
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-danger px-1.5 text-[10px] font-bold text-white">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Button>
            </Link>
            <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="Log out">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}