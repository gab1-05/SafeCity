import { Link, Outlet } from "react-router-dom";
import { MapPin, Monitor, Moon, ShieldCheck, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";
import { SystemStatus } from "@/components/SystemStatus";

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

export function PublicLayout() {
  const { user } = useAuthStore();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur-sm">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-bold text-primary" aria-label="SafeCity Home">
            <ShieldCheck className="h-7 w-7" aria-hidden />
            <span className="text-xl">SafeCity</span>
          </Link>
          <nav className="hidden items-center gap-8 md:flex" aria-label="Main navigation">
            <Link to="/map" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Live Map
            </Link>
            <Link to="/track" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Track Report
            </Link>
            <Link to="/announcements" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Announcements
            </Link>
            <Link to="/about" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              About
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            {user ? (
              <Link to="/dashboard">
                <Button size="sm">Dashboard</Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="ghost" size="sm">Log in</Button>
                </Link>
                <Link to="/register">
                  <Button size="sm" className="btn-brand">Sign up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t bg-muted/30 py-8">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground md:flex-row">
          <div className="flex flex-col items-center gap-2 text-center md:text-left">
            <Link to="/" className="flex items-center gap-2 font-bold text-primary">
              <ShieldCheck className="h-6 w-6" aria-hidden />
              SafeCity
            </Link>
            <p>SDP Project, The Bombay Salesian Society. For coordination, not emergencies.</p>
          </div>
          <nav className="flex flex-wrap items-center justify-center gap-4 md:gap-6" aria-label="Footer navigation">
            <Link to="/about" className="hover:text-primary transition-colors">About</Link>
            <Link to="/map" className="hover:text-primary transition-colors">Live Map</Link>
            <Link to="/announcements" className="hover:text-primary transition-colors">Announcements</Link>
            <Link to="/track" className="hover:text-primary transition-colors">Track Report</Link>
          </nav>
          <p className="flex items-center gap-3">
            <MapPin className="h-4 w-4" aria-hidden />
            Maps © OpenStreetMap contributors
            <SystemStatus />
          </p>
        </div>
      </footer>
    </div>
  );
}